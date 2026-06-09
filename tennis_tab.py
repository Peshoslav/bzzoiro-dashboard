"""
🎾 Tennis Tab v2 — Match Predictor
- Падащо меню с търсене на играчи (от Sackmann + Bzzoiro)
- Ръчно въвеждане на коефициенти
- ML прогноза (winner + over/under games)
- Краткосрочна и дългосрочна статистика
- Gemini AI верификация и корекция
"""
from __future__ import annotations
import streamlit as st
import pandas as pd
import numpy as np
import requests
import io
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from tennis_predictor import predict_winner, predict_games

# ── CSS ───────────────────────────────────────────────────────────
TENNIS_CSS = """
<style>
.t-card{background:#161b27;border:1px solid #1e2737;border-radius:12px;
  padding:1rem 1.2rem;margin-bottom:.8rem}
.t-card-title{font-size:.68rem;font-weight:700;color:#4b5563;
  text-transform:uppercase;letter-spacing:1.5px;margin-bottom:.8rem;
  border-bottom:1px solid #1e2737;padding-bottom:.5rem}
.prob-bar{display:flex;border-radius:8px;overflow:hidden;height:44px;margin:.6rem 0}
.stat-row{display:flex;justify-content:space-between;align-items:center;
  padding:.35rem 0;border-bottom:1px solid #0d1117;font-size:.82rem}
.stat-label{color:#6b7280;font-size:.75rem}
.stat-val{font-weight:700;color:#e2e8f0}
.stat-val.good{color:#22c55e}
.stat-val.warn{color:#f59e0b}
.stat-val.bad{color:#ef4444}
.surf-pill{display:inline-block;padding:2px 10px;border-radius:20px;
  font-size:.7rem;font-weight:700;margin-left:.5rem}
.surf-Hard{background:rgba(14,165,233,.15);color:#0ea5e9}
.surf-Clay{background:rgba(245,158,11,.15);color:#f59e0b}
.surf-Grass{background:rgba(34,197,94,.15);color:#22c55e}
.surf-Carpet{background:rgba(167,139,250,.15);color:#a78bfa}
.value-badge{background:rgba(0,212,170,.1);border:1px solid rgba(0,212,170,.3);
  border-radius:6px;padding:.15rem .5rem;font-size:.75rem;color:#00d4aa;font-weight:700}
.odds-ev{font-size:.72rem;padding:2px 7px;border-radius:4px;font-weight:700}
.odds-pos{background:rgba(34,197,94,.15);color:#22c55e}
.odds-neg{background:rgba(239,68,68,.15);color:#ef4444}
.odds-neu{background:rgba(107,114,128,.15);color:#6b7280}
.ai-badge{display:inline-flex;align-items:center;gap:.3rem;
  background:rgba(0,212,170,.08);border:1px solid rgba(0,212,170,.2);
  border-radius:6px;padding:.2rem .6rem;font-size:.7rem;color:#00d4aa}
</style>
"""

# ── Зареждане на играчи от Sackmann ──────────────────────────────
@st.cache_data(ttl=86400, show_spinner=False)
def load_player_list() -> pd.DataFrame:
    """
    Зарежда топ ATP и WTA играчи от последните Sackmann файлове.
    Връща DataFrame с колони: name, rank, tour, surface_stats.
    """
    frames = []
    base_atp = "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master"
    base_wta = "https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master"

    for year in [2025, 2024]:
        for base, tour in [(base_atp,"ATP"),(base_wta,"WTA")]:
            url = f"{base}/{tour.lower()}_matches_{year}.csv"
            try:
                r = requests.get(url, timeout=15)
                if r.status_code != 200: continue
                df = pd.read_csv(io.StringIO(r.text), low_memory=False)
                df["_tour"] = tour
                frames.append(df)
            except: continue

    if not frames:
        return pd.DataFrame(columns=["name","rank","tour"])

    all_df = pd.concat(frames, ignore_index=True)
    all_df["tourney_date"] = pd.to_datetime(all_df["tourney_date"],
                                             format="%Y%m%d", errors="coerce")

    players: Dict[str, Dict] = {}

    for _, row in all_df.sort_values("tourney_date").iterrows():
        tour = row["_tour"]
        for name_col, rank_col, prefix in [
            ("winner_name","winner_rank","w"),
            ("loser_name", "loser_rank", "l")
        ]:
            name = row.get(name_col,"")
            if not isinstance(name, str) or not name.strip(): continue
            rank = row.get(rank_col)
            try: rank = int(float(rank))
            except: rank = 9999

            entry = players.setdefault(name, {
                "name": name, "rank": rank, "tour": tour,
                "matches": 0,
                "w_svpt":0,"w_1stWon":0,"w_2ndWon":0,"w_1stIn":0,
                "w_ace":0,"w_df":0,"w_bpSaved":0,"w_bpFaced":0,"w_SvGms":0,
            })
            entry["rank"] = rank
            entry["matches"] += 1

            # Акумулираме статистики
            for stat in ["svpt","1stWon","2ndWon","1stIn","ace","df",
                         "bpSaved","bpFaced","SvGms"]:
                try:
                    v = float(row.get(f"{prefix}_{stat}", 0) or 0)
                    entry[f"w_{stat}"] += v
                except: pass

    if not players:
        return pd.DataFrame(columns=["name","rank","tour"])

    result = pd.DataFrame(players.values())
    # Изчисляваме агрегирана статистика
    result["spw"] = np.where(
        result["w_svpt"]>0,
        (result["w_1stWon"]+result["w_2ndWon"])/result["w_svpt"], np.nan)
    result["ace_rate"] = np.where(
        result["w_svpt"]>0, result["w_ace"]/result["w_svpt"], np.nan)
    result["df_rate"] = np.where(
        result["w_svpt"]>0, result["w_df"]/result["w_svpt"], np.nan)
    result["first_in"] = np.where(
        result["w_svpt"]>0, result["w_1stIn"]/result["w_svpt"], np.nan)
    result["bp_save"] = np.where(
        result["w_bpFaced"]>0, result["w_bpSaved"]/result["w_bpFaced"], np.nan)

    return result.sort_values("rank").reset_index(drop=True)


@st.cache_data(ttl=3600, show_spinner=False)
def load_player_recent(player_name: str, n: int = 20) -> pd.DataFrame:
    """Последните N мача на играча от Sackmann данните."""
    base_atp = "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master"
    base_wta = "https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master"

    frames = []
    for year in [2025, 2024, 2023]:
        for base in [base_atp, base_wta]:
            url = f"{base}/{'atp' if 'atp' in base else 'wta'}_matches_{year}.csv"
            try:
                r = requests.get(url, timeout=15)
                if r.status_code != 200: continue
                df = pd.read_csv(io.StringIO(r.text), low_memory=False)
                mask = (df["winner_name"]==player_name)|(df["loser_name"]==player_name)
                frames.append(df[mask])
            except: continue

    if not frames:
        return pd.DataFrame()

    result = pd.concat(frames).drop_duplicates()
    result["tourney_date"] = pd.to_datetime(result["tourney_date"],
                                             format="%Y%m%d", errors="coerce")
    return result.sort_values("tourney_date", ascending=False).head(n)


def _player_stats_from_recent(df: pd.DataFrame, player: str) -> Dict:
    """Изчислява статистики от последните мачове на играча."""
    if df.empty:
        return {}

    stats_long = {"spw":[], "rpw":[], "ace":[], "df":[], "bp_save":[], "win":[]}
    stats_short = {"spw":[], "rpw":[], "ace":[], "df":[], "bp_save":[], "win":[]}

    for _, row in df.iterrows():
        is_winner = row.get("winner_name","") == player
        p = "w" if is_winner else "l"
        op = "l" if is_winner else "w"

        svpt = float(row.get(f"{p}_svpt",0) or 0)
        op_svpt = float(row.get(f"{op}_svpt",0) or 0)

        if svpt > 0:
            spw = (float(row.get(f"{p}_1stWon",0) or 0) +
                   float(row.get(f"{p}_2ndWon",0) or 0)) / svpt
            ace = float(row.get(f"{p}_ace",0) or 0) / svpt
            df_ = float(row.get(f"{p}_df",0) or 0) / svpt
            bpf = float(row.get(f"{p}_bpFaced",0) or 0)
            bps = float(row.get(f"{p}_bpSaved",0) or 0)
            bp_s = bps/bpf if bpf > 0 else None
        else:
            spw = ace = df_ = bp_s = None

        rpw = (1 - (float(row.get(f"{op}_1stWon",0) or 0) +
                    float(row.get(f"{op}_2ndWon",0) or 0)) / op_svpt
               ) if op_svpt > 0 else None

        for d in [stats_long, stats_short]:
            if spw is not None: d["spw"].append(spw)
            if rpw is not None: d["rpw"].append(rpw)
            if ace is not None: d["ace"].append(ace)
            if df_ is not None: d["df"].append(df_)
            if bp_s is not None: d["bp_save"].append(bp_s)
            d["win"].append(1 if is_winner else 0)

    # short = последните 5, long = всички
    result = {}
    for key, vals in stats_long.items():
        result[f"long_{key}"] = np.mean(vals) if vals else None
    for key, vals in [(k,v[:5]) for k,v in stats_short.items()]:
        result[f"short_{key}"] = np.mean(vals) if vals else None

    result["n_matches"] = len(df)
    result["form"] = stats_short["win"][:5]
    return result


# ── Helper: коефициент → вероятност ──────────────────────────────
def odds_to_prob(odds: float) -> float:
    if odds <= 1.0: return 0.5
    return round(1.0 / odds, 4)

def margin_normalized(p1: float, p2: float) -> Tuple[float, float]:
    """Нормализира две вероятности за да премахне букмейкърски марж."""
    total = p1 + p2
    if total <= 0: return 0.5, 0.5
    return round(p1/total, 4), round(p2/total, 4)

def kelly_fraction(prob: float, odds: float, fraction: float = 0.25) -> float:
    """Fractional Kelly критерий."""
    b = odds - 1.0
    q = 1.0 - prob
    kelly = (b * prob - q) / b
    return round(max(0.0, kelly) * fraction, 4)


# ── Gemini верификация ────────────────────────────────────────────
def _gemini_tennis_analysis(
    p1: str, p2: str, surface: str,
    ml_p1_prob: float, ml_p2_prob: float,
    ml_games: float,
    p1_stats: Dict, p2_stats: Dict,
    p1_odds: float, p2_odds: float,
    ou_line: float, ou_odds_over: float, ou_odds_under: float,
    client,
) -> str:
    """
    Изпраща контекст към Gemini и иска верификация + корекция на ML прогнозата.
    """
    if client is None:
        return "Gemini не е наличен."

    def fmt(v, pct=False):
        if v is None: return "N/A"
        return f"{v*100:.1f}%" if pct else f"{v:.3f}"

    ctx = f"""Тенис мач анализ:
{p1} vs {p2} на {surface}

ML МОДЕЛ ПРОГНОЗА:
- {p1} победа: {ml_p1_prob*100:.1f}%
- {p2} победа: {ml_p2_prob*100:.1f}%
- Очаквани геймове: {ml_games:.1f}

КОЕФИЦИЕНТИ:
- {p1}: {p1_odds} (implied {odds_to_prob(p1_odds)*100:.1f}%)
- {p2}: {p2_odds} (implied {odds_to_prob(p2_odds)*100:.1f}%)
- Over/Under {ou_line}: Over {ou_odds_over} | Under {ou_odds_under}

СТАТИСТИКА {p1} (последни мачове):
- Win rate (кратко): {fmt(p1_stats.get("short_win"), True)}
- Win rate (дълго): {fmt(p1_stats.get("long_win"), True)}
- Serve points won: {fmt(p1_stats.get("long_spw"), True)}
- Return points won: {fmt(p1_stats.get("long_rpw"), True)}
- BP save rate: {fmt(p1_stats.get("long_bp_save"), True)}
- Ace rate: {fmt(p1_stats.get("long_ace"), True)}
- Форма (последни 5): {p1_stats.get("form", [])}

СТАТИСТИКА {p2} (последни мачове):
- Win rate (кратко): {fmt(p2_stats.get("short_win"), True)}
- Win rate (дълго): {fmt(p2_stats.get("long_win"), True)}
- Serve points won: {fmt(p2_stats.get("long_spw"), True)}
- Return points won: {fmt(p2_stats.get("long_rpw"), True)}
- BP save rate: {fmt(p2_stats.get("long_bp_save"), True)}
- Ace rate: {fmt(p2_stats.get("long_ace"), True)}
- Форма (последни 5): {p2_stats.get("form", [])}
"""

    system_prompt = f"""Ти си експертен тенис анализатор. Получаваш ML прогноза и статистики за мач.
Твоята задача:
1. Провери дали ML прогнозата е логична спрямо статистиките и формата
2. Провери дали букмейкърските коефициенти съвпадат или се разминават с ML прогнозата
3. Ако има значимо разминаване (>10%), обясни защо и предложи коригирана вероятност
4. Анализирай over/under пазара
5. Дай кратка финална препоръка

Отговаряй на БЪЛГАРСКИ. Бъди кратък и конкретен — максимум 250 думи.
Формат:
🔍 ВЕРИФИКАЦИЯ: [съгласен/несъгласен с ML] — [1 изречение защо]
📊 ПОБЕДИТЕЛ: [твоята оценка на вероятността]
🎮 ГЕЙМОВЕ: [над/под {ou_line} — кратко обяснение]
⚡ ПРЕПОРЪКА: [конкретна препоръка]"""

    try:
        from google.genai import types
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=[types.Content(
                role="user",
                parts=[types.Part(text=ctx)]
            )],
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=400,
            )
        )
        return response.text or "Няма отговор."
    except Exception as e:
        err = str(e)
        if "429" in err or "RESOURCE_EXHAUSTED" in err:
            import re
            retry = re.search(r"retry[^0-9]*([0-9]+)s", err)
            wait  = retry.group(1) if retry else "60"
            return (f"⏳ Gemini rate limit — изчакай {wait} секунди и опитай отново.\n"
                    f"Ако проблемът продължава, провери квотата на: https://ai.dev/rate-limit")
        if "API_KEY" in err or "api_key" in err.lower():
            return "🔑 Невалиден Gemini API ключ. Провери GEMINI_API_KEY в Streamlit secrets."
        return f"Gemini грешка: {e}"


# ── Stat display helper ───────────────────────────────────────────
def _stat_color(val: float, good_above: float, bad_below: float) -> str:
    if val >= good_above: return "good"
    if val <= bad_below:  return "bad"
    return "warn"

def _render_player_stats(name: str, stats: Dict, col):
    with col:
        short_win = stats.get("short_win")
        long_win  = stats.get("long_win")
        form      = stats.get("form", [])
        n         = stats.get("n_matches", 0)

        # Форма индикатори
        form_html = ""
        for r in form[:5]:
            clr = "#22c55e" if r == 1 else "#ef4444"
            lbl = "W" if r == 1 else "L"
            form_html += (f'<span style="display:inline-flex;align-items:center;'
                         f'justify-content:center;width:22px;height:22px;'
                         f'border-radius:4px;font-size:.7rem;font-weight:800;'
                         f'background:{clr}22;color:{clr};margin-right:3px">{lbl}</span>')

        st.markdown(f'''<div class="t-card">
          <div class="t-card-title">{name[:20]}</div>
          <div style="margin-bottom:.6rem">{form_html}</div>
          <div style="font-size:.65rem;color:#4b5563;margin-bottom:.6rem">
            Последни {n} мача</div>''', unsafe_allow_html=True)

        rows = [
            ("Win rate (кратко)",  short_win, True,  0.60, 0.40),
            ("Win rate (дълго)",   long_win,  True,  0.55, 0.40),
            ("Serve pts won",      stats.get("long_spw"),  True,  0.65, 0.55),
            ("Return pts won",     stats.get("long_rpw"),  True,  0.42, 0.30),
            ("BP save rate",       stats.get("long_bp_save"), True, 0.65, 0.50),
            ("Ace rate",           stats.get("long_ace"),  True,  0.08, 0.02),
            ("DF rate",            stats.get("long_df"),   True,  0.02, 0.06),
        ]
        for label, val, is_pct, good, bad in rows:
            if val is None: continue
            display = f"{val*100:.1f}%" if is_pct else f"{val:.3f}"
            # DF rate: обратна логика
            if label == "DF rate":
                css_cls = _stat_color(val, 0.06, 0.02)
                css_cls = "bad" if val >= 0.06 else "good" if val <= 0.02 else "warn"
            else:
                css_cls = _stat_color(val, good, bad)
            st.markdown(
                f'<div class="stat-row"><span class="stat-label">{label}</span>'
                f'<span class="stat-val {css_cls}">{display}</span></div>',
                unsafe_allow_html=True
            )
        st.markdown("</div>", unsafe_allow_html=True)


# ── Главна функция ────────────────────────────────────────────────
def render_tennis_tab():
    st.markdown(TENNIS_CSS, unsafe_allow_html=True)

    # Gemini client
    try:
        import google.genai as genai
        _client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    except Exception:
        _client = None

    # Зареждаме играчите веднъж
    with st.spinner("Зареждане на играчи…"):
        players_df = load_player_list()

    if players_df.empty:
        st.error("Неуспешно зареждане на играчи. Провери интернет връзката.")
        return

    # Разделяме ATP и WTA
    atp_players = players_df[players_df["tour"]=="ATP"]["name"].tolist()
    wta_players = players_df[players_df["tour"]=="WTA"]["name"].tolist()
    all_players = sorted(set(atp_players + wta_players))

    # ── HEADER ───────────────────────────────────────────────────
    st.markdown('''<div style="margin-bottom:1.2rem">
      <div style="font-size:1.4rem;font-weight:900;color:#fff">
        🎾 Тенис <span style="color:#00d4aa">Предиктор</span></div>
      <div style="font-size:.8rem;color:#6b7280;margin-top:.2rem">
        ML прогноза + Gemini AI верификация</div>
    </div>''', unsafe_allow_html=True)

    # ── ФОРМА ────────────────────────────────────────────────────
    with st.container():
        st.markdown('<div class="t-card"><div class="t-card-title">Избор на мач</div>',
                    unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            p1_name = st.selectbox(
                "🎾 Играч 1",
                options=[""] + all_players,
                format_func=lambda x: "Избери играч…" if x=="" else x,
                key="tennis_p1"
            )
        with c2:
            p2_name = st.selectbox(
                "🎾 Играч 2",
                options=[""] + all_players,
                format_func=lambda x: "Избери играч…" if x=="" else x,
                key="tennis_p2"
            )

        c3, c4, c5 = st.columns(3)
        with c3:
            surface = st.selectbox(
                "🏟️ Настилка",
                ["Hard","Clay","Grass","Carpet"],
                key="tennis_surf"
            )
        with c4:
            circuit = st.selectbox(
                "🏆 Тур",
                ["ATP","WTA","CH_ITF"],
                key="tennis_circuit"
            )
        with c5:
            best_of = st.selectbox(
                "🎯 Формат",
                [3, 5],
                format_func=lambda x: f"Best of {x}",
                key="tennis_bo"
            )

        st.markdown('<div style="margin-top:.8rem">', unsafe_allow_html=True)
        st.markdown('<div class="t-card-title">Коефициенти (незадължително)</div>',
                    unsafe_allow_html=True)
        oc1, oc2, oc3, oc4, oc5 = st.columns(5)
        with oc1:
            p1_odds = st.number_input(
                f"Победа {(p1_name or 'P1')[:10]}",
                min_value=1.01, max_value=50.0, value=1.85,
                step=0.05, format="%.2f", key="t_odds_p1"
            )
        with oc2:
            p2_odds = st.number_input(
                f"Победа {(p2_name or 'P2')[:10]}",
                min_value=1.01, max_value=50.0, value=2.00,
                step=0.05, format="%.2f", key="t_odds_p2"
            )
        with oc3:
            ou_line = st.number_input(
                "О/У линия",
                min_value=15.5, max_value=40.5, value=22.5,
                step=1.0, format="%.1f", key="t_ou_line"
            )
        with oc4:
            ou_over = st.number_input(
                "Над", min_value=1.01, max_value=10.0,
                value=1.85, step=0.05, format="%.2f", key="t_odds_over"
            )
        with oc5:
            ou_under = st.number_input(
                "Под", min_value=1.01, max_value=10.0,
                value=1.95, step=0.05, format="%.2f", key="t_odds_under"
            )
        st.markdown("</div></div>", unsafe_allow_html=True)

    if not p1_name or not p2_name:
        st.info("👆 Избери двама играчи за да видиш прогнозата.")
        return

    if p1_name == p2_name:
        st.warning("Играчите трябва да са различни.")
        return

    # ── ЗАРЕЖДАМЕ ДАННИТЕ ────────────────────────────────────────
    with st.spinner(f"Зареждане на статистики…"):
        df_p1 = load_player_recent(p1_name, 30)
        df_p2 = load_player_recent(p2_name, 30)
        stats_p1 = _player_stats_from_recent(df_p1, p1_name)
        stats_p2 = _player_stats_from_recent(df_p2, p2_name)

    # Rank от players_df
    p1_row = players_df[players_df["name"]==p1_name]
    p2_row = players_df[players_df["name"]==p2_name]
    p1_rank = int(p1_row["rank"].iloc[0]) if not p1_row.empty else 100
    p2_rank = int(p2_row["rank"].iloc[0]) if not p2_row.empty else 100

    # Прост Elo proxy от rank (ако нямаме изчислен)
    p1_elo = max(1200, 2200 - p1_rank * 3)
    p2_elo = max(1200, 2200 - p2_rank * 3)

    # ── ML ПРОГНОЗА ───────────────────────────────────────────────
    ml_result = predict_winner(
        p1_rank=p1_rank, p2_rank=p2_rank,
        p1_rank_pts=None, p2_rank_pts=None,
        p1_elo=p1_elo, p2_elo=p2_elo,
        p1_adj_elo=p1_elo, p2_adj_elo=p2_elo,
        surface=surface, circuit=circuit,
        best_of=best_of, tourney_level=2.0,
        p1_spw_m=stats_p1.get("long_spw"),
        p2_spw_m=stats_p2.get("long_spw"),
        p1_rpw_m=stats_p1.get("long_rpw"),
        p2_rpw_m=stats_p2.get("long_rpw"),
        p1_hold_m=None, p2_hold_m=None,
        p1_brk_m=None,  p2_brk_m=None,
    )

    games_result = predict_games(
        elo_diff=p1_elo-p2_elo,
        adj_elo_diff=p1_elo-p2_elo,
        rank_diff=p2_rank-p1_rank,
        rank_ratio=p1_rank/(p2_rank+1),
        surface=surface, best_of=best_of,
    )

    # Fallback ако моделите не са заредени
    if ml_result is None:
        # Прост Elo baseline
        p1_prob = 1/(1+10**((p2_elo-p1_elo)/400))
        p2_prob = 1 - p1_prob
        model_label = "Elo baseline (ML модел не е зареден)"
    else:
        p1_prob = ml_result["p1_win_prob"]
        p2_prob = ml_result["p2_win_prob"]
        model_label = ml_result.get("model_used","LightGBM v4")

    exp_games = games_result["expected_games"] if games_result else 22.0

    # Нормализирани букмейкърски вероятности
    bk_p1, bk_p2 = margin_normalized(odds_to_prob(p1_odds), odds_to_prob(p2_odds))
    bk_over  = odds_to_prob(ou_over)
    bk_under = odds_to_prob(ou_under)

    # ── ПРОГНОЗА СЕКЦИЯ ───────────────────────────────────────────
    st.markdown('''<div style="font-size:.7rem;font-weight:700;color:#4b5563;
      text-transform:uppercase;letter-spacing:1.5px;margin:1.2rem 0 .6rem;
      border-bottom:1px solid #1e2737;padding-bottom:.4rem">
      Прогноза за победител</div>''', unsafe_allow_html=True)

    p1pct = int(p1_prob*100); p2pct = 100-p1pct
    surf_badge = f'<span class="surf-pill surf-{surface}">{surface}</span>'

    st.markdown(f'''<div class="t-card">
      <div style="display:flex;justify-content:space-between;align-items:center;
        margin-bottom:.8rem">
        <span style="font-size:.72rem;color:#4b5563">⚙️ {model_label}</span>
        {surf_badge}
      </div>
      <div style="display:flex;justify-content:space-between;margin-bottom:.3rem">
        <span style="font-size:1rem;font-weight:800;color:#e2e8f0">
          {p1_name}</span>
        <span style="font-size:1rem;font-weight:800;color:#e2e8f0">
          {p2_name}</span>
      </div>
      <div style="display:flex;justify-content:space-between;margin-bottom:.5rem">
        <span style="font-size:.72rem;color:#6b7280">Ранг #{p1_rank}</span>
        <span style="font-size:.72rem;color:#6b7280">Ранг #{p2_rank}</span>
      </div>
    </div>''', unsafe_allow_html=True)

    # Prob bar
    st.markdown(f'''<div class="prob-bar">
      <div style="flex:{p1pct};background:linear-gradient(135deg,#00d4aa,#0ea5e9);
        display:flex;align-items:center;justify-content:center;gap:.4rem">
        <span style="font-size:1.1rem;font-weight:900;color:#0d1117">{p1pct}%</span>
      </div>
      <div style="flex:{p2pct};background:linear-gradient(135deg,#f59e0b,#ef4444);
        display:flex;align-items:center;justify-content:center;gap:.4rem">
        <span style="font-size:1.1rem;font-weight:900;color:#0d1117">{p2pct}%</span>
      </div>
    </div>
    <div style="display:flex;justify-content:space-between;
      font-size:.72rem;color:#6b7280;margin-bottom:1rem">
      <span>🎾 {p1_name}</span><span>🎾 {p2_name}</span>
    </div>''', unsafe_allow_html=True)

    # ── OVER/UNDER ────────────────────────────────────────────────
    st.markdown('''<div style="font-size:.7rem;font-weight:700;color:#4b5563;
      text-transform:uppercase;letter-spacing:1.5px;margin:1rem 0 .6rem;
      border-bottom:1px solid #1e2737;padding-bottom:.4rem">
      Над / Под геймове</div>''', unsafe_allow_html=True)

    g1, g2, g3, g4 = st.columns(4)
    over_prob = games_result.get(f"over_{int(ou_line)}", 0.5) if games_result else 0.5
    under_prob = 1 - over_prob

    # EV изчисление
    ev_over  = round(over_prob * ou_over - 1, 3)
    ev_under = round(under_prob * ou_under - 1, 3)
    ev_p1    = round(p1_prob * p1_odds - 1, 3)
    ev_p2    = round(p2_prob * p2_odds - 1, 3)

    tiles = [
        (f"{exp_games:.1f}", "Очаквани геймове", "#00d4aa"),
        (f"{int(over_prob*100)}%", f"Над {ou_line}", "#0ea5e9"),
        (f"{int(under_prob*100)}%", f"Под {ou_line}", "#f59e0b"),
        (f"{bk_over*100:.0f}% / {bk_under*100:.0f}%",
         "Букмейкър Над/Под", "#6b7280"),
    ]
    for col, (val, lbl, clr) in zip([g1,g2,g3,g4], tiles):
        col.markdown(f'<div style="background:#161b27;border:1px solid #1e2737;'
                    f'border-radius:10px;padding:.7rem;text-align:center">'
                    f'<div style="font-size:1.3rem;font-weight:800;color:{clr}">{val}</div>'
                    f'<div style="font-size:.62rem;color:#6b7280;margin-top:.2rem">{lbl}</div>'
                    f'</div>', unsafe_allow_html=True)

    # ── EDGE ANALYSIS ─────────────────────────────────────────────
    st.markdown('''<div style="font-size:.7rem;font-weight:700;color:#4b5563;
      text-transform:uppercase;letter-spacing:1.5px;margin:1rem 0 .6rem;
      border-bottom:1px solid #1e2737;padding-bottom:.4rem">
      Edge анализ спрямо коефициентите</div>''', unsafe_allow_html=True)

    e1, e2, e3, e4 = st.columns(4)
    edge_data = [
        (e1, f"EV {p1_name[:12]}", ev_p1, kelly_fraction(p1_prob, p1_odds)),
        (e2, f"EV {p2_name[:12]}", ev_p2, kelly_fraction(p2_prob, p2_odds)),
        (e3, f"EV Над {ou_line}", ev_over, kelly_fraction(over_prob, ou_over)),
        (e4, f"EV Под {ou_line}", ev_under, kelly_fraction(under_prob, ou_under)),
    ]
    for col, lbl, ev, kelly in edge_data:
        ev_cls  = "odds-pos" if ev > 0.03 else "odds-neg" if ev < -0.03 else "odds-neu"
        ev_sign = "+" if ev > 0 else ""
        with col:
            st.markdown(f'<div style="background:#161b27;border:1px solid #1e2737;'
                       f'border-radius:10px;padding:.65rem;text-align:center">'
                       f'<div style="font-size:.65rem;color:#6b7280;margin-bottom:.3rem">{lbl}</div>'
                       f'<span class="odds-ev {ev_cls}">{ev_sign}{ev*100:.1f}%</span>'
                       f'<div style="font-size:.62rem;color:#4b5563;margin-top:.3rem">'
                       f'Kelly: {kelly*100:.1f}%</div></div>',
                       unsafe_allow_html=True)

    # ── СТАТИСТИКИ ────────────────────────────────────────────────
    st.markdown('''<div style="font-size:.7rem;font-weight:700;color:#4b5563;
      text-transform:uppercase;letter-spacing:1.5px;margin:1.2rem 0 .6rem;
      border-bottom:1px solid #1e2737;padding-bottom:.4rem">
      Статистики на играчите</div>''', unsafe_allow_html=True)

    sc1, sc2 = st.columns(2)
    if stats_p1:
        _render_player_stats(p1_name, stats_p1, sc1)
    else:
        with sc1:
            st.info(f"Няма статистики за {p1_name}")

    if stats_p2:
        _render_player_stats(p2_name, stats_p2, sc2)
    else:
        with sc2:
            st.info(f"Няма статистики за {p2_name}")

    # ── GEMINI ВЕРИФИКАЦИЯ ────────────────────────────────────────
    st.markdown('''<div style="font-size:.7rem;font-weight:700;color:#4b5563;
      text-transform:uppercase;letter-spacing:1.5px;margin:1.2rem 0 .6rem;
      border-bottom:1px solid #1e2737;padding-bottom:.4rem">
      🤖 Gemini AI верификация</div>''', unsafe_allow_html=True)

    gemini_key = f"gemini_tennis_{p1_name}_{p2_name}_{surface}"

    if gemini_key not in st.session_state:
        st.session_state[gemini_key] = None

    if st.button("🔍 Анализирай с Gemini", key="t_gemini_btn",
                 type="primary", use_container_width=False):
        with st.spinner("Gemini анализира мача…"):
            analysis = _gemini_tennis_analysis(
                p1=p1_name, p2=p2_name, surface=surface,
                ml_p1_prob=p1_prob, ml_p2_prob=p2_prob,
                ml_games=exp_games,
                p1_stats=stats_p1, p2_stats=stats_p2,
                p1_odds=p1_odds, p2_odds=p2_odds,
                ou_line=ou_line,
                ou_odds_over=ou_over, ou_odds_under=ou_under,
                client=_client,
            )
            st.session_state[gemini_key] = analysis

    if st.session_state[gemini_key]:
        st.markdown(f'''<div style="background:#0d1117;border:1px solid #00d4aa33;
          border-radius:10px;padding:1rem 1.2rem;margin-top:.5rem;
          font-size:.88rem;color:#e2e8f0;line-height:1.75;white-space:pre-wrap">
          <div class="ai-badge" style="margin-bottom:.7rem">
            ✨ Gemini 2.0 Flash</div>
          {st.session_state[gemini_key]}
        </div>''', unsafe_allow_html=True)
    elif _client is None:
        st.warning("Gemini не е конфигуриран. Добави GEMINI_API_KEY в Streamlit secrets.")
    else:
        st.caption("Натисни бутона за Gemini анализ.")

    # ── GEMINI ЧАТ ────────────────────────────────────────────────
    st.markdown('''<div style="font-size:.7rem;font-weight:700;color:#4b5563;
      text-transform:uppercase;letter-spacing:1.5px;margin:1.4rem 0 .6rem;
      border-bottom:1px solid #1e2737;padding-bottom:.4rem">
      💬 Разговор с Gemini</div>''', unsafe_allow_html=True)

    # Инициализираме история на чата — отделна за всяка двойка играчи
    chat_key = f"tennis_chat_{p1_name}_{p2_name}"
    if chat_key not in st.session_state:
        st.session_state[chat_key] = []

    # Показваме историята
    for msg in st.session_state[chat_key]:
        role_icon = "✨" if msg["role"] == "assistant" else "👤"
        bg = "#0d1117" if msg["role"] == "assistant" else "#1a2035"
        border = "#00d4aa33" if msg["role"] == "assistant" else "#1e2737"
        st.markdown(
            f'''<div style="background:{bg};border:1px solid {border};
              border-radius:10px;padding:.75rem 1rem;margin-bottom:.4rem;
              font-size:.87rem;color:#e2e8f0;line-height:1.7;white-space:pre-wrap">
              <span style="font-size:.65rem;color:#4b5563;display:block;margin-bottom:.3rem">
              {role_icon} {"Gemini" if msg["role"]=="assistant" else "Ти"}</span>
              {msg["content"]}
            </div>''',
            unsafe_allow_html=True
        )

    # Контекст за Gemini чат — включва всичко за мача
    def _build_chat_system(p1, p2, surface, p1_prob, p2_prob,
                           exp_games, p1_stats, p2_stats,
                           p1_odds, p2_odds, ou_line):
        return f"""Ти си експертен тенис анализатор асистент. Помагаш на потребителя да анализира мача:

МАЧ: {p1} vs {p2} на {surface}
ML ПРОГНОЗА: {p1} {p1_prob*100:.1f}% | {p2} {p2_prob*100:.1f}%
ОЧАКВАНИ ГЕЙМОВЕ: {exp_games:.1f}
КОЕФИЦИЕНТИ: {p1} @ {p1_odds} | {p2} @ {p2_odds} | О/У {ou_line}

СТАТИСТИКИ {p1}: win%={p1_stats.get('long_win',0) or 0:.1%}, \
spw={p1_stats.get('long_spw',0) or 0:.1%}, rpw={p1_stats.get('long_rpw',0) or 0:.1%}, \
форма={p1_stats.get('form',[])}

СТАТИСТИКИ {p2}: win%={p2_stats.get('long_win',0) or 0:.1%}, \
spw={p2_stats.get('long_spw',0) or 0:.1%}, rpw={p2_stats.get('long_rpw',0) or 0:.1%}, \
форма={p2_stats.get('form',[])}

Отговаряй на БЪЛГАРСКИ. Бъди кратък, конкретен и аналитичен.
Когато даваш препоръки за залагания, винаги споменавай рисковете."""

    # Поле за въвеждане
    user_input = st.chat_input(
        placeholder=f"Питай Gemini за {p1_name} vs {p2_name}…",
        key=f"tennis_chat_input_{p1_name}_{p2_name}"
    )

    if user_input and _client:
        # Добавяме съобщението на потребителя
        st.session_state[chat_key].append({
            "role": "user", "content": user_input
        })

        # Изграждаме history за Gemini
        history_for_gemini = []
        for msg in st.session_state[chat_key][:-1]:  # всичко без последното
            history_for_gemini.append(msg)

        with st.spinner("Gemini мисли…"):
            try:
                from google.genai import types

                # Изграждаме contents с история
                contents = []
                for msg in history_for_gemini[-8:]:  # последните 8 съобщения
                    role = "user" if msg["role"] == "user" else "model"
                    contents.append(types.Content(
                        role=role,
                        parts=[types.Part(text=msg["content"])]
                    ))
                # Добавяме текущото съобщение
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part(text=user_input)]
                ))

                system = _build_chat_system(
                    p1_name, p2_name, surface,
                    p1_prob, p2_prob, exp_games,
                    stats_p1, stats_p2,
                    p1_odds, p2_odds, ou_line
                )

                response = _client.models.generate_content(
                    model="gemini-3.1-flash-lite",
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system,
                        max_output_tokens=500,
                    )
                )
                answer = response.text or "Няма отговор."
            except Exception as e:
                err = str(e)
                if "429" in err or "RESOURCE_EXHAUSTED" in err:
                    import re
                    retry = re.search(r"retry[^0-9]*([0-9]+)s", err)
                    wait  = retry.group(1) if retry else "60"
                    answer = (f"⏳ Rate limit — изчакай {wait} секунди и опитай отново.")
                else:
                    answer = f"Gemini грешка: {e}"

        st.session_state[chat_key].append({
            "role": "assistant", "content": answer
        })
        st.rerun()

    elif user_input and _client is None:
        st.warning("Gemini не е конфигуриран.")

    # Бутон за изчистване на историята
    if st.session_state[chat_key]:
        if st.button("🗑️ Изчисти чата", key=f"clear_chat_{p1_name}_{p2_name}",
                     type="secondary"):
            st.session_state[chat_key] = []
            st.rerun()
