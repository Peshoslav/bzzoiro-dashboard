"""
Bzzoiro Sports API v2 — REST wrapper with Streamlit caching.
"""
from __future__ import annotations
import streamlit as st
import requests
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

BASE    = "https://sports.bzzoiro.com/api/v2"
TIMEOUT = 10

# Statuses that mean "match is currently being played"
LIVE_STATUSES = {
    "inprogress","live","1h","2h","ht","et","pen",
    "in_progress","playing","1st_half","2nd_half",
    "halftime","extra_time","penalties","paused",
}

def _headers() -> Dict[str, str]:
    return {"Authorization": f"Token {st.secrets['BZZOIRO_API_KEY']}"}

def _get(path: str, params: Optional[Dict] = None) -> Any:
    r = requests.get(f"{BASE}{path}", headers=_headers(),
                     params=params or {}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def _results(data: Any) -> List[Dict]:
    if isinstance(data, list): return data
    if isinstance(data, dict): return data.get("results", [])
    return []

def _status_str(m: Dict) -> str:
    v = m.get("status", m.get("event_status", ""))
    if isinstance(v, dict): v = v.get("type", "")
    return str(v or "").lower().strip()


# ── Events ────────────────────────────────────────────────────────

@st.cache_data(ttl=60, show_spinner=False)
def get_events(date_from: str, date_to: str,
               league_id: Optional[int] = None,
               status: Optional[str] = None,
               limit: int = 100) -> List[Dict]:
    params: Dict[str, Any] = {
        "date_from": date_from, "date_to": date_to, "limit": limit
    }
    if league_id: params["league_id"] = league_id
    if status:    params["status"]    = status
    try:    return _results(_get("/events/", params))
    except: return []


@st.cache_data(ttl=20, show_spinner=False)
def get_live_events() -> List[Dict]:
    """
    Fetch live matches — uses two strategies:
    1. API-side filter status=inprogress
    2. Fetch today's all events and filter client-side
    (Covers cases where API uses non-standard status strings)
    """
    today     = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    # Strategy 1: API filter
    try:
        api_live = _results(_get("/events/", {
            "status": "inprogress",
            "date_from": yesterday,
            "date_to": today,
            "limit": 50,
        }))
        if api_live:
            return api_live
    except: pass

    # Strategy 2: fetch today and filter client-side
    try:
        today_events = _results(_get("/events/", {
            "date_from": yesterday,
            "date_to": today,
            "limit": 200,
        }))
        return [m for m in today_events
                if _status_str(m) in LIVE_STATUSES]
    except: return []


@st.cache_data(ttl=90, show_spinner=False)
def get_event_stats(event_id: int) -> Dict:
    try:    return _get(f"/events/{event_id}/stats/")
    except: return {}


@st.cache_data(ttl=90, show_spinner=False)
def get_event_incidents(event_id: int) -> List[Dict]:
    try:    return _results(_get(f"/events/{event_id}/incidents/"))
    except: return []


@st.cache_data(ttl=90, show_spinner=False)
def get_event_lineups(event_id: int) -> Dict:
    try:    return _get(f"/events/{event_id}/lineups/")
    except: return {}


@st.cache_data(ttl=90, show_spinner=False)
def get_event_shotmap(event_id: int) -> List[Dict]:
    try:    return _results(_get(f"/events/{event_id}/shotmap/"))
    except: return []


@st.cache_data(ttl=120, show_spinner=False)
def get_event_odds(event_id: int) -> Dict:
    """Try multiple endpoint variants for odds."""
    for path in (f"/events/{event_id}/odds/",
                 f"/odds/?event_id={event_id}&limit=1"):
        try:
            data = _get(path)
            if data: return data
        except: pass
    return {}


@st.cache_data(ttl=120, show_spinner=False)
def get_odds_comparison(event_id: int) -> Dict:
    """All bookmaker odds — tries comparison endpoint then falls back."""
    for path in (f"/odds/{event_id}/comparison/",
                 f"/events/{event_id}/odds/",
                 f"/odds/comparison/?event_id={event_id}"):
        try:
            data = _get(path)
            if data: return data
        except: pass
    return {}


# ── Teams — team_name param avoids need for ID ───────────────────

@st.cache_data(ttl=300, show_spinner=False)
def get_team_fixtures(team_id: Optional[int] = None,
                      team_name: Optional[str] = None,
                      last_n: int = 10) -> List[Dict]:
    params: Dict[str, Any] = {
        "status":    "finished",
        "date_from": (date.today() - timedelta(days=365)).isoformat(),
        "date_to":   date.today().isoformat(),
        "limit":     min(last_n * 2, 50),
    }
    if team_id:   params["team_id"]   = team_id
    elif team_name: params["team_name"] = team_name
    else:         return []
    try:    return _results(_get("/events/", params))[:last_n]
    except: return []


@st.cache_data(ttl=300, show_spinner=False)
def get_h2h(home_id: Optional[int], away_id: Optional[int],
            home_name: Optional[str] = None, away_name: Optional[str] = None,
            last_n: int = 10) -> List[Dict]:
    all_fx = get_team_fixtures(team_id=home_id, team_name=home_name, last_n=50)
    def _away_match(m: Dict) -> bool:
        for side in ("home_team","away_team","home","away"):
            v = m.get(side)
            tn  = v.get("name","") if isinstance(v, dict) else str(v or "")
            tid = v.get("id")      if isinstance(v, dict) else None
            if away_id   and tid == away_id:                     return True
            if away_name and away_name.lower() in tn.lower():    return True
        return False
    return [m for m in all_fx if _away_match(m)][:last_n]


# ── Leagues & standings ───────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def get_leagues() -> List[Dict]:
    try:    return _results(_get("/leagues/", {"limit": 200}))
    except: return []


@st.cache_data(ttl=1800, show_spinner=False)
def get_standings(league_id: int) -> List[Dict]:
    try:
        data = _get(f"/leagues/{league_id}/standings/")
        return data.get("standings", _results(data))
    except: return []


# ── Predictions ───────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def get_prediction(event_id: int) -> Dict:
    """Try multiple endpoint variants for predictions."""
    # Try event-specific endpoint first
    for path in (f"/events/{event_id}/predictions/",
                 f"/predictions/?event_id={event_id}&limit=1",
                 f"/predictions/{event_id}/"):
        try:
            data = _get(path)
            if isinstance(data, dict) and data:
                # Direct object
                if "home_win_pct" in data or "home_probability" in data:
                    return data
                # Wrapped in results
                res = data.get("results", [])
                if res: return res[0]
            if isinstance(data, list) and data:
                return data[0]
        except: pass
    return {}


# ── Players ───────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def get_event_player_stats(event_id: int) -> List[Dict]:
    for path in (f"/events/{event_id}/player-stats/",
                 f"/events/{event_id}/players/"):
        try:
            data = _get(path)
            if data: return _results(data)
        except: pass
    return []


@st.cache_data(ttl=3600, show_spinner=False)
def search_teams_by_name(name: str) -> List[Dict]:
    try:    return _results(_get("/teams/", {"search": name, "limit": 5}))
    except: return []
