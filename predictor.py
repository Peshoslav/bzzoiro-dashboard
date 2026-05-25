"""
Dixon-Coles Football Match Predictor
=====================================
Uses real bzzoiro form data (last N matches per team) to calculate:
  - 1/X/2 win probabilities
  - Expected goals (xG) for each team
  - Top 10 most likely scorelines
  - BTTS (Both Teams To Score)
  - Over/Under 0.5, 1.5, 2.5, 3.5 goals
  - Scoreline probability heatmap data

Model details:
  - Poisson model with Dixon-Coles low-score correction (rho parameter)
  - Time-weighted form: recent matches count more (exponential decay)
  - Home advantage factor
  - H2H weighting: direct meetings contribute extra weight
  - Attack/Defense strength ratings relative to sample average
  - Minimum 3 matches per team required; degrades gracefully below that

All functions are pure Python + math — zero extra dependencies.
Results are cached with @st.cache_data.
"""

from __future__ import annotations
import math
from typing import Dict, List, Optional, Tuple, Any
from datetime import date, datetime
import streamlit as st


# ── Constants ─────────────────────────────────────────────────────
HOME_ADVANTAGE  = 1.20   # multiplier on home attack strength
RHO             = -0.13  # Dixon-Coles correction for low scores
DECAY_HALF_LIFE = 60     # days: a match 60 days ago is worth half as much
MIN_MATCHES     = 3      # minimum matches needed per team
MAX_GOALS       = 8      # max goals per team in scoreline grid


# ── Helpers ───────────────────────────────────────────────────────

def _days_ago(match: Dict) -> float:
    """Return how many days ago a match was played."""
    for k in ("start_at", "kickoff_at", "event_date", "scheduled"):
        v = match.get(k)
        if not v:
            continue
        try:
            s = str(v).strip().rstrip("Zz")
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
                        "%Y-%m-%dT%H:%M",    "%Y-%m-%d"):
                try:
                    dt = datetime.strptime(s[:19], fmt[:len(s[:19])])
                    return max(0.0, (datetime.utcnow() - dt).total_seconds() / 86400)
                except ValueError:
                    continue
        except Exception:
            continue
    return 30.0  # assume 30 days if unknown


def _weight(days: float) -> float:
    """Exponential time-decay weight."""
    return math.exp(-math.log(2) * days / DECAY_HALF_LIFE)


def _score_from_match(m: Dict) -> Tuple[Optional[int], Optional[int]]:
    """Extract (home_goals, away_goals) from a match dict."""
    s = m.get("score")
    if isinstance(s, dict):
        h, a = s.get("home"), s.get("away")
    else:
        h = m.get("home_score")
        a = m.get("away_score")
    try:
        return int(h), int(a)
    except (TypeError, ValueError):
        return None, None


def _is_home(match: Dict, team_name: str) -> bool:
    """Did the team play at home in this match?"""
    home_v = match.get("home_team") or match.get("home") or {}
    if isinstance(home_v, dict):
        hn = home_v.get("name", "")
    else:
        hn = str(home_v)
    return team_name.lower() in hn.lower()


# ── Strength rating from fixtures ─────────────────────────────────

def _compute_strength(fixtures: List[Dict], team_name: str
                       ) -> Tuple[float, float, float, int]:
    """
    Compute time-weighted attack & defense strength for a team.
    Returns (attack_str, defense_str, avg_xg_conceded, n_matches_used).
    
    attack_str  = weighted avg goals scored per match
    defense_str = weighted avg goals conceded per match (lower = better defense)
    """
    total_w    = 0.0
    scored_w   = 0.0
    conceded_w = 0.0
    n          = 0

    for m in fixtures:
        hg, ag = _score_from_match(m)
        if hg is None or ag is None:
            continue
        days = _days_ago(m)
        w    = _weight(days)
        if _is_home(m, team_name):
            scored_w   += w * hg
            conceded_w += w * ag
        else:
            scored_w   += w * ag
            conceded_w += w * hg
        total_w += w
        n       += 1

    if n == 0 or total_w < 0.01:
        return 1.2, 1.2, 1.2, 0   # league average fallback

    atk = scored_w   / total_w
    dfn = conceded_w / total_w
    return max(0.1, atk), max(0.1, dfn), dfn, n


# ── Dixon-Coles correction ────────────────────────────────────────

def _dc_correction(hg: int, ag: int, lam: float, mu: float, rho: float) -> float:
    """
    Dixon-Coles correction factor τ for low-scoring cells.
    Only applied to (0,0), (1,0), (0,1), (1,1).
    """
    if hg == 0 and ag == 0:
        return 1 - lam * mu * rho
    if hg == 1 and ag == 0:
        return 1 + mu * rho
    if hg == 0 and ag == 1:
        return 1 + lam * rho
    if hg == 1 and ag == 1:
        return 1 - rho
    return 1.0


def _poisson_pmf(k: int, lam: float) -> float:
    """P(X=k) for Poisson(lambda)."""
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


# ── Main prediction engine ────────────────────────────────────────

@st.cache_data(ttl=600, show_spinner=False)
def predict_match(
    home_name:     str,
    away_name:     str,
    home_fixtures: List[Dict],
    away_fixtures: List[Dict],
    h2h_matches:   Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """
    Full Dixon-Coles pre-match prediction.

    Returns a dict with keys:
      home_win, draw, away_win          (probabilities 0-1)
      home_xg, away_xg                  (expected goals)
      btts                              (both teams to score probability)
      over05, over15, over25, over35    (over N goals probability)
      under25                           (under 2.5 goals)
      top_scorelines                    (list of {h,a,prob} sorted by prob)
      heatmap                           (MAX_GOALS+1 × MAX_GOALS+1 matrix)
      confidence                        (0-100 score based on data quality)
      home_matches_used, away_matches_used
      warning                           (None or string if low data)
    """
    # ── Build fixtures list with H2H weighting ────────────────────
    # H2H matches count as double weight — they're the most relevant signal
    h2h = h2h_matches or []

    def _augment(fixtures, team_name):
        """Add H2H matches to the fixtures list with extra copies."""
        augmented = list(fixtures)
        for hm in h2h:
            hg, ag = _score_from_match(hm)
            if hg is None: continue
            # Add H2H match twice (double weight)
            augmented.append(hm)
            augmented.append(hm)
        return augmented

    home_aug = _augment(home_fixtures, home_name)
    away_aug = _augment(away_fixtures, away_name)

    # ── Compute strengths ─────────────────────────────────────────
    home_atk, home_dfn, _, home_n = _compute_strength(home_aug, home_name)
    away_atk, away_dfn, _, away_n = _compute_strength(away_aug, away_name)

    # ── League average (from both teams' data pooled) ─────────────
    # Used to normalise: strength = team_rate / league_avg
    all_fx = list(home_fixtures) + list(away_fixtures)
    if all_fx:
        total_goals = 0; total_w = 0.0
        for m in all_fx:
            hg, ag = _score_from_match(m)
            if hg is None: continue
            w = _weight(_days_ago(m))
            total_goals += w * (hg + ag)
            total_w     += w * 2
        league_avg = (total_goals / total_w) if total_w > 0 else 1.2
    else:
        league_avg = 1.2

    league_avg = max(0.5, league_avg)

    # Normalised strengths relative to league average
    home_atk_n = home_atk / league_avg
    home_dfn_n = home_dfn / league_avg
    away_atk_n = away_atk / league_avg
    away_dfn_n = away_dfn / league_avg

    # ── Expected goals ────────────────────────────────────────────
    # λ (home xG) = home_attack × away_defense × league_avg × home_advantage
    # μ (away xG) = away_attack × home_defense × league_avg
    lam = home_atk_n * away_dfn_n * league_avg * HOME_ADVANTAGE
    mu  = away_atk_n * home_dfn_n * league_avg

    lam = max(0.1, min(lam, MAX_GOALS - 0.1))
    mu  = max(0.1, min(mu,  MAX_GOALS - 0.1))

    # ── Scoreline probability matrix ──────────────────────────────
    grid = []
    for hg in range(MAX_GOALS + 1):
        row = []
        for ag in range(MAX_GOALS + 1):
            p = (_poisson_pmf(hg, lam) *
                 _poisson_pmf(ag, mu)  *
                 _dc_correction(hg, ag, lam, mu, RHO))
            row.append(max(0.0, p))
        grid.append(row)

    # Normalise (DC correction can shift total slightly)
    total = sum(grid[h][a] for h in range(MAX_GOALS+1) for a in range(MAX_GOALS+1))
    if total > 0:
        grid = [[grid[h][a] / total
                 for a in range(MAX_GOALS+1)]
                for h in range(MAX_GOALS+1)]

    # ── Aggregate probabilities ───────────────────────────────────
    home_win = sum(grid[h][a] for h in range(MAX_GOALS+1)
                               for a in range(MAX_GOALS+1) if h > a)
    draw     = sum(grid[h][a] for h in range(MAX_GOALS+1)
                               for a in range(MAX_GOALS+1) if h == a)
    away_win = 1.0 - home_win - draw

    btts     = sum(grid[h][a] for h in range(1, MAX_GOALS+1)
                               for a in range(1, MAX_GOALS+1))

    def _over(n):
        return sum(grid[h][a] for h in range(MAX_GOALS+1)
                               for a in range(MAX_GOALS+1) if h + a > n)

    over05  = _over(0.5)
    over15  = _over(1.5)
    over25  = _over(2.5)
    over35  = _over(3.5)
    under25 = 1.0 - over25

    # ── Top scorelines ────────────────────────────────────────────
    all_scores = [
        {"h": h, "a": a, "prob": grid[h][a]}
        for h in range(MAX_GOALS+1)
        for a in range(MAX_GOALS+1)
    ]
    top_scorelines = sorted(all_scores, key=lambda x: -x["prob"])[:12]

    # ── Confidence score ──────────────────────────────────────────
    # Based on: number of matches available for each team
    n_min      = min(home_n, away_n)
    n_max      = max(home_n, away_n)
    conf_base  = min(100, int((n_min / 10) * 60 + (n_max / 15) * 40))
    h2h_bonus  = min(15, len(h2h) * 3)
    confidence = min(100, conf_base + h2h_bonus)

    warning = None
    if home_n < MIN_MATCHES or away_n < MIN_MATCHES:
        warning = (f"⚠️ Ограничени данни: "
                   f"{home_name} ({home_n} мача), "
                   f"{away_name} ({away_n} мача). "
                   f"Прогнозата е по-малко надеждна.")

    return {
        "home_win":          round(home_win, 4),
        "draw":              round(draw,     4),
        "away_win":          round(away_win, 4),
        "home_xg":           round(lam, 2),
        "away_xg":           round(mu,  2),
        "btts":              round(btts,    4),
        "over05":            round(over05,  4),
        "over15":            round(over15,  4),
        "over25":            round(over25,  4),
        "over35":            round(over35,  4),
        "under25":           round(under25, 4),
        "top_scorelines":    top_scorelines,
        "heatmap":           grid,
        "confidence":        confidence,
        "home_matches_used": home_n,
        "away_matches_used": away_n,
        "warning":           warning,
        "home_name":         home_name,
        "away_name":         away_name,
        "league_avg_goals":  round(league_avg, 2),
    }
