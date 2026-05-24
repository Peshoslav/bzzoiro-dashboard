"""
⚽ AI Football Analytics — Main Streamlit App
Inspired by statstobucks.com — dark, card-based, data-first design.

Tabs:
  1. Програма  — Match schedule + team stats + H2H
  2. На Живо   — WebSocket live matches with real-time stats
  3. AI Анализ — Gemini analysis of any selected match
"""

# ── MUST be first Streamlit call ─────────────────────────────────
import streamlit as st

st.set_page_config(
    page_title="AI Football Analytics",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Stdlib / third-party ─────────────────────────────────────────
import json
from datetime import date, timedelta
from typing import Dict, List, Optional, Any

# ── Local modules ────────────────────────────────────────────────
from api import (
    get_events, get_live_events, get_event_stats, get_event_incidents,
    get_event_odds, get_team_fixtures, get_h2h, get_leagues,
    get_standings, get_prediction,
)
from ws_manager import get_ws_manager

# ── Gemini ───────────────────────────────────────────────────────
try:
    from google import genai as google_genai
    _gemini = google_genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except Exception:
    _gemini = None


# ═════════════════════════════════════════════════════════════════
# CSS — Dark theme, statstobucks-style
# ═════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

/* ── Root ─────────────────────────────────────────────────── */
.stApp, [data-testid="stAppViewContainer"] {
    background: #0d1117 !important;
    font-family: 'Inter', sans-serif;
}
[data-testid="stSidebar"] { background: #0d1117; }
.block-container { padding: 0.75rem 1.5rem 2rem; max-width: 1400px; }
#MainMenu, footer, header { visibility: hidden; }

/* ── Top bar ──────────────────────────────────────────────── */
.topbar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 0.8rem 0; margin-bottom: 1.2rem;
    border-bottom: 1px solid #1e2737;
}
.logo { font-size: 1.5rem; font-weight: 900; color: #fff; letter-spacing: -0.5px; }
.logo span { color: #00d4aa; }
.live-pill {
    background: rgba(239,68,68,0.15); border: 1px solid rgba(239,68,68,0.4);
    color: #ef4444; border-radius: 20px; padding: 3px 12px;
    font-size: 0.7rem; font-weight: 700; letter-spacing: 1px;
    animation: blink 1.8s ease-in-out infinite;
}
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.5} }

/* ── Tabs ─────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    background: #161b27; border-radius: 10px;
    padding: 4px; gap: 4px; border: 1px solid #1e2737;
}
.stTabs [data-baseweb="tab"] {
    background: transparent; color: #6b7280; border-radius: 7px;
    font-weight: 600; font-size: 0.85rem; padding: 0.55rem 1.4rem;
}
.stTabs [aria-selected="true"] {
    background: #00d4aa !important; color: #0d1117 !important;
}
.stTabs [data-baseweb="tab-panel"] { padding-top: 1rem; }

/* ── Section header ───────────────────────────────────────── */
.sec-hd {
    font-size: 0.7rem; font-weight: 700; color: #4b5563;
    text-transform: uppercase; letter-spacing: 1.5px;
    padding-bottom: 0.5rem; margin: 1.2rem 0 0.6rem;
    border-bottom: 1px solid #1e2737;
}

/* ── Match card ───────────────────────────────────────────── */
.match-card {
    background: #161b27; border: 1px solid #1e2737;
    border-radius: 12px; padding: 1rem 1.2rem;
    margin-bottom: 0.6rem; cursor: pointer;
    transition: border-color .15s, transform .15s, box-shadow .15s;
}
.match-card:hover {
    border-color: #00d4aa; transform: translateY(-1px);
    box-shadow: 0 4px 18px rgba(0,212,170,.12);
}
.match-card.live-card { border-color: rgba(239,68,68,.35); }
.mc-meta {
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: .45rem;
}
.league-tag {
    font-size: 0.68rem; color: #6b7280; font-weight: 600;
    letter-spacing: .4px;
}
.time-tag {
    font-size: 0.7rem; color: #4b5563; font-weight: 500;
}
.mc-teams {
    display: flex; align-items: center; gap: 0.5rem;
}
.team { flex: 1; font-size: 0.95rem; font-weight: 600; color: #e2e8f0; }
.team.away { text-align: right; }
.score {
    background: #1e2737; border-radius: 7px;
    padding: 5px 14px; font-size: 1.1rem; font-weight: 800;
    color: #00d4aa; min-width: 70px; text-align: center;
    letter-spacing: 2px;
}
.score.live-score {
    background: rgba(239,68,68,.12); color: #ef4444;
    border: 1px solid rgba(239,68,68,.3);
}
.score.ns { color: #4b5563; font-size: 0.8rem; }
.minute-tag {
    font-size: 0.7rem; color: #ef4444; font-weight: 700;
    background: rgba(239,68,68,.1); border-radius: 4px;
    padding: 2px 6px;
}

/* ── Stat bars ────────────────────────────────────────────── */
.stat-wrapper { margin: .4rem 0; }
.stat-meta { display: flex; justify-content: space-between; margin-bottom: 3px; }
.stat-name { font-size: 0.72rem; color: #6b7280; font-weight: 500; }
.stat-vals { font-size: 0.72rem; color: #e2e8f0; font-weight: 700; }
.bar-track {
    width: 100%; height: 5px; background: #1e2737;
    border-radius: 3px; overflow: hidden; display: flex;
}
.bar-home {
    height: 100%; border-radius: 3px 0 0 3px;
    background: linear-gradient(90deg, #00d4aa, #0ea5e9);
    transition: width .5s ease;
}
.bar-away {
    height: 100%; border-radius: 0 3px 3px 0;
    background: linear-gradient(90deg, #f59e0b, #ef4444);
    transition: width .5s ease;
}

/* ── H2H result badges ────────────────────────────────────── */
.h2h-badges { display: flex; gap: 4px; flex-wrap: wrap; }
.badge {
    width: 26px; height: 26px; border-radius: 5px;
    font-size: 0.65rem; font-weight: 800; display: inline-flex;
    align-items: center; justify-content: center;
}
.w-badge { background: rgba(34,197,94,.2); color: #22c55e; }
.d-badge { background: rgba(234,179,8,.2); color: #eab308; }
.l-badge { background: rgba(239,68,68,.2); color: #ef4444; }

/* ── Metric tiles ─────────────────────────────────────────── */
.tile {
    background: #161b27; border: 1px solid #1e2737;
    border-radius: 10px; padding: 1rem; text-align: center;
}
.tile-val { font-size: 1.7rem; font-weight: 800; color: #00d4aa; }
.tile-lbl { font-size: 0.68rem; color: #6b7280; text-transform: uppercase; letter-spacing: .5px; }

/* ── AI response box ──────────────────────────────────────── */
.ai-box {
    background: linear-gradient(135deg, #111827, #161b27);
    border: 1px solid #00d4aa; border-radius: 12px;
    padding: 1.4rem; color: #e2e8f0; line-height: 1.75;
    font-size: 0.9rem;
}
.ai-icon { font-size: 1.4rem; margin-bottom: .4rem; }

/* ── Odds card ────────────────────────────────────────────── */
.odds-card {
    background: #161b27; border: 1px solid #1e2737;
    border-radius: 10px; padding: .8rem 1rem;
}
.odds-label { font-size: 0.7rem; color: #6b7280; margin-bottom: 4px; }
.odds-val { font-size: 1.1rem; font-weight: 700; color: #f59e0b; }

/* ── Scrollbar ────────────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: #0d1117; }
::-webkit-scrollbar-thumb { background: #1e2737; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #00d4aa; }

/* ── Streamlit overrides ──────────────────────────────────── */
div[data-testid="stSelectbox"] > div,
div[data-testid="stMultiSelect"] > div,
div[data-testid="stDateInput"] > div {
    background: #161b27 !important; border-color: #1e2737 !important; color: #e2e8f0 !important;
}
.stButton > button {
    background: #00d4aa; color: #0d1117; font-weight: 700;
    border: none; border-radius: 8px; padding: .5rem 1.2rem;
}
.stButton > button:hover { background: #00b896; }
label, .stSelectbox label, .stSlider label { color: #9ca3af !important; font-size: 0.8rem !important; }
</style>
""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════
# Helper renderers
# ═════════════════════════════════════════════════════════════════

def _team(val: Any) -> Dict:
    """
    Normalise ANY team field shape to {"id": ..., "name": ...}.

    bzzoiro v2 can return:
      • dict  {"id": 123, "name": "Arsenal", ...}  ← normal
      • str   "Arsenal"                             ← compact form
      • None / missing                              ← safety
    """
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        return {"id": None, "name": val}
    return {"id": None, "name": "?"}


def _league_name(m: Dict) -> str:
    for key in ("league", "tournament"):
        val = m.get(key)
        if isinstance(val, dict):
            name = val.get("name", "")
            if name:
                return name
        elif isinstance(val, str) and val:
            return val
    return ""


def _score(m: Dict) -> tuple:
    score_obj = m.get("score")
    if isinstance(score_obj, dict):
        return str(score_obj.get("home", "")), str(score_obj.get("away", ""))
    h = m.get("home_score", "")
    a = m.get("away_score", "")
    return (str(h) if h is not None else ""), (str(a) if a is not None else "")


def render_match_card(m: Dict, live: bool = False) -> None:
    home = _team(m.get("home_team") or m.get("home"))
    away = _team(m.get("away_team") or m.get("away"))
    home_name = home.get("name", "?")
    away_name = away.get("name", "?")
    score_h, score_a = _score(m)
    league  = _league_name(m)
    kickoff = m.get("start_at", m.get("kickoff_at", m.get("event_date", "")))
    minute  = m.get("minute", "") or (m.get("time", {}) or {}).get("minute", "")

    time_str = ""
    if kickoff and len(kickoff) >= 16:
        time_str = kickoff[11:16]

    score_html = ""
    if live and minute:
        score_html = f'<div class="score live-score">{score_h} – {score_a}</div>'
    elif score_h != "" and score_a != "":
        score_html = f'<div class="score">{score_h} – {score_a}</div>'
    else:
        score_html = f'<div class="score ns">{time_str or "–"}</div>'

    minute_tag = f'<span class="minute-tag">{minute}′</span>' if (live and minute) else ""
    card_class = "match-card live-card" if live else "match-card"

    st.markdown(f"""
    <div class="{card_class}">
      <div class="mc-meta">
        <span class="league-tag">{league}</span>
        <span class="time-tag">{time_str} {minute_tag}</span>
      </div>
      <div class="mc-teams">
        <div class="team">{home_name}</div>
        {score_html}
        <div class="team away">{away_name}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def render_stat_bar(label: str, home_val, away_val) -> None:
    try:
        h = float(home_val) if home_val not in (None, "") else 0
        a = float(away_val) if away_val not in (None, "") else 0
        total = h + a
        pct_h = round(h / total * 100) if total else 50
        pct_a = 100 - pct_h
    except Exception:
        h, a, pct_h, pct_a = 0, 0, 50, 50

    st.markdown(f"""
    <div class="stat-wrapper">
      <div class="stat-meta">
        <span class="stat-name">{label}</span>
        <span class="stat-vals">{int(h)} — {int(a)}</span>
      </div>
      <div class="bar-track">
        <div class="bar-home" style="width:{pct_h}%"></div>
        <div class="bar-away" style="width:{pct_a}%"></div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def render_team_form(fixtures: List[Dict], team_id: int) -> str:
    """Return last-5 W/D/L HTML badges for a team."""
    badges = []
    for m in fixtures[:5]:
        home = _team(m.get("home_team") or m.get("home")).get("id")
        away = _team(m.get("away_team") or m.get("away")).get("id")
        score_h_str, score_a_str = _score(m)
        sh = int(score_h_str) if score_h_str.isdigit() else 0
        sa = int(score_a_str) if score_a_str.isdigit() else 0
        sh, sa = int(sh), int(sa)
        is_home = (home == team_id)
        if sh == sa:
            badges.append('<span class="badge d-badge">D</span>')
        elif (is_home and sh > sa) or (not is_home and sa > sh):
            badges.append('<span class="badge w-badge">W</span>')
        else:
            badges.append('<span class="badge l-badge">L</span>')
    return f'<div class="h2h-badges">{"".join(badges)}</div>'


def extract_stat(stats_side: Dict, key: str) -> float:
    """Safely extract a stat value that might be {value,total,pct} or a plain number."""
    val = stats_side.get(key, 0)
    if isinstance(val, dict):
        return float(val.get("value", 0) or 0)
    return float(val or 0)


def render_event_stats(event_id: int, home_name: str, away_name: str) -> None:
    stats_data = get_event_stats(event_id)
    if not stats_data:
        st.info("Статистиките не са налични за този мач.")
        return

    home_s = stats_data.get("home") or (stats_data.get("stats") or {}).get("home") or {}
    away_s = stats_data.get("away") or (stats_data.get("stats") or {}).get("away") or {}

    col1, col2 = st.columns([1, 1])
    col1.markdown(f"**{home_name}**")
    col2.markdown(f"**{away_name}**", )

    stat_fields = [
        ("Овладяване (%)",      "ball_possession"),
        ("Общо удари",          "total_shots"),
        ("В рамка",             "shots_on_target"),
        ("xG",                  "xg"),
        ("Ъглови",              "corner_kicks"),
        ("Предавания",          "passes"),
        ("Точни предавания (%)", "pass_accuracy_pct"),
        ("Фаулове",             "fouls"),
        ("Жълти картони",       "yellow_cards"),
        ("Спасявания",          "goalkeeper_saves"),
        ("Отнемания",           "tackles"),
        ("Прехващания",         "interceptions"),
        ("Опасни атаки",        "dangerous_attack"),
    ]

    for label, key in stat_fields:
        h_val = extract_stat(home_s, key)
        a_val = extract_stat(away_s, key)
        if h_val or a_val:
            render_stat_bar(label, h_val, a_val)


def render_odds_row(odds: Dict) -> None:
    mw = odds.get("odds", odds).get("match_winner", {}) or {}
    ou = odds.get("odds", odds).get("over_under", {}) or {}
    btts = odds.get("odds", odds).get("btts", {}) or {}
    if not any([mw, ou, btts]):
        return
    st.markdown("**Коефициенти (консенсус)**")
    cols = st.columns(7)
    pairs = [
        ("1", mw.get("home")), ("X", mw.get("draw")), ("2", mw.get("away")),
        ("O2.5", ou.get("over_25")), ("U2.5", ou.get("under_25")),
        ("BTTS Да", btts.get("yes")), ("BTTS Не", btts.get("no")),
    ]
    for col, (lbl, val) in zip(cols, pairs):
        with col:
            st.markdown(f"""
            <div class="odds-card">
              <div class="odds-label">{lbl}</div>
              <div class="odds-val">{f"{val:.2f}" if val else "–"}</div>
            </div>""", unsafe_allow_html=True)


def gemini_analyze(prompt: str) -> str:
    if not _gemini:
        return "❌ Gemini клиентът не е инициализиран. Проверете GEMINI_API_KEY."
    try:
        resp = _gemini.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=prompt,
        )
        return resp.text
    except Exception as e:
        return f"❌ Gemini грешка: {e}"


# ═════════════════════════════════════════════════════════════════
# Top bar
# ═════════════════════════════════════════════════════════════════

ws_mgr = get_ws_manager()
try:
    ws_mgr.start(st.secrets["BZZOIRO_API_KEY"])
except Exception:
    pass

st.markdown(f"""
<div class="topbar">
  <div class="logo">⚽ AI Football <span>Analytics</span></div>
  <div>{ws_mgr.status}</div>
</div>
""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════
# Tabs
# ═════════════════════════════════════════════════════════════════

tab_schedule, tab_live, tab_ai = st.tabs(["📅 Програма", "🔴 На Живо", "🤖 AI Анализ"])


# ─────────────────────────────────────────────────────────────────
# TAB 1 — ПРОГРАМА
# ─────────────────────────────────────────────────────────────────
with tab_schedule:
    st.markdown('<div class="sec-hd">Програма на мачовете</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1.5, 1.5, 1])
    with c1:
        sel_date = st.date_input("Дата", value=date.today(), label_visibility="visible")
    with c2:
        leagues_list = get_leagues()
        league_names = ["Всички"] + [l.get("name", "") for l in leagues_list]
        sel_league = st.selectbox("Лига", league_names)
    with c3:
        n_matches = st.slider("Последни мачове", 3, 20, 5, help="За статистики на отбор")

    date_str = sel_date.isoformat()
    league_id = None
    if sel_league != "Всички":
        match = next((l for l in leagues_list if l.get("name") == sel_league), None)
        league_id = match.get("id") if match else None

    with st.spinner("Зареждане на мачове…"):
        events = get_events(
            date_from=date_str, date_to=date_str,
            league_id=league_id, limit=100
        )

    if not events:
        st.info("Няма намерени мачове за избраните критерии.")
    else:
        left_col, right_col = st.columns([2, 3])

        with left_col:
            st.markdown(f'<div class="sec-hd">{len(events)} мача</div>', unsafe_allow_html=True)
            selected_event_idx = st.session_state.get("selected_event_idx", 0)

            for idx, m in enumerate(events):
                render_match_card(m)
                if st.button("Виж статистики", key=f"ev_{idx}", use_container_width=True):
                    st.session_state["selected_event_idx"] = idx
                    st.session_state["selected_event"] = m

        with right_col:
            sel_ev = st.session_state.get("selected_event")
            if sel_ev:
                home = _team(sel_ev.get("home_team") or sel_ev.get("home"))
                away = _team(sel_ev.get("away_team") or sel_ev.get("away"))
                home_id   = home.get("id")
                away_id   = away.get("id")
                home_name = home.get("name", "Домакин")
                away_name = away.get("name", "Гост")
                event_id  = sel_ev.get("id")

                st.markdown(f"### {home_name} – {away_name}")

                inner_tabs = st.tabs(["📊 Статистики на мача", f"🏠 {home_name}", f"✈️ {away_name}", "⚔️ H2H"])

                with inner_tabs[0]:
                    render_event_stats(event_id, home_name, away_name)
                    st.divider()
                    render_odds_row(get_event_odds(event_id))

                with inner_tabs[1]:
                    st.markdown(f'<div class="sec-hd">Последни {n_matches} мача — {home_name}</div>', unsafe_allow_html=True)
                    if home_id:
                        home_fixtures = get_team_fixtures(home_id, last_n=n_matches)
                        st.markdown(render_team_form(home_fixtures, home_id), unsafe_allow_html=True)
                        for fm in home_fixtures:
                            render_match_card(fm)
                            fid = fm.get("id")
                            fhome = _team(fm.get("home_team") or fm.get("home")).get("name","?")
                            faway = _team(fm.get("away_team") or fm.get("away")).get("name","?")
                            with st.expander(f"Статистики: {fhome} – {faway}"):
                                render_event_stats(fid, fhome, faway)

                with inner_tabs[2]:
                    st.markdown(f'<div class="sec-hd">Последни {n_matches} мача — {away_name}</div>', unsafe_allow_html=True)
                    if away_id:
                        away_fixtures = get_team_fixtures(away_id, last_n=n_matches)
                        st.markdown(render_team_form(away_fixtures, away_id), unsafe_allow_html=True)
                        for fm in away_fixtures:
                            render_match_card(fm)
                            fid = fm.get("id")
                            fhome = _team(fm.get("home_team") or fm.get("home")).get("name","?")
                            faway = _team(fm.get("away_team") or fm.get("away")).get("name","?")
                            with st.expander(f"Статистики: {fhome} – {faway}"):
                                render_event_stats(fid, fhome, faway)

                with inner_tabs[3]:
                    if home_id and away_id:
                        h2h_matches = get_h2h(home_id, away_id, last_n=10)
                        if not h2h_matches:
                            st.info("Няма намерени H2H мачове.")
                        else:
                            # Summary row
                            h_wins = d = a_wins = 0
                            for hm in h2h_matches:
                                _sh, _sa = _score(hm)
                                sh = int(_sh) if _sh.isdigit() else 0
                                sa = int(_sa) if _sa.isdigit() else 0
                                htid = _team(hm.get("home_team") or hm.get("home")).get("id")
                                if sh == sa:
                                    d += 1
                                elif htid == home_id and sh > sa:
                                    h_wins += 1
                                else:
                                    a_wins += 1

                            tc1, tc2, tc3 = st.columns(3)
                            tc1.markdown(f'<div class="tile"><div class="tile-val">{h_wins}</div><div class="tile-lbl">{home_name}</div></div>', unsafe_allow_html=True)
                            tc2.markdown(f'<div class="tile"><div class="tile-val">{d}</div><div class="tile-lbl">Равни</div></div>', unsafe_allow_html=True)
                            tc3.markdown(f'<div class="tile"><div class="tile-val">{a_wins}</div><div class="tile-lbl">{away_name}</div></div>', unsafe_allow_html=True)
                            st.markdown("")
                            for hm in h2h_matches:
                                render_match_card(hm)
            else:
                st.info("👈 Избери мач от лявата колона за детайли, статистики и H2H.")


# ─────────────────────────────────────────────────────────────────
# TAB 2 — НА ЖИВО
# Each live match has its own expandable panel:
#   top  → live stats + odds + situation (WebSocket)
#   bottom → inline Gemini chat window fed with live data
# ─────────────────────────────────────────────────────────────────
with tab_live:
    import time as _time

    # Drain WS queue first thing on every rerun
    ws_mgr.drain()

    # ── Controls bar ────────────────────────────────────────────
    ctrl1, ctrl2, ctrl3 = st.columns([2, 2, 1])
    with ctrl1:
        st.markdown('<div class="sec-hd">Мачове на живо</div>', unsafe_allow_html=True)
    with ctrl2:
        auto_refresh = st.toggle("🔄 Авто-обновяване (15 сек)", value=False)
    with ctrl3:
        st.markdown(f"**WS:** {ws_mgr.status}")

    live_events = get_live_events()

    if not live_events:
        st.info("⏳ Няма мачове на живо в момента. Провери по-късно.")
    else:
        # Ensure per-match chat history dict exists
        if "live_chats" not in st.session_state:
            st.session_state["live_chats"] = {}  # {event_id: [{"role","content"}, ...]}

        for lev in live_events:
            eid = lev.get("id")
            home = _team(lev.get("home_team") or lev.get("home"))
            away = _team(lev.get("away_team") or lev.get("away"))
            home_name = home.get("name", "Домакин")
            away_name = away.get("name", "Гост")

            # Auto-subscribe this match to WebSocket
            if eid and eid not in ws_mgr.subscribed:
                ws_mgr.subscribe(eid)

            snap = ws_mgr.snapshots.get(eid, {})

            # ── Score header from WS snapshot or API fallback ──
            _snap_score = snap.get("score") or {}
            _lev_sh, _lev_sa = _score(lev)
            score_h = _snap_score.get("home", _lev_sh or "–")
            score_a = _snap_score.get("away", _lev_sa or "–")
            minute   = (snap.get("time") or {}).get("minute", "")
            status   = (snap.get("time") or {}).get("status", "")
            league   = (lev.get("league") or lev.get("tournament") or {}).get("name", "")
            live_tick = snap.get("livedata", {})
            situation = (live_tick or {}).get("situation", "")
            sit_side  = (live_tick or {}).get("side", "")

            emoji_map = {
                "attack": "⚡", "goal": "⚽", "corner": "🚩",
                "free_kick": "🎯", "penalty": "🔴", "substitution": "🔄",
                "ball_safe": "🛡️", "dangerous_attack": "💥",
            }
            sit_icon = emoji_map.get(situation, "🏃") if situation else ""
            sit_side_str = home_name if sit_side == "home" else (away_name if sit_side == "away" else "")

            min_badge = f'<span class="minute-tag">{minute}′</span>' if minute else ""
            sit_badge = (
                f'<span style="font-size:.75rem;color:#9ca3af;margin-left:8px">'
                f'{sit_icon} {situation.replace("_"," ").title()} {f"· {sit_side_str}" if sit_side_str else ""}</span>'
            ) if situation else ""

            # Expander label: "⚽ Arsenal 2 – 1 Chelsea  45′"
            exp_label = f"🔴 {home_name}  {score_h} – {score_a}  {away_name}   {f'  {minute}′' if minute else ''}"

            with st.expander(exp_label, expanded=True):

                # ── Two-column layout: stats left, AI chat right ──
                stats_col, ai_col = st.columns([1, 1], gap="large")

                # ─── LEFT: live statistics ────────────────────────
                with stats_col:
                    st.markdown(f'<div class="sec-hd">{league} · Статистики {min_badge}{sit_badge}</div>', unsafe_allow_html=True)

                    ws_stats = snap.get("stats", {})
                    if ws_stats:
                        hs  = ws_stats.get("home", {})
                        as_ = ws_stats.get("away", {})

                        # Possession big display
                        poss_h = extract_stat(hs, "ball_possession")
                        poss_a = extract_stat(as_, "ball_possession")
                        st.markdown(f"""
                        <div style="display:flex;justify-content:space-between;margin-bottom:.3rem">
                          <span style="font-size:1.5rem;font-weight:800;color:#00d4aa">{int(poss_h)}%</span>
                          <span style="font-size:.7rem;color:#6b7280;align-self:center">ОВЛАДЯВАНЕ</span>
                          <span style="font-size:1.5rem;font-weight:800;color:#f59e0b">{int(poss_a)}%</span>
                        </div>""", unsafe_allow_html=True)

                        stat_pairs = [
                            ("Общо удари",      "total_shots"),
                            ("В рамка",         "shots_on_target"),
                            ("xG",              "xg"),
                            ("Ъглови",          "corner_kicks"),
                            ("Опасни атаки",    "dangerous_attack"),
                            ("Атаки",           "attack"),
                            ("Фаулове",         "fouls"),
                            ("Жълти картони",   "yellow_cards"),
                            ("Спасявания",      "goalkeeper_saves"),
                        ]
                        for lbl, key in stat_pairs:
                            hv = extract_stat(hs, key)
                            av = extract_stat(as_, key)
                            if hv or av:
                                render_stat_bar(lbl, hv, av)

                    else:
                        st.caption("⏳ Изчакване на WebSocket данни…")
                        render_event_stats(eid, home_name, away_name)

                    # Live odds row
                    ws_odds = snap.get("odds")
                    if ws_odds:
                        st.markdown("")
                        render_odds_row(ws_odds)

                # ─── RIGHT: inline Gemini chat window ─────────────
                with ai_col:
                    st.markdown(f'<div class="sec-hd">🤖 AI Анализ — {home_name} vs {away_name}</div>', unsafe_allow_html=True)

                    if not _gemini:
                        st.error("Добави GEMINI_API_KEY в Streamlit Secrets.")
                    else:
                        chat_key = f"live_chats_{eid}"
                        if chat_key not in st.session_state:
                            st.session_state[chat_key] = []

                        chat_history = st.session_state[chat_key]

                        # Display conversation history
                        for msg in chat_history:
                            role_icon = "🤖" if msg["role"] == "assistant" else "👤"
                            bg = "#161b27" if msg["role"] == "assistant" else "#1a2035"
                            border = "#00d4aa" if msg["role"] == "assistant" else "#1e2737"
                            st.markdown(f"""
                            <div style="background:{bg};border:1px solid {border};border-radius:8px;
                                        padding:.7rem 1rem;margin-bottom:.5rem;font-size:.85rem;
                                        color:#e2e8f0;line-height:1.6">
                              <span style="font-size:.7rem;color:#6b7280">{role_icon} {'AI' if msg["role"]=="assistant" else 'Ти'}</span><br>
                              {msg["content"]}
                            </div>""", unsafe_allow_html=True)

                        # Quick-action buttons (pre-made prompts)
                        qa_cols = st.columns(3)
                        quick_prompts = {
                            "📊 Обобщи": "Направи кратко обобщение на мача до момента.",
                            "⚽ Гол?": "Какъв е шансът за гол в следващите 10 минути?",
                            "💰 Залог?": "Има ли стойностен залог в момента? Кой и защо?",
                        }
                        for col, (btn_label, qprompt) in zip(qa_cols, quick_prompts.items()):
                            if col.button(btn_label, key=f"qa_{eid}_{btn_label}"):
                                st.session_state[f"pending_q_{eid}"] = qprompt

                        # Free text input
                        user_input = st.text_input(
                            "Задай въпрос…",
                            key=f"chat_input_{eid}",
                            placeholder="Как се представя домакинът в атака?",
                            label_visibility="collapsed",
                        )
                        send_col, clear_col = st.columns([3, 1])
                        do_send  = send_col.button("Изпрати ↗", key=f"send_{eid}")
                        do_clear = clear_col.button("Изчисти", key=f"clear_{eid}")

                        if do_clear:
                            st.session_state[chat_key] = []
                            st.rerun()

                        # Resolve question: typed or quick-action
                        question = None
                        if do_send and user_input.strip():
                            question = user_input.strip()
                        elif f"pending_q_{eid}" in st.session_state:
                            question = st.session_state.pop(f"pending_q_{eid}")

                        if question:
                            # Build rich live context for Gemini
                            ws_stats_now = snap.get("stats", {})
                            ws_odds_now  = snap.get("odds", {})
                            live_ctx = ""
                            if ws_stats_now:
                                hs  = ws_stats_now.get("home", {})
                                as_ = ws_stats_now.get("away", {})
                                live_ctx = f"""
ЖИВИ СТАТИСТИКИ (WebSocket):
  {home_name}: удари={extract_stat(hs,'total_shots')}, в рамка={extract_stat(hs,'shots_on_target')}, xG={extract_stat(hs,'xg')}, овладяване={extract_stat(hs,'ball_possession')}%, опасни атаки={extract_stat(hs,'dangerous_attack')}, ъглови={extract_stat(hs,'corner_kicks')}, жълти={extract_stat(hs,'yellow_cards')}
  {away_name}: удари={extract_stat(as_,'total_shots')}, в рамка={extract_stat(as_,'shots_on_target')}, xG={extract_stat(as_,'xg')}, овладяване={extract_stat(as_,'ball_possession')}%, опасни атаки={extract_stat(as_,'dangerous_attack')}, ъглови={extract_stat(as_,'corner_kicks')}, жълти={extract_stat(as_,'yellow_cards')}"""

                            odds_ctx = ""
                            if ws_odds_now:
                                mw = (ws_odds_now.get("odds") or ws_odds_now).get("match_winner", {}) or {}
                                ou = (ws_odds_now.get("odds") or ws_odds_now).get("over_under", {}) or {}
                                odds_ctx = f"\nКОЕФИЦИЕНТИ: 1={mw.get('home','?')} X={mw.get('draw','?')} 2={mw.get('away','?')} | O2.5={ou.get('over_25','?')} U2.5={ou.get('under_25','?')}"

                            sit_ctx = f"\nТЕКУЩА СИТУАЦИЯ: {situation} ({sit_side_str})" if situation else ""
                            min_ctx = f"\nМИНУТА: {minute}" if minute else ""

                            # Build conversation history for Gemini (last 6 turns for context)
                            history_ctx = ""
                            if chat_history:
                                recent = chat_history[-6:]
                                history_ctx = "\n\nИСТОРИЯ НА РАЗГОВОРА:\n" + "\n".join(
                                    f"{'AI' if m['role']=='assistant' else 'Потребител'}: {m['content']}"
                                    for m in recent
                                )

                            system_prompt = f"""Ти си футболен анализатор на живо. Говори на БЪЛГАРСКИ. Бъди кратък и конкретен — максимум 3-4 изречения освен ако не е поискано повече.

МАЧ: {home_name} срещу {away_name}
РЕЗУЛТАТ: {score_h} – {score_a}{min_ctx}{sit_ctx}
{live_ctx}{odds_ctx}{history_ctx}

Отговори на въпроса на базата на тези реални live данни."""

                            full_prompt = f"{system_prompt}\n\nВЪПРОС: {question}"

                            with st.spinner("AI анализира…"):
                                answer = gemini_analyze(full_prompt)

                            # Append to history
                            st.session_state[chat_key].append({"role": "user",      "content": question})
                            st.session_state[chat_key].append({"role": "assistant", "content": answer})
                            st.rerun()

    # ── Auto-refresh ─────────────────────────────────────────────
    if auto_refresh:
        _time.sleep(15)
        st.rerun()


# ─────────────────────────────────────────────────────────────────
# TAB 3 — AI АНАЛИЗ
# ─────────────────────────────────────────────────────────────────
with tab_ai:
    st.markdown('<div class="sec-hd">Gemini AI анализ</div>', unsafe_allow_html=True)

    ai_ev = st.session_state.get("ai_event") or st.session_state.get("selected_event")
    ai_source = st.session_state.get("ai_source", "schedule")

    if not _gemini:
        st.error("Gemini не е инициализиран. Добави GEMINI_API_KEY в Streamlit Secrets.")
    else:
        mode = st.radio(
            "Режим",
            ["Анализ на мач", "Свободен въпрос", "Стойностни залози"],
            horizontal=True,
        )

        if mode == "Анализ на мач":
            if not ai_ev:
                st.info("Избери мач от таб **Програма** или **На Живо** и натисни 🤖 AI.")
            else:
                home = _team(ai_ev.get("home_team") or ai_ev.get("home")).get("name", "?")
                away = _team(ai_ev.get("away_team") or ai_ev.get("away")).get("name", "?")
                eid = ai_ev.get("id")
                st.markdown(f"**Мач:** {home} – {away}  (ID {eid})")

                focus_options = [
                    "Общ анализ и прогноза",
                    "Тактически анализ",
                    "Залозни препоръки",
                    "Сравнение на форма",
                ]
                focus = st.selectbox("Фокус на анализа", focus_options)

                if st.button("🤖 Анализирай"):
                    with st.spinner("Gemini анализира…"):
                        # Collect data for context
                        stats = get_event_stats(eid)
                        odds  = get_event_odds(eid)
                        pred  = get_prediction(eid)
                        ws_snap = ws_mgr.snapshots.get(eid, {})
                        home_id = _team(ai_ev.get("home_team") or ai_ev.get("home")).get("id")
                        away_id = _team(ai_ev.get("away_team") or ai_ev.get("away")).get("id")
                        home_form = get_team_fixtures(home_id, 5) if home_id else []
                        away_form = get_team_fixtures(away_id, 5) if away_id else []
                        h2h = get_h2h(home_id, away_id, 5) if home_id and away_id else []

                        is_live = ai_source == "live" or bool(ws_snap.get("stats"))

                        prompt = f"""Ти си топ футболен анализатор. Говори на БЪЛГАРСКИ.

МАЧ: {home} срещу {away}
СТАТУС: {"НА ЖИВО" if is_live else "Предстоящ / Приключил"}
ФОКУС: {focus}

СТАТИСТИКИ НА МАЧА:
{json.dumps(stats, ensure_ascii=False, indent=2)[:1500]}

{"LIVE WS ДАННИ: " + json.dumps(ws_snap.get("stats", {}), ensure_ascii=False)[:800] if is_live else ""}

КОЕФИЦИЕНТИ: {json.dumps(odds, ensure_ascii=False)[:500]}

ML ПРОГНОЗА: {json.dumps(pred, ensure_ascii=False)[:400]}

ФОРМА {home} (последни 5): {[f"{_team(m.get('home_team') or m.get('home')).get('name','')} {'–'.join(_score(m))} {_team(m.get('away_team') or m.get('away')).get('name','')}" for m in home_form]}

ФОРМА {away} (последни 5): {[f"{_team(m.get('home_team') or m.get('home')).get('name','')} {'–'.join(_score(m))} {_team(m.get('away_team') or m.get('away')).get('name','')}" for m in away_form]}

H2H (последни 5): {[f"{_team(m.get('home_team') or m.get('home')).get('name','')} {'–'.join(_score(m))} {_team(m.get('away_team') or m.get('away')).get('name','')}" for m in h2h]}

Дай структуриран анализ. Бъди конкретен и директен. Включи ключови наблюдения, вероятни сценарии и конкретна препоръка."""

                        result = gemini_analyze(prompt)

                    st.markdown(f'<div class="ai-box"><div class="ai-icon">🤖</div>{result}</div>', unsafe_allow_html=True)

        elif mode == "Свободен въпрос":
            user_q = st.text_area("Въпрос към AI", placeholder="Напр. Кой е фаворит в тази среща и защо?", height=100)
            context_match = ""
            if ai_ev:
                home = _team(ai_ev.get("home_team") or ai_ev.get("home")).get("name", "")
                away = _team(ai_ev.get("away_team") or ai_ev.get("away")).get("name", "")
                context_match = f"Контекст — текущо избран мач: {home} срещу {away}."

            if st.button("🤖 Изпрати") and user_q:
                with st.spinner("Gemini мисли…"):
                    result = gemini_analyze(f"Ти си футболен анализатор. Говори на БЪЛГАРСКИ.\n{context_match}\n\nВъпрос: {user_q}")
                st.markdown(f'<div class="ai-box">{result}</div>', unsafe_allow_html=True)

        elif mode == "Стойностни залози":
            val_date = st.date_input("Дата за стойностни залози", value=date.today())
            if st.button("🔍 Анализирай програмата"):
                with st.spinner("Зареждане и анализ…"):
                    day_events = get_events(date_from=val_date.isoformat(), date_to=val_date.isoformat(), limit=30)
                    events_summary = []
                    for ev in day_events[:15]:
                        h = _team(ev.get("home_team") or ev.get("home")).get("name","?")
                        a = _team(ev.get("away_team") or ev.get("away")).get("name","?")
                        lg = (ev.get("league") or ev.get("tournament") or {}).get("name","?")
                        events_summary.append(f"{lg}: {h} – {a}")

                    prompt = f"""Ти си експерт по стойностни залози. Говори на БЪЛГАРСКИ.
Програма за {val_date}:
{chr(10).join(events_summary)}

Анализирай кои мачове имат потенциал за стойностни залози. Обясни логиката си. 
Препоръчай максимум 3 залога с аргументи. НЕ давай конкретни коефициенти."""

                    result = gemini_analyze(prompt)
                st.markdown(f'<div class="ai-box">{result}</div>', unsafe_allow_html=True)
