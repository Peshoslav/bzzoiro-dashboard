"""
WebSocket Manager for Sports.bzzoiro live data.
Uses @st.cache_resource so it runs as a single background thread
across all Streamlit reruns — NOT restarted on every page rerun.
"""

import websocket
import threading
import queue
import json
import time
import logging
from typing import Optional, Dict, Any, Set
import streamlit as st

logger = logging.getLogger(__name__)


class WSManager:
    """
    Thread-safe singleton WebSocket manager.

    Pattern:
      1. Background thread owns the WS connection.
      2. on_message() drops parsed frames into a thread-safe Queue.
      3. Streamlit main thread drains the queue on each rerun
         and stores the latest snapshot per event_id in self.snapshots.
    """

    def __init__(self):
        self._queue: queue.Queue = queue.Queue(maxsize=200)
        self._ws: Optional[websocket.WebSocketApp] = None
        self._thread: Optional[threading.Thread] = None
        self._api_key: Optional[str] = None
        self._running: bool = False
        self.is_connected: bool = False
        self.subscribed: Set[int] = set()          # event_ids currently subscribed
        # Latest snapshots per event — updated by drain()
        self.snapshots: Dict[int, Dict[str, Any]] = {}

    # ── Public API ────────────────────────────────────────────────

    def start(self, api_key: str) -> None:
        """Start background thread if not already running."""
        if self._running:
            return
        self._api_key = api_key
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="ws-bzzoiro")
        self._thread.start()

    def subscribe(self, event_id: int) -> None:
        """Subscribe to a live match by its event_id."""
        self.subscribed.add(event_id)
        if self.is_connected and self._ws:
            self._ws.send(json.dumps({"action": "subscribe", "event_id": event_id}))

    def unsubscribe(self, event_id: int) -> None:
        """Unsubscribe from a live match."""
        self.subscribed.discard(event_id)
        if self.is_connected and self._ws:
            self._ws.send(json.dumps({"action": "unsubscribe", "event_id": event_id}))

    def drain(self) -> list:
        """
        Drain all pending frames from the queue and merge into self.snapshots.
        Call this at the top of each Streamlit rerun in the Live tab.
        Returns the list of new frames for logging / debugging.
        """
        new_frames = []
        while True:
            try:
                frame = self._queue.get_nowait()
                new_frames.append(frame)
                eid = frame.get("event_id")
                if eid:
                    existing = self.snapshots.get(eid, {})
                    ftype = frame.get("type")
                    if ftype == "event":
                        existing.update(frame)           # full snapshot overwrite
                    elif ftype == "livedata":
                        existing["livedata"] = frame     # replace tick
                    elif ftype in ("odds", "odds_book"):
                        existing["odds"] = frame
                    self.snapshots[eid] = existing
            except queue.Empty:
                break
        return new_frames

    @property
    def status(self) -> str:
        if not self._running:
            return "⛔ Спрян"
        if self.is_connected:
            return "🟢 Свързан"
        return "🟡 Свързване…"

    # ── Private ───────────────────────────────────────────────────

    def _loop(self) -> None:
        """Auto-reconnecting WebSocket run loop."""
        delay = 3
        while self._running:
            try:
                # Token passed as query parameter (per v2 docs)
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
                logger.info("Reconnecting in %ds…", delay)
                time.sleep(delay)
                delay = min(delay * 2, 60)   # exponential back-off, cap 60 s

    def _on_open(self, ws) -> None:
        self.is_connected = True
        logger.info("WS opened — re-subscribing %d matches", len(self.subscribed))
        for eid in self.subscribed:
            ws.send(json.dumps({"action": "subscribe", "event_id": eid}))

    def _on_message(self, ws, raw: str) -> None:
        try:
            frame = json.loads(raw)
            if not self._queue.full():
                self._queue.put_nowait(frame)
        except (json.JSONDecodeError, queue.Full):
            pass

    def _on_close(self, ws, code, msg) -> None:
        self.is_connected = False
        logger.info("WS closed %s %s", code, msg)

    def _on_error(self, ws, err) -> None:
        self.is_connected = False
        logger.error("WS error: %s", err)


# ── Streamlit singleton ───────────────────────────────────────────

@st.cache_resource
def get_ws_manager() -> WSManager:
    """
    Returns the single WSManager instance shared across all Streamlit reruns.
    Because this is @st.cache_resource, it is created exactly once per
    server process, not once per user session — perfect for a background thread.
    """
    return WSManager()
