"""
AI-Supervised Model Calibration
================================
Daily automatic recalibration of predictor.py parameters supervised by Gemini.

Flow:
  1. _collect_bias_stats()  — statistical analysis of last N days
  2. run_daily_calibration() — sends stats to Gemini, receives new parameters
  3. Parameters saved to Gist under key "calibration"
  4. predictor.py loads them at import time via load_calibration()

Calibrated parameters:
  home_advantage   : float  1.05 – 1.45  (default 1.20)
  rho              : float -0.25 – 0.00  (default -0.13)
  decay_half_life  : int    20   – 90    (days, default 60)
  w_market         : float  0.00 – 0.40  (market weight, default 0.25)
  w_ema            : float  0.20 – 0.50  (EMA weight, default 0.35)
  xg_scale         : float  0.70 – 1.20  (global xG multiplier, default 1.00)
"""
from __future__ import annotations
import json
import requests
import streamlit as st
from datetime import date, timedelta, datetime
from typing import Dict, Any, Optional, List

# ── Parameter bounds (hard limits — Gemini cannot go outside these) ──
BOUNDS = {
    "home_advantage":  (1.05, 1.45),
    "rho":             (-0.25, 0.00),
    "decay_half_life": (20,    90),
    "w_market":        (0.00,  0.40),
    "w_ema":           (0.20,  0.50),
    "xg_scale":        (0.70,  1.20),
}

DEFAULTS = {
    "home_advantage":  1.20,
    "rho":             -0.13,
    "decay_half_life": 60,
    "w_market":        0.25,
    "w_ema":           0.35,
    "xg_scale":        1.00,
}


# ── Gist I/O ──────────────────────────────────────────────────────────

def _gist_id() -> str:
    return str(st.secrets.get("GIST_ID", "")).strip()

def _headers() -> Dict:
    token = st.secrets.get("GITHUB_TOKEN", "")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"}

@st.cache_data(ttl=300, show_spinner=False)
def _load_gist_json() -> Dict:
    gid = _gist_id()
    if not gid:
        return {}
    try:
        r = requests.get(f"https://api.github.com/gists/{gid}",
                         headers=_headers(), timeout=8)
        if r.status_code != 200:
            return {}
        files = r.json().get("files", {})
        for fname, fdata in files.items():
            if fname.lower() == "predictions.json":
                return json.loads(fdata.get("content", "{}") or "{}")
    except Exception:
        pass
    return {}

def _save_gist_json(data: Dict) -> bool:
    gid = _gist_id()
    if not gid:
        return False
    try:
        payload = {"files": {"predictions.json": {
            "content": json.dumps(data, ensure_ascii=False, indent=2)
        }}}
        r = requests.patch(f"https://api.github.com/gists/{gid}",
                           headers=_headers(), json=payload, timeout=15)
        if r.status_code == 200:
            _load_gist_json.clear()
            return True
    except Exception:
        pass
    return False


# ── Load / Save calibration ───────────────────────────────────────────

def load_calibration() -> Dict[str, Any]:
    """
    Load calibrated parameters from Gist.
    Returns defaults if not yet calibrated or Gist unavailable.
    Always validates against BOUNDS before returning.
    """
    try:
        data  = _load_gist_json()
        saved = data.get("_calibration", {})
        params = {}
        for key, default in DEFAULTS.items():
            val = saved.get(key, default)
            lo, hi = BOUNDS[key]
            params[key] = max(lo, min(hi, type(default)(val)))
        return params
    except Exception:
        return dict(DEFAULTS)


def save_calibration(params: Dict, reasoning: str = "",
                     stats_snapshot: Optional[Dict] = None) -> bool:
    """Save new calibration parameters + history entry to Gist."""
    data = _load_gist_json()
    history = data.get("_calibration_history", [])
    old_params = data.get("_calibration", dict(DEFAULTS))
    history.append({
        "date":       date.today().isoformat(),
        "old_params": old_params,
        "new_params": params,
        "reasoning":  reasoning[:800],
        "stats":      stats_snapshot or {},
    })
    data["_calibration"]          = params
    data["_calibration_history"]  = history[-30:]   # keep last 30 days
    data["_calibration_updated"]  = datetime.utcnow().isoformat(timespec="seconds")
    return _save_gist_json(data)


def get_calibration_history() -> List[Dict]:
    """Return calibration history for display."""
    try:
        data = _load_gist_json()
        return data.get("_calibration_history", [])
    except Exception:
        return []


# ── Bias statistics ───────────────────────────────────────────────────

def _collect_bias_stats(days_back: int = 14) -> Dict:
    """
    Analyse prediction errors over the last N days.
    Returns structured bias statistics for Gemini.
    """
    from predictions_db import load_predictions_range

    preds = load_predictions_range(days_back)
    finished = [p for p in preds if p.get("result") and p.get("accuracy")
                and p.get("prediction")]

    if len(finished) < 5:
        return {"error": f"Insufficient data: only {len(finished)} finished predictions"}

    n = len(finished)
    pr_list    = [p["prediction"] for p in finished]
    acc_list   = [p["accuracy"]   for p in finished]
    res_list   = [p["result"]     for p in finished]

    # 1X2 outcome rates
    pred_home  = sum(1 for a in acc_list if a["predicted_outcome"] == "home")
    pred_draw  = sum(1 for a in acc_list if a["predicted_outcome"] == "draw")
    pred_away  = sum(1 for a in acc_list if a["predicted_outcome"] == "away")
    act_home   = sum(1 for a in acc_list if a["actual_outcome"] == "home")
    act_draw   = sum(1 for a in acc_list if a["actual_outcome"] == "draw")
    act_away   = sum(1 for a in acc_list if a["actual_outcome"] == "away")

    # xG bias: predicted vs actual goals
    xg_h_pred  = [p.get("home_xg", 0) or 0 for p in pr_list]
    xg_a_pred  = [p.get("away_xg", 0) or 0 for p in pr_list]
    goals_h    = [r.get("home_goals", 0) or 0 for r in res_list]
    goals_a    = [r.get("away_goals", 0) or 0 for r in res_list]

    avg_xg_h_pred  = sum(xg_h_pred) / n
    avg_xg_a_pred  = sum(xg_a_pred) / n
    avg_goals_h    = sum(goals_h)    / n
    avg_goals_a    = sum(goals_a)    / n
    xg_bias_home   = avg_xg_h_pred - avg_goals_h   # positive = overestimating
    xg_bias_away   = avg_xg_a_pred - avg_goals_a

    # xG MAE
    mae_h = sum(abs(p-g) for p,g in zip(xg_h_pred, goals_h)) / n
    mae_a = sum(abs(p-g) for p,g in zip(xg_a_pred, goals_a)) / n

    # Over/Under bias
    pred_over25_count = sum(1 for p in pr_list if (p.get("over25") or 0) >= 0.5)
    act_over25_count  = sum(1 for r in res_list
                            if (r.get("home_goals",0)+r.get("away_goals",0)) > 2)

    # Accuracy by confidence band
    def _band_acc(lo, hi):
        band = [p for p, a in zip(pr_list, acc_list)
                if lo <= (p.get("confidence") or 0) <= hi]
        if not band:
            return {"n": 0}
        correct = sum(1 for p, a in zip(pr_list, acc_list)
                      if lo <= (p.get("confidence") or 0) <= hi
                      and a["outcome_correct"])
        return {"n": len(band), "accuracy": round(correct/len(band)*100, 1)}

    # Market alignment analysis
    market_aligned = [p for p in pr_list if p.get("has_market")]
    mkt_acc = None
    if market_aligned:
        mkt_correct = sum(1 for p, a in zip(pr_list, acc_list)
                          if p.get("has_market") and a["outcome_correct"])
        mkt_acc = round(mkt_correct / len(market_aligned) * 100, 1)

    # Home advantage signal: actual home win rate vs league average
    actual_home_win_rate = round(act_home / n * 100, 1)

    return {
        "n_matches":              n,
        "days_analysed":          days_back,
        "overall_1x2_accuracy":   round(sum(1 for a in acc_list if a["outcome_correct"])/n*100, 1),
        "outcome_rates": {
            "predicted": {"home": round(pred_home/n*100,1), "draw": round(pred_draw/n*100,1), "away": round(pred_away/n*100,1)},
            "actual":    {"home": round(act_home/n*100,1),  "draw": round(act_draw/n*100,1),  "away": round(act_away/n*100,1)},
        },
        "xg_bias": {
            "home_bias":     round(xg_bias_home, 3),   # + = overpredicting home goals
            "away_bias":     round(xg_bias_away, 3),
            "mae_home":      round(mae_h, 3),
            "mae_away":      round(mae_a, 3),
            "avg_pred_home": round(avg_xg_h_pred, 2),
            "avg_pred_away": round(avg_xg_a_pred, 2),
            "avg_act_home":  round(avg_goals_h, 2),
            "avg_act_away":  round(avg_goals_a, 2),
        },
        "over25_bias": {
            "predicted_over_pct": round(pred_over25_count/n*100, 1),
            "actual_over_pct":    round(act_over25_count/n*100, 1),
        },
        "accuracy_by_confidence": {
            "high_75_100":    _band_acc(75, 100),
            "medium_55_74":   _band_acc(55, 74),
            "low_35_54":      _band_acc(35, 54),
            "very_low_0_34":  _band_acc(0,  34),
        },
        "market_alignment_accuracy": mkt_acc,
        "actual_home_win_rate":      actual_home_win_rate,
    }


# ── Gemini calibration ────────────────────────────────────────────────

def run_daily_calibration(gemini_client, days_back: int = 14) -> Dict:
    """
    Full calibration run:
      1. Collect bias statistics
      2. Ask Gemini to analyse and suggest new parameters
      3. Validate and save

    Returns {"success": bool, "params": dict, "reasoning": str, "stats": dict}
    """
    # 1. Collect stats
    stats = _collect_bias_stats(days_back)
    if "error" in stats:
        return {"success": False, "error": stats["error"]}

    # 2. Load current params
    current = load_calibration()

    # 3. Build Gemini prompt
    prompt = f"""Ти си експерт по калибриране на статистически спортни модели.
Анализирай тези данни за представянето на Dixon-Coles ансамблов модел 
и предложи КОНКРЕТНИ нови стойности за параметрите.

ТЕКУЩИ ПАРАМЕТРИ:
{json.dumps(current, indent=2)}

СТАТИСТИКИ ЗА ПОСЛЕДНИТЕ {days_back} ДНИ ({stats["n_matches"]} МАЧА):
{json.dumps(stats, indent=2, ensure_ascii=False)}

ДОПУСТИМИ ГРАНИЦИ НА ПАРАМЕТРИТЕ:
{json.dumps(BOUNDS, indent=2)}

АНАЛИЗИРАЙ:
1. xg_bias.home_bias={stats["xg_bias"]["home_bias"]:.3f} → ако >+0.15, намали home_advantage и xg_scale
2. outcome_rates: predicted_home={stats["outcome_rates"]["predicted"]["home"]}% vs actual_home={stats["outcome_rates"]["actual"]["home"]}% → ако разликата >8%, коригирай home_advantage
3. over25_bias: predicted={stats["over25_bias"]["predicted_over_pct"]}% vs actual={stats["over25_bias"]["actual_over_pct"]}% → ако разликата >10%, коригирай xg_scale
4. market_alignment_accuracy={stats.get("market_alignment_accuracy","N/A")}% vs overall={stats["overall_1x2_accuracy"]}% → ако пазарът е по-точен с >5%, увеличи w_market
5. accuracy_by_confidence → ако ниска сигурност е по-точна от висока, намали decay_half_life

ЗАДЪЛЖИТЕЛНО върни САМО валиден JSON без markdown или коментари:
{{
  "home_advantage": <float>,
  "rho": <float>,
  "decay_half_life": <int>,
  "w_market": <float>,
  "w_ema": <float>,
  "xg_scale": <float>,
  "reasoning": "<на БЪЛГАРСКИ: 2-3 изречения защо тези промени>"
}}

Ако параметърът е оптимален — запази текущата стойност.
Правило: промени с максимум ±15% от текущата стойност на стъпка, за да избегнеш overfitting."""

    try:
        resp = gemini_client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=prompt,
        )
        raw = resp.text.strip()
        # Strip markdown fences if present
        raw = raw.replace("```json","").replace("```","").strip()
        suggested = json.loads(raw)
    except Exception as e:
        return {"success": False, "error": f"Gemini parse error: {e}"}

    # 4. Validate and clamp
    reasoning = suggested.pop("reasoning", "Без обяснение.")
    new_params = {}
    for key, default in DEFAULTS.items():
        val = suggested.get(key, current.get(key, default))
        lo, hi = BOUNDS[key]
        # Max ±15% change per calibration step
        cur_val = current.get(key, default)
        max_change = abs(cur_val) * 0.15
        val = max(cur_val - max_change, min(cur_val + max_change, float(val)))
        # Clamp to bounds
        new_params[key] = round(max(lo, min(hi, type(default)(val))), 4)

    # 5. Save
    ok = save_calibration(new_params, reasoning, stats)
    return {
        "success":   ok,
        "params":    new_params,
        "old_params":current,
        "reasoning": reasoning,
        "stats":     stats,
    }


def should_run_calibration() -> bool:
    """
    Returns True if daily calibration should run now.
    Triggers between 23:00-23:59 BG time, once per day.
    """
    from datetime import timezone, timedelta
    bg_now   = datetime.now(timezone(timedelta(hours=3)))
    if bg_now.hour != 23:
        return False
    try:
        data     = _load_gist_json()
        last_run = data.get("_calibration_updated", "")
        if last_run:
            last_date = last_run[:10]
            if last_date == date.today().isoformat():
                return False   # already ran today
    except Exception:
        pass
    return True
