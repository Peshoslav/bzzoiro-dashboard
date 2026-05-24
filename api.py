"""
Bzzoiro Sports API v2 — REST wrapper with Streamlit caching.
All functions are @st.cache_data — safe to call on every rerun.
"""
from __future__ import annotations
import streamlit as st
import requests
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

BASE = "https://sports.bzzoiro.com/api/v2"
TIMEOUT = 10


def _headers() -> Dict[str, str]:
    return {"Authorization": f"Token {st.secrets['BZZOIRO_API_KEY']}"}


def _get(path: str, params: Optional[Dict] = None) -> Any:
    r = requests.get(f"{BASE}{path}", headers=_headers(),
                     params=params or {}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def _results(data: Any) -> List[Dict]:
    if isinstance(data, list):   return data
    if isinstance(data, dict):   return data.get("results", [])
    return []


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
    try:
        return _results(_get("/events/", params))
    except Exception:
        return []


@st.cache_data(ttl=30, show_spinner=False)
def get_live_events() -> List[Dict]:
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    today     = date.today().isoformat()
    return get_events(date_from=yesterday, date_to=today,
                      status="inprogress", limit=50)


@st.cache_data(ttl=120, show_spinner=False)
def get_event_stats(event_id: int) -> Dict:
    try:    return _get(f"/events/{event_id}/stats/")
    except: return {}


@st.cache_data(ttl=120, show_spinner=False)
def get_event_incidents(event_id: int) -> List[Dict]:
    try:    return _results(_get(f"/events/{event_id}/incidents/"))
    except: return []


@st.cache_data(ttl=120, show_spinner=False)
def get_event_odds(event_id: int) -> Dict:
    try:    return _get(f"/events/{event_id}/odds/")
    except: return {}


@st.cache_data(ttl=300, show_spinner=False)
def get_event_lineups(event_id: int) -> Dict:
    try:    return _get(f"/events/{event_id}/lineups/")
    except: return {}


@st.cache_data(ttl=300, show_spinner=False)
def get_event_shotmap(event_id: int) -> List[Dict]:
    try:    return _results(_get(f"/events/{event_id}/shotmap/"))
    except: return []


# ── Teams — use team_name param, NO id required ───────────────────

@st.cache_data(ttl=300, show_spinner=False)
def get_team_fixtures(team_id: Optional[int] = None,
                      team_name: Optional[str] = None,
                      last_n: int = 10) -> List[Dict]:
    """
    Fetch last N finished matches for a team.
    Accepts either team_id (int) or team_name (str) — API v2 supports both.
    """
    params: Dict[str, Any] = {
        "status":    "finished",
        "date_from": (date.today() - timedelta(days=365)).isoformat(),
        "date_to":   date.today().isoformat(),
        "limit":     min(last_n * 2, 50),   # fetch extra, API is newest-first
    }
    if team_id:   params["team_id"]   = team_id
    elif team_name: params["team_name"] = team_name
    else:         return []
    try:
        results = _results(_get("/events/", params))
        # API returns newest-first; we want newest N finished
        return results[:last_n]
    except Exception:
        return []


@st.cache_data(ttl=300, show_spinner=False)
def get_h2h(home_id: Optional[int], away_id: Optional[int],
            home_name: Optional[str] = None, away_name: Optional[str] = None,
            last_n: int = 10) -> List[Dict]:
    """
    Head-to-head: fetch via home team, filter for matches involving away team.
    Uses IDs if available, falls back to name-based search.
    """
    try:
        all_fixtures = get_team_fixtures(
            team_id=home_id, team_name=home_name, last_n=50
        )
        # Filter for matches involving the away team
        def _matches_away(m: Dict) -> bool:
            for side in ("home_team", "away_team", "home", "away"):
                v = m.get(side)
                tname = v.get("name","") if isinstance(v, dict) else str(v or "")
                tid   = v.get("id")     if isinstance(v, dict) else None
                if away_id  and tid   == away_id:                    return True
                if away_name and away_name.lower() in tname.lower(): return True
            return False
        return [m for m in all_fixtures if _matches_away(m)][:last_n]
    except Exception:
        return []


# ── Leagues ───────────────────────────────────────────────────────

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


# ── Predictions & odds ────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def get_prediction(event_id: int) -> Dict:
    try:
        data = _get("/predictions/", {"event_id": event_id, "limit": 1})
        res  = _results(data)
        return res[0] if res else {}
    except: return {}


@st.cache_data(ttl=300, show_spinner=False)
def get_odds_comparison(event_id: int) -> Dict:
    """All bookmaker odds for a match (v2 comparison endpoint)."""
    try:    return _get(f"/odds/{event_id}/comparison/")
    except:
        try:    return _get(f"/events/{event_id}/odds/")
        except: return {}


# ── Players ───────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def get_event_player_stats(event_id: int) -> List[Dict]:
    try:    return _results(_get(f"/events/{event_id}/player-stats/"))
    except: return []


@st.cache_data(ttl=3600, show_spinner=False)
def search_teams_by_name(name: str) -> List[Dict]:
    """Search teams — used as last resort when no ID available."""
    try:    return _results(_get("/teams/", {"search": name, "limit": 5}))
    except: return []
