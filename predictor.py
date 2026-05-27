"""
Dixon-Coles Football Match Predictor
=====================================
Outputs:
  - 1/X/2 probabilities, xG, top scorelines, BTTS, O/U
  - data_confidence   : 0-100 — how much form data we have
  - model_confidence  : 0-100 — how certain the model is (entropy + consistency)
  - confidence        : 0-100 — combined score used for filtering in predictions tab
"""
from __future__ import annotations
import math
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import streamlit as st

HOME_ADVANTAGE  = 1.20
RHO             = -0.13
DECAY_HALF_LIFE = 60
MIN_MATCHES     = 3
MAX_GOALS       = 8


# ── Helpers ───────────────────────────────────────────────────────

def _days_ago(match: Dict) -> float:
    for k in ("start_at","kickoff_at","event_date","scheduled"):
        v = match.get(k)
        if not v: continue
        try:
            s = str(v).strip().rstrip("Zz")
            for fmt in ("%Y-%m-%dT%H:%M:%S","%Y-%m-%d %H:%M:%S",
                        "%Y-%m-%dT%H:%M",   "%Y-%m-%d"):
                try:
                    dt = datetime.strptime(s[:19], fmt[:len(s[:19])])
                    return max(0.0,(datetime.utcnow()-dt).total_seconds()/86400)
                except ValueError: continue
        except Exception: continue
    return 30.0

def _weight(days: float) -> float:
    return math.exp(-math.log(2)*days/DECAY_HALF_LIFE)

def _score_from_match(m: Dict) -> Tuple[Optional[int],Optional[int]]:
    s = m.get("score")
    if isinstance(s, dict): h,a = s.get("home"),s.get("away")
    else: h,a = m.get("home_score"),m.get("away_score")
    try:    return int(h),int(a)
    except: return None,None

def _is_home(match: Dict, team_name: str) -> bool:
    home_v = match.get("home_team") or match.get("home") or {}
    hn = home_v.get("name","") if isinstance(home_v, dict) else str(home_v)
    return team_name.lower() in hn.lower()


# ── Strength computation ──────────────────────────────────────────

def _compute_strength(fixtures: List[Dict], team_name: str):
    total_w = scored_w = conceded_w = 0.0
    n = 0
    goals_list = []   # for consistency calculation
    for m in fixtures:
        hg,ag = _score_from_match(m)
        if hg is None: continue
        days = _days_ago(m); w = _weight(days)
        gf = hg if _is_home(m, team_name) else ag
        ga = ag if _is_home(m, team_name) else hg
        scored_w   += w*gf; conceded_w += w*ga
        total_w    += w;    n          += 1
        goals_list.append(gf)
    if n == 0 or total_w < 0.01:
        return 1.2, 1.2, 0.0, 0
    atk = scored_w/total_w; dfn = conceded_w/total_w
    # form consistency = inverse of std-dev of goals scored (normalised 0-1)
    if len(goals_list) >= 3:
        mean = sum(goals_list)/len(goals_list)
        std  = math.sqrt(sum((x-mean)**2 for x in goals_list)/len(goals_list))
        consistency = max(0.0, 1.0 - std/3.0)   # std>3 → inconsistent
    else:
        consistency = 0.5
    return max(0.1,atk), max(0.1,dfn), consistency, n


# ── Dixon-Coles ───────────────────────────────────────────────────

def _dc_correction(hg,ag,lam,mu,rho):
    if hg==0 and ag==0: return 1-lam*mu*rho
    if hg==1 and ag==0: return 1+mu*rho
    if hg==0 and ag==1: return 1+lam*rho
    if hg==1 and ag==1: return 1-rho
    return 1.0

def _poisson_pmf(k,lam):
    if lam<=0: return 1.0 if k==0 else 0.0
    return math.exp(-lam)*(lam**k)/math.factorial(k)


# ── Confidence components ─────────────────────────────────────────

def _entropy_confidence(hw: float, dw: float, aw: float) -> float:
    """
    Model confidence from entropy of 1X2 distribution.
    Low entropy (concentrated probs) = high confidence.
    Returns 0-100.
    """
    MAX_H = math.log(3)   # entropy of uniform(1/3,1/3,1/3) ≈ 1.099
    probs = [p for p in (hw,dw,aw) if p > 0]
    entropy = -sum(p*math.log(p) for p in probs)
    return round((1 - entropy/MAX_H) * 100)

def _data_confidence(n_home: int, n_away: int, n_h2h: int) -> int:
    """Confidence based on volume of data available."""
    n_min     = min(n_home, n_away)
    n_max     = max(n_home, n_away)
    base      = min(100, int((n_min/10)*60 + (n_max/15)*40))
    h2h_bonus = min(15, n_h2h*3)
    return min(100, base + h2h_bonus)

def _h2h_alignment(h2h: List[Dict], home_name: str,
                   model_hw: float, model_aw: float) -> float:
    """
    Do H2H results agree with the model's prediction?
    Returns adjustment: +1.0 (strong agreement) to -1.0 (disagreement).
    """
    if len(h2h) < 2: return 0.0
    hw = dw = aw = 0
    for m in h2h:
        hg,ag = _score_from_match(m)
        if hg is None: continue
        htid = (m.get("home_team") or m.get("home") or {})
        htn  = htid.get("name","") if isinstance(htid,dict) else str(htid)
        is_h = home_name.lower() in htn.lower()
        if hg==ag:               dw+=1
        elif (is_h and hg>ag) or (not is_h and ag>hg): hw+=1
        else:                    aw+=1
    total = hw+dw+aw or 1
    h2h_hw = hw/total; h2h_aw = aw/total
    # Agreement: both model and H2H favour same team
    model_favours_home = model_hw > model_aw
    h2h_favours_home   = h2h_hw  > h2h_aw
    if model_favours_home == h2h_favours_home:
        # how strongly?
        strength = abs(model_hw-model_aw) * abs(h2h_hw-h2h_aw)
        return min(1.0, strength*4)
    else:
        return -0.5   # disagreement penalty


# ── Main prediction ───────────────────────────────────────────────

@st.cache_data(ttl=600, show_spinner=False)
def predict_match(
    home_name: str, away_name: str,
    home_fixtures: List[Dict], away_fixtures: List[Dict],
    h2h_matches: Optional[List[Dict]] = None,
) -> Dict[str,Any]:
    """
    Full Dixon-Coles pre-match prediction with three-layer confidence.

    confidence breakdown:
      data_confidence   — how much form data is available (0-100)
      model_confidence  — how decisive/concentrated the probabilities are (0-100)
      h2h_alignment     — do H2H results agree with the form model? (-1 to +1)
      confidence        — combined score: the one shown in UI and used for filtering
    """
    h2h = h2h_matches or []

    # Augment with H2H (double weight for direct meetings)
    home_aug = list(home_fixtures) + h2h + h2h
    away_aug = list(away_fixtures) + h2h + h2h

    home_atk, home_dfn, home_cons, home_n = _compute_strength(home_aug, home_name)
    away_atk, away_dfn, away_cons, away_n = _compute_strength(away_aug, away_name)

    # League average from pooled data
    all_fx = list(home_fixtures)+list(away_fixtures)
    total_goals=0; total_w=0.0
    for m in all_fx:
        hg,ag=_score_from_match(m)
        if hg is None: continue
        w=_weight(_days_ago(m)); total_goals+=w*(hg+ag); total_w+=w*2
    league_avg = max(0.5,(total_goals/total_w) if total_w>0 else 1.2)

    # Normalised strengths
    home_atk_n = home_atk/league_avg; home_dfn_n = home_dfn/league_avg
    away_atk_n = away_atk/league_avg; away_dfn_n = away_dfn/league_avg

    lam = max(0.1, min(home_atk_n*away_dfn_n*league_avg*HOME_ADVANTAGE, MAX_GOALS-0.1))
    mu  = max(0.1, min(away_atk_n*home_dfn_n*league_avg,                MAX_GOALS-0.1))

    # Scoreline grid
    grid=[]
    for hg in range(MAX_GOALS+1):
        row=[]
        for ag in range(MAX_GOALS+1):
            p=_poisson_pmf(hg,lam)*_poisson_pmf(ag,mu)*_dc_correction(hg,ag,lam,mu,RHO)
            row.append(max(0.0,p))
        grid.append(row)
    total=sum(grid[h][a] for h in range(MAX_GOALS+1) for a in range(MAX_GOALS+1))
    if total>0:
        grid=[[grid[h][a]/total for a in range(MAX_GOALS+1)] for h in range(MAX_GOALS+1)]

    home_win = sum(grid[h][a] for h in range(MAX_GOALS+1) for a in range(MAX_GOALS+1) if h>a)
    draw     = sum(grid[h][a] for h in range(MAX_GOALS+1) for a in range(MAX_GOALS+1) if h==a)
    away_win = max(0.0, 1.0-home_win-draw)

    btts   = sum(grid[h][a] for h in range(1,MAX_GOALS+1) for a in range(1,MAX_GOALS+1))
    def _over(n): return sum(grid[h][a] for h in range(MAX_GOALS+1)
                              for a in range(MAX_GOALS+1) if h+a>n)
    over05=_over(0.5); over15=_over(1.5); over25=_over(2.5); over35=_over(3.5)

    top_scorelines = sorted(
        [{"h":h,"a":a,"prob":grid[h][a]}
         for h in range(MAX_GOALS+1) for a in range(MAX_GOALS+1)],
        key=lambda x:-x["prob"])[:12]

    # ── Confidence breakdown ──────────────────────────────────────
    data_conf  = _data_confidence(home_n, away_n, len(h2h))
    model_conf = _entropy_confidence(home_win, draw, away_win)
    h2h_align  = _h2h_alignment(h2h, home_name, home_win, away_win)
    cons_bonus = int((home_cons+away_cons)/2 * 10)   # 0-10

    # Combine: data quality 40%, model sharpness 45%, H2H + consistency 15%
    raw_conf  = (data_conf*0.40 + model_conf*0.45
                 + h2h_align*10 + cons_bonus*0.5)
    confidence = max(0, min(100, int(raw_conf)))

    # Confidence label
    if confidence >= 75:   conf_label = "Висока"
    elif confidence >= 55: conf_label = "Умерена"
    elif confidence >= 35: conf_label = "Ниска"
    else:                  conf_label = "Много ниска"

    warning = None
    if home_n < MIN_MATCHES or away_n < MIN_MATCHES:
        warning = (f"⚠️ Малко данни: {home_name} ({home_n} мача), "
                   f"{away_name} ({away_n} мача).")

    return {
        "home_win":          round(home_win, 4),
        "draw":              round(draw,     4),
        "away_win":          round(away_win, 4),
        "home_xg":           round(lam, 2),
        "away_xg":           round(mu,  2),
        "btts":              round(btts,    4),
        "over05":            round(_over(0.5), 4),
        "over15":            round(over15,  4),
        "over25":            round(over25,  4),
        "over35":            round(over35,  4),
        "under25":           round(1-over25,4),
        "top_scorelines":    top_scorelines,
        "heatmap":           grid,
        # ── Confidence breakdown ──
        "confidence":        confidence,
        "conf_label":        conf_label,
        "data_confidence":   data_conf,
        "model_confidence":  model_conf,
        "h2h_alignment":     round(h2h_align, 2),
        "home_consistency":  round(home_cons, 2),
        "away_consistency":  round(away_cons, 2),
        # ── Meta ──
        "home_matches_used": home_n,
        "away_matches_used": away_n,
        "h2h_used":          len(h2h),
        "league_avg_goals":  round(league_avg, 2),
        "warning":           warning,
        "home_name":         home_name,
        "away_name":         away_name,
    }
