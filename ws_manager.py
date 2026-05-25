"""
WebSocket Manager — Bzzoiro live data.
@st.cache_resource singleton — one background thread, shared across all reruns.

Key upgrade: per-match frame HISTORY (deque) instead of overwrite.
This gives AI full match context from kick-off to current minute.
"""

import websocket
import threading
import queue
import json
import time
import logging
from collections import deque
from datetime import datetime
from typing import Optional, Dict, Any, Set, List

import streamlit as st

logger = logging.getLogger(__name__)

# Max frames stored per match (~90 min × 4 frames/min = ~360, use 600 for safety)
MAX_HISTORY = 600


class WSManager:
    def __init__(self):
        self._queue: queue.Queue       = queue.Queue(maxsize=500)
        self._ws: Optional[websocket.WebSocketApp] = None
        self._thread: Optional[threading.Thread]   = None
        self._api_key: Optional[str]  = None
        self._running: bool           = False
        self.is_connected: bool       = False
        self.subscribed: Set[int]     = set()

        # Latest snapshot per event (fast read for UI)
        self.snapshots: Dict[int, Dict[str, Any]] = {}

        # Full frame history per event — used for AI context and charts
        # deque(maxlen=MAX_HISTORY) keeps newest MAX_HISTORY frames, drops oldest
        self.history: Dict[int, deque] = {}

        # Derived series built from history — ready for st.line_chart
        # Format: {eid: {"minutes": [], "xg_home": [], "xg_away": [],
        #                "att_home": [], "att_away": []}}
        self.series: Dict[int, Dict[str, list]] = {}

    # ── Public API ────────────────────────────────────────────────

    def start(self, api_key: str) -> None:
        if self._running:
            return
        self._api_key = api_key
        self._running = True
        self._thread  = threading.Thread(
            target=self._loop, daemon=True, name="ws-bzzoiro")
        self._thread.start()

    def subscribe(self, event_id: int) -> None:
        self.subscribed.add(event_id)
        if not event_id in self.history:
            self.history[event_id] = deque(maxlen=MAX_HISTORY)
        if self.is_connected and self._ws:
            self._ws.send(json.dumps({"action": "subscribe", "event_id": event_id}))

    def unsubscribe(self, event_id: int) -> None:
        self.subscribed.discard(event_id)
        if self.is_connected and self._ws:
            self._ws.send(json.dumps({"action": "unsubscribe", "event_id": event_id}))

    def drain(self) -> list:
        """
        Drain pending frames → update snapshots + history + series.
        Call at top of each fragment rerun.
        """
        new_frames = []
        while True:
            try:
                frame = self._queue.get_nowait()
            except queue.Empty:
                break
            new_frames.append(frame)

            eid   = frame.get("event_id")
            ftype = frame.get("type", "")
            if not eid:
                continue

            # ── Ensure history deque exists ───────────────────────
            if eid not in self.history:
                self.history[eid] = deque(maxlen=MAX_HISTORY)

            # ── Stamp frame with wall-clock time ──────────────────
            frame["_ts"] = datetime.utcnow().isoformat(timespec="seconds")

            # ── Append to history (ALL frame types) ───────────────
            self.history[eid].append(frame)

            # ── Update snapshot ───────────────────────────────────
            existing = self.snapshots.get(eid, {})
            if ftype == "event":
                existing.update(frame)
            elif ftype == "livedata":
                existing["livedata"] = frame
            elif ftype in ("odds", "odds_book"):
                existing["odds"] = frame
            elif ftype == "stats":
                existing["stats"] = frame.get("stats", frame)
            else:
                existing.update({k: v for k, v in frame.items()
                                  if k not in ("type", "event_id", "_ts")})
            self.snapshots[eid] = existing

            # ── Update time series ────────────────────────────────
            self._update_series(eid, frame, ftype)

        return new_frames

    def get_ai_context(self, event_id: int,
                       home_name: str, away_name: str,
                       max_chars: int = 5000) -> str:
        """
        Build a structured, chronological context string from WS history.
        Passed to Gemini so it has the full match picture from kick-off.
        """
        hist = list(self.history.get(event_id, []))
        if not hist:
            return ""

        lines: List[str] = [
            f"\n═══ WEBSOCKET ИСТОРИЯ ({len(hist)} frames) ═══"
        ]

        # ── Score progression ─────────────────────────────────────
        scores_seen = []
        for f in hist:
            sc = f.get("score") or {}
            h  = sc.get("home"); a = sc.get("away")
            min_ = (f.get("time") or {}).get("minute", "")
            if h is not None and a is not None:
                entry = f"{min_}′ {h}–{a}"
                if not scores_seen or scores_seen[-1] != entry:
                    scores_seen.append(entry)
        if scores_seen:
            lines.append(f"РЕЗУЛТАТ ПРОГРЕСИЯ: {' → '.join(scores_seen[-8:])}")

        # ── Latest stats ──────────────────────────────────────────
        snap = self.snapshots.get(event_id, {})
        stats = snap.get("stats", {})
        if stats:
            hs  = stats.get("home", {})
            as_ = stats.get("away", {})
            def _s(d, k):
                v = d.get(k, 0)
                return float(v.get("value", 0) if isinstance(v, dict) else (v or 0))
            lines.append(
                f"ТЕКУЩИ СТАТИСТИКИ:"
                f"\n  {home_name}: xG={_s(hs,'xg'):.2f} удари={_s(hs,'total_shots'):.0f}"
                f" в_рамка={_s(hs,'shots_on_target'):.0f}"
                f" поз={_s(hs,'ball_possession'):.0f}%"
                f" оп.атаки={_s(hs,'dangerous_attack'):.0f}"
                f" ъглови={_s(hs,'corner_kicks'):.0f}"
                f"\n  {away_name}: xG={_s(as_,'xg'):.2f} удари={_s(as_,'total_shots'):.0f}"
                f" в_рамка={_s(as_,'shots_on_target'):.0f}"
                f" поз={_s(as_,'ball_possession'):.0f}%"
                f" оп.атаки={_s(as_,'dangerous_attack'):.0f}"
                f" ъглови={_s(as_,'corner_kicks'):.0f}"
            )

        # ── xG series summary ─────────────────────────────────────
        ser = self.series.get(event_id, {})
        xg_h = ser.get("xg_home", [])
        xg_a = ser.get("xg_away", [])
        mins = ser.get("minutes", [])
        if xg_h and xg_a and mins:
            lines.append(
                f"xG ПРОГРЕСИЯ (мин → домакин / гост):"
            )
            # Sample every ~10 min
            step = max(1, len(mins) // 10)
            for i in range(0, len(mins), step):
                lines.append(
                    f"  {mins[i]}′ → {xg_h[i]:.2f} / {xg_a[i]:.2f}")
            lines.append(
                f"  Финал: {xg_h[-1]:.2f} / {xg_a[-1]:.2f}")

        # ── Situation events (goals, shots, corners, cards) ───────
        events_log: List[str] = []
        for f in hist:
            ftype = f.get("type", "")
            ld    = f if ftype == "livedata" else f.get("livedata", {})
            if not ld:
                continue
            sit  = ld.get("situation", "")
            side = ld.get("side", "")
            min_ = (f.get("time") or {}).get("minute", "?")
            name = home_name if side == "home" else away_name if side == "away" else ""
            key_events = {
                "goal":             f"⚽ {min_}′ ГОЛ — {name}",
                "penalty":          f"🔴 {min_}′ ДУЗПА — {name}",
                "red_card":         f"🟥 {min_}′ ЧЕР КАРТОН — {name}",
                "yellow_card":      f"🟨 {min_}′ ЖЪЛ КАРТОН — {name}",
                "corner":           f"🚩 {min_}′ ъглов удар — {name}",
                "dangerous_attack": f"💥 {min_}′ опасна атака — {name}",
                "substitution":     f"🔄 {min_}′ смяна — {name}",
            }
            if sit in key_events:
                entry = key_events[sit]
                if not events_log or events_log[-1] != entry:
                    events_log.append(entry)

        if events_log:
            lines.append("ХРОНОЛОГИЯ НА МАЧА:")
            lines.extend(events_log[-30:])  # last 30 key events

        result = "\n".join(lines)
        # Trim to max_chars if needed
        if len(result) > max_chars:
            result = result[:max_chars] + "\n…(съкратено)"
        return result

    @property
    def status(self) -> str:
        if not self._running:   return "⛔ Спрян"
        if self.is_connected:   return "🟢 Свързан"
        return "🟡 Свързване…"

    # ── Private ───────────────────────────────────────────────────

    def _update_series(self, eid: int, frame: Dict, ftype: str) -> None:
        """Append a data point to per-match time series from a stats frame."""
        stats = None
        if ftype == "stats":
            stats = frame.get("stats", frame)
        elif ftype == "event":
            stats = frame.get("stats")
        if not stats:
            return

        hs   = stats.get("home", {})
        as_  = stats.get("away", {})
        min_ = (frame.get("time") or {}).get("minute")
        if min_ is None:
            return

        def _v(d, k):
            v = d.get(k, 0)
            return float(v.get("value", 0) if isinstance(v, dict) else (v or 0))

        if eid not in self.series:
            self.series[eid] = {
                "minutes": [], "xg_home": [], "xg_away": [],
                "att_home": [], "att_away": [],
                "shots_home": [], "shots_away": [],
            }

        s = self.series[eid]
        # Avoid duplicate minutes
        if s["minutes"] and s["minutes"][-1] == int(min_):
            # Update last point
            s["xg_home"][-1]    = _v(hs, "xg")
            s["xg_away"][-1]    = _v(as_, "xg")
            s["att_home"][-1]   = _v(hs, "dangerous_attack")
            s["att_away"][-1]   = _v(as_, "dangerous_attack")
            s["shots_home"][-1] = _v(hs, "shots_on_target")
            s["shots_away"][-1] = _v(as_, "shots_on_target")
        else:
            s["minutes"].append(int(min_))
            s["xg_home"].append(_v(hs, "xg"))
            s["xg_away"].append(_v(as_, "xg"))
            s["att_home"].append(_v(hs, "dangerous_attack"))
            s["att_away"].append(_v(as_, "dangerous_attack"))
            s["shots_home"].append(_v(hs, "shots_on_target"))
            s["shots_away"].append(_v(as_, "shots_on_target"))

    def _loop(self) -> None:
        delay = 3
        while self._running:
            try:
                url = f"wss://sports.bzzoiro.com/ws/live/?token={self._api_key}"
                self._ws = websocket.WebSocketApp(
                    url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_close=self._on_close,
                    on_error=self._on_error,
                )
                self._ws.run_forever(ping_interval=30, ping_timeout=10)
            except Exception as exc:
                logger.warning("WS crash: %s", exc)
            self.is_connected = False
            if self._running:
                time.sleep(delay)
                delay = min(delay * 2, 60)

    def _on_open(self, ws) -> None:
        self.is_connected = True
        for eid in self.subscribed:
            ws.send(json.dumps({"action": "subscribe", "event_id": eid}))

    def _on_message(self, ws, raw: str) -> None:
        try:
            frame = json.loads(raw)
            if not self._queue.full():
                self._queue.put_nowait(frame)
        except Exception:
            pass

    def _on_close(self, ws, code, msg) -> None:
        self.is_connected = False

    def _on_error(self, ws, err) -> None:
        self.is_connected = False
        logger.error("WS error: %s", err)


@st.cache_resource
def get_ws_manager() -> WSManager:
    return WSManager()
