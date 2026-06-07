"""
Tennis ML predictor — зарежда v4 LightGBM модели от Google Drive / GitHub
и изчислява winner probability + over/under games.

Ако моделите не са налични, връща None и UI използва Bzzoiro predictions.
"""
from __future__ import annotations
import pickle, json, os
import streamlit as st
import numpy as np
from typing import Dict, Optional, Tuple

# Пътища — Streamlit Cloud търси в root на repo-то
MODEL_DIR   = os.path.join(os.path.dirname(__file__), "models")
FEATURE_FILE = os.path.join(MODEL_DIR, "feature_list.json")

# Mapping тур → файл
TOUR_MAP = {
    "ATP":    "winner_atp_model.pkl",
    "WTA":    "winner_wta_model.pkl",
    "CH_ITF": "winner_ch_itf_model.pkl",
}
GAMES_FILE = "games_regressor.pkl"

@st.cache_resource(show_spinner=False)
def _load_models() -> Tuple[Dict, object, list, list]:
    """Зарежда всички модели веднъж при стартиране."""
    if not os.path.exists(FEATURE_FILE):
        return {}, None, [], []
    try:
        with open(FEATURE_FILE) as f:
            meta = json.load(f)
        winner_features = meta.get("winner_features", [])
        games_features  = meta.get("games_features",  [])

        tour_models = {}
        for tour, fname in TOUR_MAP.items():
            fpath = os.path.join(MODEL_DIR, fname)
            if os.path.exists(fpath):
                with open(fpath, "rb") as f:
                    tour_models[tour] = pickle.load(f)

        games_model = None
        gpath = os.path.join(MODEL_DIR, GAMES_FILE)
        if os.path.exists(gpath):
            with open(gpath, "rb") as f:
                games_model = pickle.load(f)

        return tour_models, games_model, winner_features, games_features
    except Exception as e:
        return {}, None, [], []

def _tour_group(circuit: str) -> str:
    c = (circuit or "").upper()
    if "WTA" in c: return "WTA"
    if "ATP" in c: return "ATP"
    return "CH_ITF"

def _safe(val, default=0.0):
    try:
        v = float(val)
        return v if np.isfinite(v) else default
    except: return default

def predict_winner(
    p1_rank:        Optional[float],
    p2_rank:        Optional[float],
    p1_rank_pts:    Optional[float],
    p2_rank_pts:    Optional[float],
    p1_elo:         float,
    p2_elo:         float,
    p1_adj_elo:     float,
    p2_adj_elo:     float,
    surface:        str,
    circuit:        str,
    best_of:        int   = 3,
    tourney_level:  float = 2.0,
    h2h_wr:         float = 0.5,
    h2h_surf_wr:    float = 0.5,
    h2h_n:          int   = 0,
    # EWMA форма (medium horizon)
    p1_spw_m:       Optional[float] = None,
    p2_spw_m:       Optional[float] = None,
    p1_rpw_m:       Optional[float] = None,
    p2_rpw_m:       Optional[float] = None,
    p1_hold_m:      Optional[float] = None,
    p2_hold_m:      Optional[float] = None,
    p1_brk_m:       Optional[float] = None,
    p2_brk_m:       Optional[float] = None,
    # Clutch
    tb_diff:        float = 0.0,
    ds_diff:        float = 0.0,
    bp_diff:        float = 0.0,
) -> Optional[Dict]:
    """
    Връща dict с p1_win_prob, p2_win_prob, confidence или None ако моделът не е наличен.
    """
    tour_models, _, winner_features, _ = _load_models()
    tg = _tour_group(circuit)
    model = tour_models.get(tg) or tour_models.get("ATP")
    if model is None or not winner_features:
        return None

    r1 = _safe(p1_rank, 500); r2 = _safe(p2_rank, 500)
    pt1 = _safe(p1_rank_pts, 0); pt2 = _safe(p2_rank_pts, 0)

    # Surface one-hot
    surf_map = {"Hard":0, "Clay":0, "Grass":0, "Carpet":0}
    surf_clean = surface.capitalize()
    if surf_clean in surf_map: surf_map[surf_clean] = 1

    # EWMA imputation — surface averages
    SURF_AVG = {
        "Hard":   {"spw":0.62,"rpw":0.38,"hold":0.76,"brk":0.24},
        "Clay":   {"spw":0.60,"rpw":0.40,"hold":0.74,"brk":0.26},
        "Grass":  {"spw":0.65,"rpw":0.35,"hold":0.80,"brk":0.20},
        "Carpet": {"spw":0.63,"rpw":0.37,"hold":0.77,"brk":0.23},
    }
    avg = SURF_AVG.get(surf_clean, SURF_AVG["Hard"])

    def imp(v, key): return _safe(v, avg[key])

    s1 = imp(p1_spw_m, "spw"); s2 = imp(p2_spw_m, "spw")
    rv1= imp(p1_rpw_m, "rpw"); rv2= imp(p2_rpw_m, "rpw")
    h1 = imp(p1_hold_m,"hold");h2 = imp(p2_hold_m,"hold")
    b1 = imp(p1_brk_m, "brk"); b2 = imp(p2_brk_m, "brk")

    elo_diff     = _safe(p1_elo)     - _safe(p2_elo)
    adj_elo_diff = _safe(p1_adj_elo) - _safe(p2_adj_elo)
    elo_prob     = 1/(1+10**((_safe(p2_elo)    -_safe(p1_elo))    /400))
    adj_elo_prob = 1/(1+10**((_safe(p2_adj_elo)-_safe(p1_adj_elo))/400))

    row = {
        "rank_diff":       r2 - r1,
        "rank_ratio":      r1 / (r2 + 1),
        "points_diff":     pt1 - pt2,
        "elo_diff":        elo_diff,
        "adj_elo_diff":    adj_elo_diff,
        "elo_prob":        elo_prob,
        "adj_elo_prob":    adj_elo_prob,
        "surf_elo_rel":    0.0,
        "days_rest_diff":  0.0,
        "h2h_wr":          _safe(h2h_wr, 0.5),
        "h2h_surf_wr":     _safe(h2h_surf_wr, 0.5),
        "h2h_n":           float(h2h_n),
        "tb_diff":         _safe(tb_diff),
        "ds_diff":         _safe(ds_diff),
        "bp_diff":         _safe(bp_diff),
        "best_of":         float(best_of),
        "tourney_level":   _safe(tourney_level, 2.0),
        # EWMA medium
        "spw_m_diff":      s1  - s2,
        "rpw_m_diff":      rv1 - rv2,
        "hold_m_diff":     h1  - h2,
        "brk_m_diff":      b1  - b2,
        # Surface one-hot
        "surf_Hard":       float(surf_map["Hard"]),
        "surf_Clay":       float(surf_map["Clay"]),
        "surf_Grass":      float(surf_map["Grass"]),
        "surf_Carpet":     float(surf_map["Carpet"]),
    }

    # Запълваме останалите features с 0
    X = np.array([[row.get(f, 0.0) for f in winner_features]])

    try:
        proba = model.predict_proba(X)[0]
        p1_prob = float(proba[1])
        p2_prob = 1.0 - p1_prob
        # Confidence: колко далеч е от 50/50
        conf = int(abs(p1_prob - 0.5) * 200)  # 0-100
        return {
            "p1_win_prob": round(p1_prob, 4),
            "p2_win_prob": round(p2_prob, 4),
            "confidence":  conf,
            "tour_group":  tg,
            "model_used":  f"LightGBM v4 ({tg})",
        }
    except:
        return None

def predict_games(
    elo_diff:       float,
    adj_elo_diff:   float,
    rank_diff:      float,
    rank_ratio:     float,
    surface:        str,
    best_of:        int   = 3,
    tourney_level:  float = 2.0,
    hold_m_diff:    float = 0.0,
    brk_m_diff:     float = 0.0,
) -> Optional[Dict]:
    """
    Предсказва очакван брой геймове и P(over X.5).
    """
    _, games_model, _, games_features = _load_models()
    if games_model is None or not games_features:
        return None

    surf_map = {"Hard":0,"Clay":0,"Grass":0,"Carpet":0}
    surf_clean = surface.capitalize()
    if surf_clean in surf_map: surf_map[surf_clean] = 1

    row = {
        "elo_diff":       elo_diff,
        "adj_elo_diff":   adj_elo_diff,
        "rank_diff":      rank_diff,
        "rank_ratio":     rank_ratio,
        "hold_m_diff":    hold_m_diff,
        "brk_m_diff":     brk_m_diff,
        "hlds_m_diff":    hold_m_diff,
        "brks_m_diff":    brk_m_diff,
        "spw_m_diff":     0.0,
        "rpw_m_diff":     0.0,
        "best_of":        float(best_of),
        "tourney_level":  tourney_level,
        "surf_Hard":      float(surf_map["Hard"]),
        "surf_Clay":      float(surf_map["Clay"]),
        "surf_Grass":     float(surf_map["Grass"]),
        "surf_Carpet":    float(surf_map["Carpet"]),
    }

    X = np.array([[row.get(f, 0.0) for f in games_features]])
    try:
        expected = float(games_model.predict(X)[0])
        # Over/Under вероятности чрез нормално разпределение около expected
        from scipy.stats import norm
        std = 4.5  # историческа дисперсия
        lines = [20.5, 21.5, 22.5, 23.5, 24.5]
        overs = {f"over_{int(l)}5": round(1 - norm.cdf(l, expected, std), 3)
                 for l in lines}
        return {"expected_games": round(expected, 1), **overs}
    except:
        try:
            return {"expected_games": round(expected, 1)}
        except:
            return None
