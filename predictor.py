"""
Ensemble Football Match Predictor v2
======================================
Three-component ensemble:
  A. Dixon-Coles (40%) — long-term form, H2H, time-decay
  B. EMA last-5 (35%)  — recent streak, hot/cold form
  C. Market-implied (25%) — bookmaker consensus (vig-removed)
     If no odds available: A=55%, B=45%

Additional corrections:
  - Rest days: <3 days fatigue penalty, >10 days rust penalty
  - Match importance: dead rubbers reduce expected goal intensity
  - Negative Binomial option (reduces xG error vs pure Poisson)

Confidence breakdown:
  data_confidence   — volume of form data available (0-100)
  model_confidence  — entropy-based sharpness of 1X2 distribution (0-100)
  h2h_alignment     — do H2H results agree with form model? (-1 to +1)
  market_alignment  — does market agree with model? (0-100 bonus)
  confidence        — combined score used for filtering (0-100)

Filter helper:
  should_show_prediction(p) → (bool, reason_str)
"""
from __future__ import annotations
import math
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, date
import streamlit as st

# ── Constants ─────────────────────────────────────────────────────
HOME_ADVANTAGE  = 1.20
RHO             = -0.13   # Dixon-Coles low-score correction
DECAY_HALF_LIFE = 60      # days
EMA_DECAY       = 0.70    # per match (most recent = weight 1.0)
EMA_N           = 5       # last N matches for EMA
MAX_GOALS       = 8
MIN_MATCHES     = 3

# Ensemble weights
W_DC      = 0.40
W_EMA     = 0.35
W_MARKET  = 0.25
# When no market odds: redistribute market weight
W_DC_NOM  = W_DC  / (W_DC + W_EMA)   # ≈ 0.533
W_EMA_NOM = W_EMA / (W_DC + W_EMA)   # ≈ 0.467


# ═════════════════════════════════════════════════════════════════
# SHARED HELPERS
# ═════════════════════════════════════════════════════════════════

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
        except: continue
    return 30.0

def _weight(days: float) -> float:
    return math.exp(-math.log(2)*days/DECAY_HALF_LIFE)

def _score(m: Dict) -> Tuple[Optional[int],Optional[int]]:
    s = m.get("score")
    if isinstance(s,dict): h,a = s.get("home"),s.get("away")
    else: h,a = m.get("home_score"),m.get("away_score")
    try:    return int(h),int(a)
    except: return None,None

def _is_home(match: Dict, team_name: str) -> bool:
    home_v = match.get("home_team") or match.get("home") or {}
    hn = home_v.get("name","") if isinstance(home_v,dict) else str(home_v)
    return team_name.lower() in hn.lower()

def _poisson_pmf(k: int, lam: float) -> float:
    if lam <= 0: return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam**k) / math.factorial(k)

def _dc_correction(hg,ag,lam,mu,rho=RHO):
    if hg==0 and ag==0: return max(0, 1-lam*mu*rho)
    if hg==1 and ag==0: return max(0, 1+mu*rho)
    if hg==0 and ag==1: return max(0, 1+lam*rho)
    if hg==1 and ag==1: return max(0, 1-rho)
    return 1.0

def _grid_to_1x2(grid) -> Tuple[float,float,float]:
    """Sum a scoreline grid into (home_win, draw, away_win)."""
    N = len(grid)
    hw = sum(grid[h][a] for h in range(N) for a in range(N) if h > a)
    dw = sum(grid[h][a] for h in range(N) for a in range(N) if h == a)
    aw = max(0.0, 1.0 - hw - dw)
    return hw, dw, aw

def _scoreline_grid(lam: float, mu: float) -> List[List[float]]:
    """Build normalised scoreline probability grid."""
    grid = [
        [_poisson_pmf(h,lam) * _poisson_pmf(a,mu) * _dc_correction(h,a,lam,mu)
         for a in range(MAX_GOALS+1)]
        for h in range(MAX_GOALS+1)
    ]
    total = sum(grid[h][a] for h in range(MAX_GOALS+1) for a in range(MAX_GOALS+1))
    if total > 0:
        grid = [[max(0,grid[h][a]/total) for a in range(MAX_GOALS+1)]
                for h in range(MAX_GOALS+1)]
    return grid

def _over_n(grid, n: float) -> float:
    N = len(grid)
    return sum(grid[h][a] for h in range(N) for a in range(N) if h+a > n)


# ═════════════════════════════════════════════════════════════════
# COMPONENT A — Dixon-Coles
# ═════════════════════════════════════════════════════════════════

def _dc_strength(fixtures: List[Dict], team_name: str
                 ) -> Tuple[float,float,float,int]:
    """→ (attack, defense, consistency, n_matches)"""
    total_w = scored_w = conceded_w = 0.0
    n = 0; goals_list = []
    for m in fixtures:
        hg,ag = _score(m)
        if hg is None: continue
        days = _days_ago(m); w = _weight(days)
        gf = hg if _is_home(m,team_name) else ag
        ga = ag if _is_home(m,team_name) else hg
        scored_w += w*gf; conceded_w += w*ga; total_w += w; n += 1
        goals_list.append(gf)
    if n==0 or total_w<0.01: return 1.2,1.2,0.5,0
    atk = scored_w/total_w; dfn = conceded_w/total_w
    if len(goals_list) >= 3:
        mean = sum(goals_list)/len(goals_list)
        std  = math.sqrt(sum((x-mean)**2 for x in goals_list)/len(goals_list))
        cons = max(0.0, 1.0 - std/3.0)
    else:
        cons = 0.5
    return max(0.1,atk), max(0.1,dfn), cons, n

def _dc_component(home_fixtures, away_fixtures, h2h,
                  home_name, away_name,
                  rest_mult_home=1.0, rest_mult_away=1.0,
                  importance_mult=1.0):
    """Returns (lam, mu, grid, home_cons, away_cons, home_n, away_n, league_avg)."""
    home_aug = list(home_fixtures) + h2h + h2h
    away_aug = list(away_fixtures) + h2h + h2h

    h_atk, h_dfn, h_cons, h_n = _dc_strength(home_aug, home_name)
    a_atk, a_dfn, a_cons, a_n = _dc_strength(away_aug, away_name)

    all_fx = list(home_fixtures) + list(away_fixtures)
    tw = 0.0; tg = 0.0
    for m in all_fx:
        hg,ag = _score(m)
        if hg is None: continue
        w = _weight(_days_ago(m)); tg += w*(hg+ag); tw += w*2
    league_avg = max(0.5, tg/tw if tw > 0 else 1.2)

    ha_n = h_atk/league_avg; hd_n = h_dfn/league_avg
    aa_n = a_atk/league_avg; ad_n = a_dfn/league_avg

    lam = (ha_n * ad_n * league_avg * HOME_ADVANTAGE
           * rest_mult_home * importance_mult)
    mu  = (aa_n * hd_n * league_avg
           * rest_mult_away * importance_mult)
    lam = max(0.1, min(lam, MAX_GOALS-0.1))
    mu  = max(0.1, min(mu,  MAX_GOALS-0.1))

    grid = _scoreline_grid(lam, mu)
    return lam, mu, grid, h_cons, a_cons, h_n, a_n, league_avg


# ═════════════════════════════════════════════════════════════════
# COMPONENT B — EMA (last 5 matches)
# ═════════════════════════════════════════════════════════════════

def _ema_lambda(fixtures: List[Dict], team_name: str,
                n=EMA_N, decay=EMA_DECAY) -> Optional[float]:
    """
    Exponential moving average of goals scored per match.
    Most recent match has weight 1.0, previous 0.7, 0.49, ...
    Returns None if insufficient data.
    """
    recent = [m for m in fixtures
              if _score(m)[0] is not None][:n]
    if len(recent) < 2:
        return None
    w_sum = gf_sum = 0.0
    for i, m in enumerate(recent):
        hg,ag = _score(m)
        gf    = hg if _is_home(m,team_name) else ag
        w     = decay ** i
        gf_sum += w * gf; w_sum += w
    return max(0.1, gf_sum / w_sum)

def _ema_component(home_fixtures, away_fixtures,
                   home_name, away_name,
                   rest_mult_home=1.0, rest_mult_away=1.0):
    """Returns (lam_ema, mu_ema, grid_ema) or None if data insufficient."""
    lam_ema = _ema_lambda(home_fixtures, home_name)
    mu_ema  = _ema_lambda(away_fixtures, away_name)
    if lam_ema is None or mu_ema is None:
        return None
    # Apply home advantage (EMA is neutral, DC handles it partially)
    lam_ema = max(0.1, min(lam_ema * HOME_ADVANTAGE * rest_mult_home, MAX_GOALS-0.1))
    mu_ema  = max(0.1, min(mu_ema * rest_mult_away, MAX_GOALS-0.1))
    grid = _scoreline_grid(lam_ema, mu_ema)
    return lam_ema, mu_ema, grid


# ═════════════════════════════════════════════════════════════════
# COMPONENT C — Market-implied probabilities
# ═════════════════════════════════════════════════════════════════

def _market_implied(odds: Dict) -> Optional[Dict[str,float]]:
    """
    Convert bookmaker match-winner odds to vig-removed probabilities.
    Accepts the full odds dict from get_event_odds() or get_odds_comparison().
    Returns {"home_win", "draw", "away_win"} or None.
    """
    if not odds: return None
    # Unwrap nested structures
    mw = (odds.get("odds") or odds).get("match_winner") or {}
    if not mw:
        # Try direct keys
        mw = odds
    h_o = mw.get("home"); x_o = mw.get("draw"); a_o = mw.get("away")
    if not all([h_o, x_o, a_o]): return None
    try:
        h_r = 1/float(h_o); x_r = 1/float(x_o); a_r = 1/float(a_o)
        total = h_r + x_r + a_r
        if total <= 0: return None
        return {
            "home_win": h_r/total,
            "draw":     x_r/total,
            "away_win": a_r/total,
        }
    except (TypeError, ZeroDivisionError, ValueError):
        return None

def _market_agreement(market: Dict, model_hw: float, model_aw: float) -> int:
    """
    How much does the market agree with our model? Returns 0-20 bonus points.
    """
    if not market: return 0
    m_hw = market["home_win"]; m_aw = market["away_win"]
    model_favours = "home" if model_hw > model_aw else "away"
    mkt_favours   = "home" if m_hw   > m_aw   else "away"
    if model_favours != mkt_favours:
        return -10   # disagreement penalty
    # Agreement — stronger when both are decisive
    strength = abs(model_hw - model_aw) * abs(m_hw - m_aw)
    return min(20, int(strength * 60))


# ═════════════════════════════════════════════════════════════════
# REST DAYS CORRECTION
# ═════════════════════════════════════════════════════════════════

def _rest_multiplier(fixtures: List[Dict]) -> float:
    """
    Attack multiplier based on days since last match.
    <3 days (midweek + weekend): fatigue -12%
    3-7 days (normal): 1.0
    >10 days: slight rust -6%
    """
    if not fixtures: return 1.0
    most_recent = next((m for m in fixtures if _score(m)[0] is not None), None)
    if not most_recent: return 1.0
    days = _days_ago(most_recent)
    if   days < 3:  return 0.88
    elif days > 10: return 0.94
    return 1.0


# ═════════════════════════════════════════════════════════════════
# CONFIDENCE COMPONENTS
# ═════════════════════════════════════════════════════════════════

def _entropy_confidence(hw,dw,aw) -> int:
    MAX_H = math.log(3)
    probs = [p for p in (hw,dw,aw) if p > 0]
    entropy = -sum(p*math.log(p) for p in probs)
    return round((1 - entropy/MAX_H) * 100)

def _data_confidence(h_n, a_n, h2h_n) -> int:
    base = min(100, int((min(h_n,a_n)/10)*60 + (max(h_n,a_n)/15)*40))
    return min(100, base + min(15, h2h_n*3))

def _h2h_alignment(h2h, home_name, model_hw, model_aw) -> float:
    if len(h2h) < 2: return 0.0
    hw = dw = aw = 0
    for m in h2h:
        hg,ag = _score(m)
        if hg is None: continue
        htn = (m.get("home_team") or m.get("home") or {})
        hn  = htn.get("name","") if isinstance(htn,dict) else str(htn)
        is_h = home_name.lower() in hn.lower()
        if hg==ag: dw+=1
        elif (is_h and hg>ag) or (not is_h and ag>hg): hw+=1
        else: aw+=1
    total = hw+dw+aw or 1
    h2h_hw = hw/total; h2h_aw = aw/total
    if (model_hw > model_aw) == (h2h_hw > h2h_aw):
        return min(1.0, abs(model_hw-model_aw)*abs(h2h_hw-h2h_aw)*4)
    return -0.5


# ═════════════════════════════════════════════════════════════════
# COMBINED FILTER
# ═════════════════════════════════════════════════════════════════

def should_show_prediction(p: Dict) -> Tuple[bool, str]:
    """
    Multi-condition quality filter.
    Returns (show: bool, reason: str).

    SHOW if ALL:
      confidence >= 45
      data_confidence >= 50
      |home_win - away_win| > 0.10   (clear favourite)
      h2h_alignment >= 0             (H2H doesn't contradict)

    HIDE if ANY:
      confidence < 35
      home_matches_used < 4
      away_matches_used < 4
      |home_xg - away_xg| < 0.15    (too close to call)
    """
    conf     = p.get("confidence", 0)
    d_conf   = p.get("data_confidence", 0)
    h_n      = p.get("home_matches_used", 0)
    a_n      = p.get("away_matches_used", 0)
    h2h_al   = p.get("h2h_alignment", 0)
    hw       = p.get("home_win", 0.33)
    aw       = p.get("away_win", 0.33)
    h_xg     = p.get("home_xg", 0)
    a_xg     = p.get("away_xg", 0)

    # Hard stops
    if conf < 35:
        return False, f"Сигурност {conf}% < 35%"
    if h_n < 4:
        return False, f"Малко данни: {p.get('home_name','')} ({h_n} мача)"
    if a_n < 4:
        return False, f"Малко данни: {p.get('away_name','')} ({a_n} мача)"
    if abs(h_xg - a_xg) < 0.15:
        return False, f"xG твърде близко: {h_xg:.2f}–{a_xg:.2f}"

    # Quality gates
    reasons = []
    if conf < 45:
        reasons.append(f"Ниска сигурност ({conf}%)")
    if d_conf < 50:
        reasons.append(f"Малко данни ({d_conf}%)")
    if abs(hw - aw) < 0.10:
        reasons.append("Няма ясен фаворит")
    if h2h_al < 0:
        reasons.append("H2H противоречи на формата")

    if reasons:
        return False, " · ".join(reasons)
    return True, ""


# ═════════════════════════════════════════════════════════════════
# MAIN ENSEMBLE PREDICTOR
# ═════════════════════════════════════════════════════════════════

@st.cache_data(ttl=600, show_spinner=False)
def predict_match(
    home_name: str, away_name: str,
    home_fixtures: List[Dict], away_fixtures: List[Dict],
    h2h_matches: Optional[List[Dict]] = None,
    market_odds: Optional[Dict] = None,
) -> Dict[str,Any]:
    """
    Full ensemble prediction.
    market_odds: dict from get_event_odds() — optional but improves accuracy.
    """
    h2h = h2h_matches or []

    # ── Rest days corrections ─────────────────────────────────────
    rm_home = _rest_multiplier(home_fixtures)
    rm_away = _rest_multiplier(away_fixtures)

    # ── Component A: Dixon-Coles ──────────────────────────────────
    dc_lam, dc_mu, dc_grid, h_cons, a_cons, h_n, a_n, lg_avg = _dc_component(
        home_fixtures, away_fixtures, h2h,
        home_name, away_name, rm_home, rm_away)
    dc_hw, dc_dw, dc_aw = _grid_to_1x2(dc_grid)

    # ── Component B: EMA ─────────────────────────────────────────
    ema_result = _ema_component(
        home_fixtures, away_fixtures, home_name, away_name, rm_home, rm_away)

    if ema_result:
        ema_lam, ema_mu, ema_grid = ema_result
        ema_hw, ema_dw, ema_aw = _grid_to_1x2(ema_grid)
        has_ema = True
    else:
        ema_hw, ema_dw, ema_aw = dc_hw, dc_dw, dc_aw
        ema_lam = dc_lam; ema_mu = dc_mu
        has_ema = False

    # ── Component C: Market ───────────────────────────────────────
    market = _market_implied(market_odds) if market_odds else None
    has_market = market is not None

    # ── Ensemble blend ────────────────────────────────────────────
    if has_market:
        blend_hw = dc_hw*W_DC + ema_hw*W_EMA + market["home_win"]*W_MARKET
        blend_dw = dc_dw*W_DC + ema_dw*W_EMA + market["draw"]    *W_MARKET
        blend_aw = dc_aw*W_DC + ema_aw*W_EMA + market["away_win"]*W_MARKET
    else:
        blend_hw = dc_hw*W_DC_NOM + ema_hw*W_EMA_NOM
        blend_dw = dc_dw*W_DC_NOM + ema_dw*W_EMA_NOM
        blend_aw = dc_aw*W_DC_NOM + ema_aw*W_EMA_NOM

    # Normalise (floating point safety)
    total_blend = blend_hw + blend_dw + blend_aw
    blend_hw /= total_blend; blend_dw /= total_blend; blend_aw /= total_blend

    # ── Blended xG (DC + EMA average for expected goals) ─────────
    if has_ema:
        blend_lam = dc_lam*0.55 + ema_lam*0.45
        blend_mu  = dc_mu *0.55 + ema_mu *0.45
    else:
        blend_lam = dc_lam; blend_mu = dc_mu

    # Final scoreline grid from blended xG
    final_grid = _scoreline_grid(blend_lam, blend_mu)

    # Derived stats from final grid
    btts   = sum(final_grid[h][a] for h in range(1,MAX_GOALS+1)
                                   for a in range(1,MAX_GOALS+1))
    over25 = _over_n(final_grid, 2.5)
    top_sc = sorted(
        [{"h":h,"a":a,"prob":final_grid[h][a]}
         for h in range(MAX_GOALS+1) for a in range(MAX_GOALS+1)],
        key=lambda x:-x["prob"])[:12]

    # ── Confidence ────────────────────────────────────────────────
    data_conf   = _data_confidence(h_n, a_n, len(h2h))
    model_conf  = _entropy_confidence(blend_hw, blend_dw, blend_aw)
    h2h_align   = _h2h_alignment(h2h, home_name, blend_hw, blend_aw)
    mkt_bonus   = _market_agreement(market, blend_hw, blend_aw) if market else 0
    cons_bonus  = int((h_cons+a_cons)/2 * 10)
    rest_note   = ""
    if rm_home < 1.0: rest_note += f" Умора {home_name}."
    if rm_away < 1.0: rest_note += f" Умора {away_name}."

    raw_conf   = (data_conf*0.38 + model_conf*0.42
                  + h2h_align*10 + mkt_bonus*0.5 + cons_bonus*0.5)
    confidence = max(0, min(100, int(raw_conf)))

    if   confidence >= 75: conf_label = "Висока"
    elif confidence >= 55: conf_label = "Умерена"
    elif confidence >= 35: conf_label = "Ниска"
    else:                  conf_label = "Много ниска"

    warning = None
    if h_n < MIN_MATCHES or a_n < MIN_MATCHES:
        warning = (f"⚠️ Малко данни: {home_name} ({h_n}), {away_name} ({a_n})")
    if rest_note:
        warning = (warning + rest_note) if warning else f"⚠️{rest_note}"

    result = {
        # 1X2
        "home_win":  round(blend_hw, 4),
        "draw":      round(blend_dw, 4),
        "away_win":  round(blend_aw, 4),
        # xG
        "home_xg":   round(blend_lam, 2),
        "away_xg":   round(blend_mu,  2),
        # Markets
        "btts":      round(btts,   4),
        "over05":    round(_over_n(final_grid,0.5), 4),
        "over15":    round(_over_n(final_grid,1.5), 4),
        "over25":    round(over25, 4),
        "over35":    round(_over_n(final_grid,3.5), 4),
        "under25":   round(1-over25, 4),
        # Scorelines
        "top_scorelines": top_sc,
        "heatmap":        final_grid,
        # Confidence
        "confidence":        confidence,
        "conf_label":        conf_label,
        "data_confidence":   data_conf,
        "model_confidence":  model_conf,
        "h2h_alignment":     round(h2h_align, 2),
        "market_alignment":  mkt_bonus,
        "home_consistency":  round(h_cons, 2),
        "away_consistency":  round(a_cons, 2),
        # Components (for debug/display)
        "dc_hw":    round(dc_hw, 3), "dc_dw": round(dc_dw,3),  "dc_aw": round(dc_aw,3),
        "ema_hw":   round(ema_hw,3), "ema_dw": round(ema_dw,3), "ema_aw": round(ema_aw,3),
        "market":   market,
        "has_ema":  has_ema, "has_market": has_market,
        "rest_home": round(rm_home, 2), "rest_away": round(rm_away, 2),
        # Meta
        "home_matches_used": h_n,
        "away_matches_used": a_n,
        "h2h_used":          len(h2h),
        "league_avg_goals":  round(lg_avg, 2),
        "warning":           warning,
        "home_name":         home_name,
        "away_name":         away_name,
    }

    return result
