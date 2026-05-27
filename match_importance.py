"""
Match Importance Calculator (0-100)
Uses league standings to determine how much a result matters
for each team's seasonal objectives.
"""
from __future__ import annotations
import streamlit as st
from typing import Dict, List, Optional, Tuple, Any

# ── League configuration ──────────────────────────────────────────
# Maps partial lowercase league name → {cl, el, conf, rel, teams}
LEAGUE_CONFIG: Dict[str, Dict] = {
    "premier league":   {"cl":4,"el":2,"conf":1,"rel":3,"teams":20},
    "la liga":          {"cl":4,"el":2,"conf":0,"rel":3,"teams":20},
    "bundesliga":       {"cl":4,"el":2,"conf":1,"rel":2,"teams":18},
    "serie a":          {"cl":4,"el":2,"conf":0,"rel":3,"teams":20},
    "ligue 1":          {"cl":3,"el":2,"conf":0,"rel":3,"teams":18},
    "eredivisie":       {"cl":2,"el":2,"conf":1,"rel":3,"teams":18},
    "primeira liga":    {"cl":3,"el":2,"conf":0,"rel":3,"teams":18},
    "super lig":        {"cl":2,"el":2,"conf":0,"rel":3,"teams":19},
    "championship":     {"cl":0,"el":0,"conf":0,"rel":3,"teams":24,"promotion":2,"playoff":4},
    "champions league": {"cl":0,"el":0,"conf":0,"rel":0,"teams":8,"advance":2},
    "europa league":    {"cl":0,"el":0,"conf":0,"rel":0,"teams":8,"advance":2},
    # fallback
    "_default":         {"cl":3,"el":2,"conf":0,"rel":3,"teams":18},
}

LABELS = {
    (90,100): ("🔴 Season-defining", "#ef4444",
               "Титла, изпадане или Шампионска лига без право на грешка."),
    (75, 89): ("🟠 Критичен",        "#f97316",
               "Загуба тук почти елиминира реалния шанс за ключова цел."),
    (55, 74): ("🟡 Висок залог",      "#eab308",
               "Победа или загуба значително променя шансовете."),
    (35, 54): ("🟢 Значим",           "#22c55e",
               "Има за какво да се играе, но един резултат не е решаващ."),
    (15, 34): ("🔵 Нисък залог",      "#3b82f6",
               "Позиционни или финансови импликации. Не европейски зони."),
    ( 0, 14): ("⚫ Мъртъв мач",       "#6b7280",
               "Позицията е потвърдена или няма какво да се спечели."),
}


def _get_label(score: int) -> Tuple[str,str,str]:
    for (lo,hi),(label,color,desc) in LABELS.items():
        if lo <= score <= hi:
            return label, color, desc
    return "⚫ Мъртъв мач","#6b7280","—"


def _find_config(league_name: str) -> Dict:
    ln = (league_name or "").lower()
    for key, cfg in LEAGUE_CONFIG.items():
        if key != "_default" and key in ln:
            return cfg
    return LEAGUE_CONFIG["_default"]


def _find_team_row(standings: List[Dict], team_name: str,
                   team_id=None) -> Optional[Dict]:
    """Find a team's row in the standings list."""
    name_l = (team_name or "").lower()
    for row in standings:
        # Try ID match first
        team = row.get("team") or {}
        if isinstance(team, dict):
            rid = team.get("id"); rname = (team.get("name") or "").lower()
        else:
            rid = None; rname = str(team).lower()
        if team_id and rid == team_id:         return row
        if name_l and name_l in rname:          return row
        if rname and rname in name_l:            return row
    return None


def _estimate_matches_remaining(row: Dict, total_teams: int) -> int:
    """Estimate matches left from played count."""
    played = (row.get("played") or row.get("matches_played") or
              row.get("games_played") or 0)
    total_season = (total_teams - 1) * 2    # home + away vs every team
    remaining    = max(0, total_season - int(played))
    return remaining


def _tightness(gap: int, max_possible: int) -> float:
    """
    How tight is the race?
    gap=0 → 1.0 (dead tight)
    gap>=max_possible → 0.0 (mathematically over)
    """
    if max_possible <= 0: return 0.0
    return max(0.0, 1.0 - gap / max_possible)


def calculate_importance(
    team_name:   str,
    team_id,
    standings:   List[Dict],
    league_name: str = "",
) -> Dict[str, Any]:
    """
    Calculate match importance for a single team.

    Returns:
      score       : 0-100
      label       : e.g. "🔴 Season-defining"
      color       : hex color
      description : one-line explanation
      detail      : dict with race components
    """
    if not standings:
        return _no_data(team_name)

    row = _find_team_row(standings, team_name, team_id)
    if not row:
        return _no_data(team_name)

    cfg       = _find_config(league_name)
    n_teams   = cfg["teams"]
    pos       = int(row.get("position") or row.get("rank") or row.get("pos") or 99)
    pts       = int(row.get("points") or row.get("pts") or 0)
    remaining = _estimate_matches_remaining(row, n_teams)
    max_pts   = remaining * 3

    def _pts_at(target_pos: int) -> int:
        """Points of team at target_pos."""
        for r in standings:
            p = int(r.get("position") or r.get("rank") or r.get("pos") or 0)
            if p == target_pos:
                return int(r.get("points") or r.get("pts") or 0)
        return 0

    detail: Dict[str, Any] = {"pos": pos, "pts": pts, "remaining": remaining}
    scores: List[float]    = []

    # ── Title race ────────────────────────────────────────────────
    pts_1st     = _pts_at(1)
    gap_title   = max(0, pts_1st - pts)
    t_title     = _tightness(gap_title, max_pts)
    if pos == 1: t_title = max(t_title, 0.7)   # leader always has something to play for
    scores.append(t_title * 100)
    detail["title_gap"] = gap_title

    # ── Champions League ──────────────────────────────────────────
    cl_cutoff = cfg.get("cl", 0)
    if cl_cutoff > 0:
        pts_cl    = _pts_at(cl_cutoff)
        if pos <= cl_cutoff:
            gap_cl = max(0, _pts_at(cl_cutoff+1) - pts + 1) if cl_cutoff+1 <= n_teams else 0
        else:
            gap_cl = max(0, pts_cl - pts)
        t_cl = _tightness(gap_cl, max_pts)
        scores.append(t_cl * 90)
        detail["cl_gap"] = gap_cl

    # ── Europa League ─────────────────────────────────────────────
    el_cutoff = cfg.get("cl",0) + cfg.get("el",0)
    if cfg.get("el",0) > 0 and el_cutoff > cfg.get("cl",0):
        pts_el = _pts_at(el_cutoff)
        if pos <= el_cutoff:
            gap_el = max(0, _pts_at(el_cutoff+1) - pts + 1) if el_cutoff+1 <= n_teams else 0
        else:
            gap_el = max(0, pts_el - pts)
        t_el = _tightness(gap_el, max_pts)
        scores.append(t_el * 70)
        detail["el_gap"] = gap_el

    # ── Relegation ────────────────────────────────────────────────
    rel_cutoff = cfg.get("rel",0)
    if rel_cutoff > 0:
        safe_pos  = n_teams - rel_cutoff   # last safe position
        pts_rel   = _pts_at(safe_pos)
        if pos > safe_pos:
            # In the relegation zone — how far to safety?
            gap_safety = max(0, pts_rel - pts + 1)
        else:
            # Safe — how close is the drop zone chasing them?
            gap_safety = max(0, pts - _pts_at(safe_pos+1))
        # Closer to the edge → higher importance (from both sides)
        t_rel = _tightness(gap_safety, max_pts)
        scores.append(t_rel * 100)
        detail["rel_gap"] = gap_safety

    # ── Promotion (e.g. Championship) ────────────────────────────
    if cfg.get("promotion",0) > 0:
        pts_prom = _pts_at(cfg["promotion"])
        gap_prom = max(0, pts_prom - pts)
        scores.append(_tightness(gap_prom, max_pts) * 95)

    # Final score = max component (a team is as important as their most
    # critical race), slightly blended with average
    if not scores:
        score = 20
    else:
        top    = max(scores)
        avg    = sum(scores)/len(scores)
        score  = int(top*0.75 + avg*0.25)
        score  = max(0, min(100, score))

    # Decay for dead rubbers: if mathematically confirmed in position
    if max_pts == 0:
        score = min(score, 5)

    label, color, desc = _get_label(score)
    return {
        "score":       score,
        "label":       label,
        "color":       color,
        "description": desc,
        "detail":      detail,
        "available":   True,
    }


def _no_data(team_name: str) -> Dict:
    return {
        "score": -1, "label": "—", "color": "#4b5563",
        "description": "Класирането не е налично.",
        "detail": {}, "available": False,
    }


@st.cache_data(ttl=1800, show_spinner=False)
def get_match_importance(
    home_name: str, away_name: str,
    home_id, away_id,
    league_id: Optional[int],
    league_name: str = "",
) -> Tuple[Dict, Dict]:
    """
    Returns (home_importance, away_importance) dicts.
    Cached 30 min — standings don't change that fast.
    """
    if not league_id:
        return _no_data(home_name), _no_data(away_name)
    try:
        from api import get_standings
        standings = get_standings(league_id)
        if not standings:
            return _no_data(home_name), _no_data(away_name)
        hi = calculate_importance(home_name, home_id, standings, league_name)
        ai = calculate_importance(away_name, away_id, standings, league_name)
        return hi, ai
    except Exception as e:
        return _no_data(home_name), _no_data(away_name)
