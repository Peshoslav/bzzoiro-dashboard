"""
Bzzoiro Sports API v2 — REST wrapper with Streamlit caching.

Base URL : https://sports.bzzoiro.com/api/v2/
Auth     : Authorization: Token YOUR_API_KEY

All public functions are decorated with @st.cache_data so that rapid
re-runs of the Streamlit script don't hammer the API.
"""

from __future__ import annotations

import streamlit as st
import requests
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

BASE = "https://sports.bzzoiro.com/api/v2"


def _headers() -> Dict[str, str]:
    return {"Authorization": f"Token {st.secrets['BZZOIRO_API_KEY']}"}


def _get(path: str, params: Optional[Dict] = None) -> Any:
    """
    Raw GET helper.  Returns parsed JSON or raises an exception that
    the caller can catch and display via st.error().
    """
    r = requests.get(f"{BASE}{path}", headers=_headers(), params=params or {}, timeout=12)
    r.raise_for_status()
    return r.json()


# ─── Events (matches) ────────────────────────────────────────────

@st.cache_data(ttl=120)   # 2-min cache — schedule changes rarely
def get_events(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    team_id: Optional[int] = None,
    league_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 100,
) -> List[Dict]:
    """List events (matches) with optional filters."""
    today = date.today().isoformat()
    params: Dict[str, Any] = {
        "date_from": date_from or today,
        "date_to": date_to or today,
        "limit": limit,
    }
    if team_id:
        params["team_id"] = team_id
    if league_id:
        params["league_id"] = league_id
    if status:
        params["status"] = status
    try:
        data = _get("/events/", params)
        return data.get("results", [])
    except Exception as e:
        st.error(f"API грешка (events): {e}")
        return []


@st.cache_data(ttl=60)
def get_live_events() -> List[Dict]:
    """Return all events currently in progress."""
    return get_events(
        date_from=(date.today() - timedelta(days=1)).isoformat(),
        date_to=date.today().isoformat(),
        status="inprogress",
        limit=50,
    )


@st.cache_data(ttl=300)
def get_event_stats(event_id: int) -> Dict:
    """Per-side statistics for a finished or live event."""
    try:
        return _get(f"/events/{event_id}/stats/")
    except Exception as e:
        st.error(f"API грешка (stats {event_id}): {e}")
        return {}


@st.cache_data(ttl=300)
def get_event_incidents(event_id: int) -> List[Dict]:
    """Goal, card, substitution incidents for an event."""
    try:
        data = _get(f"/events/{event_id}/incidents/")
        return data if isinstance(data, list) else data.get("results", [])
    except Exception as e:
        return []


@st.cache_data(ttl=300)
def get_event_odds(event_id: int) -> Dict:
    """Pre-match / live consensus odds for an event."""
    try:
        return _get(f"/events/{event_id}/odds/")
    except Exception:
        return {}


# ─── Teams ───────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def get_team(team_id: int) -> Dict:
    """Team detail."""
    try:
        return _get(f"/teams/{team_id}/")
    except Exception:
        return {}


@st.cache_data(ttl=3600)
def search_team_by_name(name: str) -> Optional[Dict]:
    """
    Search for a team by name and return the best match as a dict
    {"id": ..., "name": ...}, or None if not found.

    Tries two strategies:
      1. GET /teams/?search=<name>  (preferred — direct search)
      2. GET /teams/?name=<name>    (fallback param name)
    Then does a client-side case-insensitive exact/prefix match.
    Results are cached for 1 hour — safe to call on every rerun.
    """
    if not name or not name.strip():
        return None
    name_clean = name.strip()
    for params in ({"search": name_clean, "limit": 10},
                   {"name":   name_clean, "limit": 10}):
        try:
            data    = _get("/teams/", params)
            results = data.get("results", data) if isinstance(data, dict) else data
            if not isinstance(results, list):
                continue
            # Exact match first, then prefix, then substring
            lower = name_clean.lower()
            for strategy in ("exact", "prefix", "sub"):
                for t in results:
                    tname = (t.get("name") or "").lower()
                    if strategy == "exact"  and tname == lower:        return t
                    if strategy == "prefix" and tname.startswith(lower): return t
                    if strategy == "sub"    and lower in tname:         return t
        except Exception:
            continue
    return None


@st.cache_data(ttl=1800)
def resolve_team_id(name_or_id: Any) -> Optional[int]:
    """
    Given either an int team_id or a string team name, return the team_id.
    Returns None if lookup fails.
    Uses search_team_by_name for strings.
    """
    if isinstance(name_or_id, int):
        return name_or_id
    if isinstance(name_or_id, str) and name_or_id.strip():
        team = search_team_by_name(name_or_id.strip())
        if team:
            return team.get("id")
    return None


@st.cache_data(ttl=300)
def get_team_fixtures(team_id: int, last_n: int = 10) -> List[Dict]:
    """
    Last N finished matches for a team (newest-first).
    Uses team_id filter on /events/ with status=finished.
    """
    try:
        params = {
            "team_id": team_id,
            "status": "finished",
            "limit": last_n,
            "date_from": (date.today() - timedelta(days=365)).isoformat(),
            "date_to": date.today().isoformat(),
        }
        data = _get("/events/", params)
        return data.get("results", [])[:last_n]
    except Exception as e:
        st.error(f"API грешка (fixtures {team_id}): {e}")
        return []


# ─── H2H ─────────────────────────────────────────────────────────

@st.cache_data(ttl=600)
def get_h2h(team1_id: int, team2_id: int, last_n: int = 10) -> List[Dict]:
    """
    Head-to-head: fetch finished events where both teams participated.
    The v2 API doesn't have a dedicated H2H endpoint, so we fetch by
    team1 and filter client-side for matches involving team2.
    """
    try:
        all_fixtures = get_team_fixtures(team1_id, last_n=50)

        def _tid(val):
            if isinstance(val, dict):
                return val.get("id")
            return None  # string team name — can't filter by ID

        h2h = [
            m for m in all_fixtures
            if (_tid(m.get("home_team") or m.get("home")) == team2_id
                or _tid(m.get("away_team") or m.get("away")) == team2_id)
        ]
        # If team IDs were None (string names), fall back to returning all fixtures
        if not h2h and team1_id is None:
            return all_fixtures[:last_n]
        return h2h[:last_n]
    except Exception:
        return []


# ─── Leagues ─────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def get_leagues() -> List[Dict]:
    """All available leagues."""
    try:
        data = _get("/leagues/", {"limit": 200})
        return data.get("results", [])
    except Exception:
        return []


@st.cache_data(ttl=1800)
def get_standings(league_id: int, season_id: Optional[int] = None) -> List[Dict]:
    """League table standings."""
    try:
        params = {}
        if season_id:
            params["season_id"] = season_id
        data = _get(f"/leagues/{league_id}/standings/", params)
        return data.get("standings", data.get("results", []))
    except Exception:
        return []


# ─── Predictions ─────────────────────────────────────────────────

@st.cache_data(ttl=600)
def get_prediction(event_id: int) -> Dict:
    """ML prediction for a single event."""
    try:
        data = _get("/predictions/", {"event_id": event_id, "limit": 1})
        results = data.get("results", [])
        return results[0] if results else {}
    except Exception:
        return {}
