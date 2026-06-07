"""
Bzzoiro Tennis API v2 — REST wrapper, паралелен на api.py за футбол.
"""
from __future__ import annotations
import streamlit as st
import requests
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

BASE    = "https://sports.bzzoiro.com/tennis/api/v2"
TIMEOUT = 10

LIVE_STATUSES = {
    "inprogress","live","playing","in_progress",
    "1st_set","2nd_set","3rd_set","4th_set","5th_set",
    "set1","set2","set3","set4","set5",
}

def _h() -> Dict[str, str]:
    return {"Authorization": f"Token {st.secrets['BZZOIRO_API_KEY']}"}

def _get(path: str, params: Optional[Dict] = None) -> Any:
    r = requests.get(f"{BASE}{path}", headers=_h(),
                     params=params or {}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def _results(data: Any) -> List[Dict]:
    if isinstance(data, list):  return data
    if isinstance(data, dict):  return data.get("results", [])
    return []

def _status(m: Dict) -> str:
    v = m.get("status", "")
    if isinstance(v, dict): v = v.get("type", "")
    return str(v or "").lower().strip()

# ── Matches ───────────────────────────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def tennis_get_matches(date_from: str, date_to: str,
                       circuit: Optional[str] = None,
                       status: Optional[str] = None,
                       limit: int = 100) -> List[Dict]:
    params: Dict[str, Any] = {
        "date_from": date_from, "date_to": date_to, "limit": limit
    }
    if circuit: params["circuit"] = circuit   # ATP | WTA
    if status:  params["status"]  = status
    try:    return _results(_get("/matches/", params))
    except: return []

@st.cache_data(ttl=20, show_spinner=False)
def tennis_get_live() -> List[Dict]:
    today     = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    # Strategy 1: API filter
    try:
        live = _results(_get("/matches/live/"))
        if live: return live
    except: pass
    # Strategy 2: today's matches filtered client-side
    try:
        all_m = _results(_get("/matches/", {
            "date_from": yesterday, "date_to": today, "limit": 200
        }))
        return [m for m in all_m if _status(m) in LIVE_STATUSES]
    except: return []

@st.cache_data(ttl=90, show_spinner=False)
def tennis_get_match(match_id: int) -> Dict:
    try:    return _get(f"/matches/{match_id}/")
    except: return {}

@st.cache_data(ttl=90, show_spinner=False)
def tennis_get_h2h(match_id: int) -> Dict:
    """H2H + recent form за двамата играчи."""
    try:    return _get(f"/matches/{match_id}/h2h/")
    except: return {}

# ── Tournaments ───────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def tennis_get_tournaments(circuit: Optional[str] = None,
                           surface: Optional[str] = None) -> List[Dict]:
    params: Dict[str, Any] = {"limit": 200}
    if circuit: params["circuit"] = circuit
    if surface: params["surface"] = surface
    try:    return _results(_get("/tournaments/", params))
    except: return []

# ── Rankings ──────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def tennis_get_rankings(circuit: str = "ATP", limit: int = 100) -> List[Dict]:
    try:    return _results(_get("/rankings/", {"type": circuit, "limit": limit}))
    except: return []

# ── Predictions ───────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def tennis_get_prediction(match_id: int) -> Dict:
    """Bzzoiro собствена XGBoost прогноза за мача."""
    for path in (f"/matches/{match_id}/predictions/",
                 f"/predictions/?match_id={match_id}&limit=1",
                 f"/predictions/{match_id}/"):
        try:
            data = _get(path)
            if isinstance(data, list) and data:   return data[0]
            if isinstance(data, dict) and data:   return data
        except: pass
    # Fallback: списък с upcoming predictions
    try:
        preds = _results(_get("/predictions/", {"limit": 200}))
        for p in preds:
            mid = p.get("match_id") or (p.get("match") or {}).get("id")
            if mid == match_id: return p
    except: pass
    return {}

@st.cache_data(ttl=300, show_spinner=False)
def tennis_get_upcoming_predictions(circuit: Optional[str] = None,
                                    limit: int = 50) -> List[Dict]:
    params: Dict[str, Any] = {"limit": limit}
    if circuit: params["circuit"] = circuit
    try:    return _results(_get("/predictions/", params))
    except: return []

# ── Players ───────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def tennis_search_player(name: str) -> List[Dict]:
    try:    return _results(_get("/players/", {"search": name, "limit": 5}))
    except: return []

# ── Helper: извлича имена и rankove от match dict ─────────────────
def parse_tennis_match(m: Dict) -> Dict:
    """Нормализира match dict независимо от API response shape."""
    p1 = m.get("player1") or m.get("home") or {}
    p2 = m.get("player2") or m.get("away") or {}
    if isinstance(p1, str): p1 = {"name": p1}
    if isinstance(p2, str): p2 = {"name": p2}

    sc1 = m.get("player1_sets", m.get("home_score", ""))
    sc2 = m.get("player2_sets", m.get("away_score", ""))

    tourn = m.get("tournament") or m.get("league") or {}
    if isinstance(tourn, str): tourn = {"name": tourn}

    return {
        "id":          m.get("id"),
        "p1_name":     p1.get("name", "?"),
        "p2_name":     p2.get("name", "?"),
        "p1_rank":     p1.get("ranking") or p1.get("rank"),
        "p2_rank":     p2.get("ranking") or p2.get("rank"),
        "p1_sets":     sc1,
        "p2_sets":     sc2,
        "current_pt":  m.get("current_point", ""),
        "is_srv_p1":   m.get("is_serving_p1"),
        "status":      _status(m),
        "tournament":  tourn.get("name", ""),
        "surface":     (tourn.get("surface") or m.get("surface") or "").capitalize(),
        "round":       m.get("round", ""),
        "scheduled":   m.get("scheduled") or m.get("start_at") or "",
        "circuit":     tourn.get("circuit") or m.get("circuit") or "",
        "raw":         m,
    }
