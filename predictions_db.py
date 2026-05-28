"""
Predictions Database — GitHub Gist backend
============================================
Stores daily predictions and their outcomes persistently.

Setup (one-time):
  1. Go to github.com → Settings → Developer Settings → Personal Access Tokens
     → Tokens (classic) → New token → select scope: "gist"
  2. Create a new SECRET Gist at gist.github.com with one file: predictions.json
     Content: {}
  3. Add to Streamlit Secrets:
       GITHUB_TOKEN = "ghp_..."
       GIST_ID      = "abc123..."  (the ID from the gist URL)

Data schema:
  {
    "2026-05-27": {
      "12345": {                    ← event_id as string
        "event_id":   12345,
        "home":       "Arsenal",
        "away":       "Chelsea",
        "league":     "Premier League",
        "kickoff_bg": "20:00",
        "saved_at":   "2026-05-27T10:00:00",
        "prediction": {
          "home_win": 0.45,  "draw": 0.28,  "away_win": 0.27,
          "home_xg":  1.82,  "away_xg": 1.31,
          "btts":     0.62,  "over25":  0.58,
          "top_scoreline": {"h":2,"a":1,"prob":0.12},
          "confidence":       72,
          "data_confidence":  85,
          "model_confidence": 60,
          "conf_label":       "Умерена",
        },
        "result":   null,      ← filled after match
        "accuracy": null       ← filled after match
      }
    }
  }
"""
from __future__ import annotations
import json
import requests
import streamlit as st
from datetime import date, datetime, timedelta
from typing import Dict, Any, Optional, List

GIST_FILENAME = "predictions.json"
GITHUB_API    = "https://api.github.com"


# ── GitHub Gist I/O ───────────────────────────────────────────────

def _headers() -> Dict:
    token = st.secrets.get("GITHUB_TOKEN","")
    if not token:
        return {}
    # GitHub accepts both "token xxx" and "Bearer xxx" for PATs
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }

def _gist_id() -> str:
    return str(st.secrets.get("GIST_ID","")).strip()


@st.cache_data(ttl=30, show_spinner=False)
def _load_raw() -> Dict:
    """Load all predictions from Gist. Cached 30s."""
    gid = _gist_id()
    if not gid:
        return {}
    try:
        r = requests.get(f"{GITHUB_API}/gists/{gid}",
                         headers=_headers(), timeout=8)
        if r.status_code != 200:
            return {}
        files   = r.json().get("files", {})
        # Try exact name first, then case-insensitive
        content = None
        for fname, fdata in files.items():
            if fname.lower() == GIST_FILENAME.lower():
                content = fdata.get("content", "{}")
                break
        if content is None:
            return {}
        return json.loads(content or "{}")
    except Exception:
        return {}


def _save_raw(data: Dict) -> tuple:
    """
    Write all predictions to Gist.
    Returns (success: bool, error_msg: str).
    """
    gid = _gist_id()
    if not gid:
        return False, "GIST_ID не е настроен в Secrets"
    token = st.secrets.get("GITHUB_TOKEN","")
    if not token:
        return False, "GITHUB_TOKEN не е настроен в Secrets"
    try:
        payload = {"files": {GIST_FILENAME: {
            "content": json.dumps(data, ensure_ascii=False, indent=2)
        }}}
        r = requests.patch(
            f"{GITHUB_API}/gists/{gid}",
            headers=_headers(),
            json=payload,
            timeout=15,
        )
        if r.status_code == 200:
            _load_raw.clear()
            return True, ""
        # Parse GitHub error message
        try:
            err_detail = r.json().get("message", r.text[:200])
        except Exception:
            err_detail = r.text[:200]
        return False, f"HTTP {r.status_code}: {err_detail}"
    except Exception as e:
        return False, f"Exception: {e}"


# ── Public API ────────────────────────────────────────────────────

def is_configured() -> bool:
    return bool(_gist_id() and st.secrets.get("GITHUB_TOKEN",""))


def save_prediction(event_id: int, home: str, away: str,
                    league: str, kickoff_bg: str,
                    prediction: Dict) -> bool:
    """
    Save a pre-match prediction. Safe to call multiple times —
    skips if already saved for this event_id today.
    """
    today = date.today().isoformat()
    data  = _load_raw()
    day   = data.setdefault(today, {})
    eid_s = str(event_id)

    if eid_s in day:
        return True   # already saved today

    day[eid_s] = {
        "event_id":   event_id,
        "home":       home,
        "away":       away,
        "league":     league,
        "kickoff_bg": kickoff_bg,
        "saved_at":   datetime.utcnow().isoformat(timespec="seconds"),
        "prediction": {
            "home_win":        prediction.get("home_win"),
            "draw":            prediction.get("draw"),
            "away_win":        prediction.get("away_win"),
            "home_xg":         prediction.get("home_xg"),
            "away_xg":         prediction.get("away_xg"),
            "btts":            prediction.get("btts"),
            "over25":          prediction.get("over25"),
            "top_scoreline":   (prediction.get("top_scorelines") or [{}])[0],
            "confidence":      prediction.get("confidence"),
            "data_confidence": prediction.get("data_confidence"),
            "model_confidence":prediction.get("model_confidence"),
            "conf_label":      prediction.get("conf_label","—"),
        },
        "result":   None,
        "accuracy": None,
    }
    ok, err = _save_raw(data)
    if not ok:
        # Surface error so caller can log it
        raise RuntimeError(f"Gist write failed: {err}")
    return True


def update_result(event_id: int, target_date: str,
                  home_goals: int, away_goals: int) -> bool:
    """
    Record the actual result and compute accuracy vs prediction.
    Searches target_date first, then all other dates as fallback
    (in case the match was saved on a different calendar day).
    """
    data  = _load_raw()
    eid_s = str(event_id)

    # Find which date this event was saved under
    found_date = None
    if eid_s in data.get(target_date, {}):
        found_date = target_date
    else:
        # Search all dates — match might have been saved on a different day
        for d, day_data in data.items():
            if eid_s in day_data:
                found_date = d
                break

    if not found_date:
        return False   # never saved a prediction for this match

    entry = data[found_date][eid_s]
    if entry.get("result"):
        return True   # already recorded

    pred  = entry.get("prediction", {})
    entry["result"] = {"home_goals": home_goals, "away_goals": away_goals}

    # ── Accuracy ──────────────────────────────────────────────────
    # Predicted outcome
    hw = pred.get("home_win",0); dw = pred.get("draw",0); aw = pred.get("away_win",0)
    if hw >= dw and hw >= aw:   pred_outcome = "home"
    elif dw >= hw and dw >= aw: pred_outcome = "draw"
    else:                       pred_outcome = "away"

    # Actual outcome
    if home_goals >  away_goals: actual_outcome = "home"
    elif home_goals == away_goals: actual_outcome = "draw"
    else:                        actual_outcome = "away"

    # Predicted top scoreline
    top_sc = pred.get("top_scoreline",{}) or {}
    sc_correct = (top_sc.get("h") == home_goals and
                  top_sc.get("a") == away_goals)

    # BTTS
    btts_actual    = home_goals > 0 and away_goals > 0
    btts_pred      = (pred.get("btts") or 0) >= 0.5
    btts_correct   = btts_actual == btts_pred

    # Over 2.5
    over25_actual  = home_goals + away_goals > 2
    over25_pred    = (pred.get("over25") or 0) >= 0.5
    over25_correct = over25_actual == over25_pred

    # xG error
    xg_h_err = (abs(pred.get("home_xg",0) - home_goals)
                if pred.get("home_xg") is not None else None)
    xg_a_err = (abs(pred.get("away_xg",0) - away_goals)
                if pred.get("away_xg") is not None else None)

    entry["accuracy"] = {
        "outcome_correct":  actual_outcome == pred_outcome,
        "predicted_outcome":pred_outcome,
        "actual_outcome":   actual_outcome,
        "scoreline_correct":sc_correct,
        "btts_correct":     btts_correct,
        "over25_correct":   over25_correct,
        "xg_error_home":    round(xg_h_err,2) if xg_h_err is not None else None,
        "xg_error_away":    round(xg_a_err,2) if xg_a_err is not None else None,
    }
    ok, err = _save_raw(data)
    if not ok:
        raise RuntimeError(f"Gist write failed: {err}")
    return True



def save_predictions_batch(matches: list) -> tuple:
    """
    Save ALL predictions in a single Gist PATCH (one HTTP request).
    matches: list of {event_id, home, away, league, kickoff_bg, prediction}.
    Returns (saved, skipped, error_msg).
    """
    today = date.today().isoformat()
    data  = _load_raw()
    day   = data.setdefault(today, {})
    saved = skipped = 0
    for m in matches:
        eid_s = str(m["event_id"])
        if eid_s in day:
            skipped += 1; continue
        pred = m["prediction"]
        day[eid_s] = {
            "event_id": m["event_id"], "home": m["home"], "away": m["away"],
            "league": m["league"], "kickoff_bg": m["kickoff_bg"],
            "saved_at": datetime.utcnow().isoformat(timespec="seconds"),
            "prediction": {
                "home_win":         pred.get("home_win"),
                "draw":             pred.get("draw"),
                "away_win":         pred.get("away_win"),
                "home_xg":          pred.get("home_xg"),
                "away_xg":          pred.get("away_xg"),
                "btts":             pred.get("btts"),
                "over25":           pred.get("over25"),
                "top_scoreline":    (pred.get("top_scorelines") or [{}])[0],
                "confidence":       pred.get("confidence"),
                "data_confidence":  pred.get("data_confidence"),
                "model_confidence": pred.get("model_confidence"),
                "conf_label":       pred.get("conf_label", "—"),
            },
            "result": None, "accuracy": None,
        }
        saved += 1
    if saved == 0:
        return 0, skipped, ""
    ok, err = _save_raw(data)
    return (saved, skipped, "") if ok else (0, skipped, err)


def update_results_batch(finished_matches: list) -> tuple:
    """
    Update results for ALL finished matches in a single Gist PATCH.
    finished_matches: list of {event_id, target_date, home_goals, away_goals}.
    Returns (updated, error_msg).
    """
    data = _load_raw(); updated = 0
    for m in finished_matches:
        eid_s = str(m["event_id"])
        hg = m["home_goals"]; ag = m["away_goals"]; td = m["target_date"]
        found = td if eid_s in data.get(td, {}) else next(
            (d for d, dd in data.items() if eid_s in dd), None)
        if not found: continue
        entry = data[found][eid_s]
        if entry.get("result"): continue
        pred = entry.get("prediction", {})
        entry["result"] = {"home_goals": hg, "away_goals": ag}
        hw = pred.get("home_win",0); dw = pred.get("draw",0); aw = pred.get("away_win",0)
        po = "home" if hw>=dw and hw>=aw else "draw" if dw>=hw and dw>=aw else "away"
        ao = "home" if hg>ag else "draw" if hg==ag else "away"
        sc = pred.get("top_scoreline", {}) or {}
        entry["accuracy"] = {
            "outcome_correct":   ao == po,
            "predicted_outcome": po, "actual_outcome": ao,
            "scoreline_correct": sc.get("h")==hg and sc.get("a")==ag,
            "btts_correct":      (hg>0 and ag>0)==((pred.get("btts") or 0)>=0.5),
            "over25_correct":    (hg+ag>2)==((pred.get("over25") or 0)>=0.5),
            "xg_error_home":     round(abs(pred.get("home_xg",0)-hg),2) if pred.get("home_xg") is not None else None,
            "xg_error_away":     round(abs(pred.get("away_xg",0)-ag),2) if pred.get("away_xg") is not None else None,
        }
        updated += 1
    if updated == 0: return 0, ""
    ok, err = _save_raw(data)
    return (updated, "") if ok else (0, err)


def load_predictions_for_date(target_date: str) -> List[Dict]:
    data = _load_raw()
    return list(data.get(target_date, {}).values())


def load_predictions_range(days_back: int = 30) -> List[Dict]:
    """Load all predictions from the last N days."""
    data    = _load_raw()
    results = []
    for i in range(days_back + 1):
        d   = (date.today() - timedelta(days=i)).isoformat()
        day = data.get(d, {})
        for entry in day.values():
            results.append({**entry, "date": d})
    return results


def compute_stats(predictions: List[Dict],
                  min_confidence: int = 0) -> Dict:
    """
    Compute accuracy statistics for a list of prediction entries.
    Filters out entries without results and below min_confidence.
    """
    finished = [
        p for p in predictions
        if p.get("result") and p.get("accuracy")
        and (p.get("prediction",{}).get("confidence") or 0) >= min_confidence
    ]
    if not finished:
        return {"n": 0}

    n          = len(finished)
    outcome_ok = sum(1 for p in finished if p["accuracy"]["outcome_correct"])
    sc_ok      = sum(1 for p in finished if p["accuracy"]["scoreline_correct"])
    btts_ok    = sum(1 for p in finished if p["accuracy"]["btts_correct"])
    o25_ok     = sum(1 for p in finished if p["accuracy"]["over25_correct"])

    xg_errs    = [p["accuracy"]["xg_error_home"] for p in finished
                  if p["accuracy"].get("xg_error_home") is not None]
    xg_errs   += [p["accuracy"]["xg_error_away"] for p in finished
                  if p["accuracy"].get("xg_error_away") is not None]
    avg_xg_err = round(sum(xg_errs)/len(xg_errs),2) if xg_errs else None

    return {
        "n":             n,
        "outcome_pct":   round(outcome_ok/n*100, 1),
        "scoreline_pct": round(sc_ok/n*100,      1),
        "btts_pct":      round(btts_ok/n*100,    1),
        "over25_pct":    round(o25_ok/n*100,     1),
        "avg_xg_error":  avg_xg_err,
    }
