"""
⚽ AI Football Analytics
Tabs: 1. Програма  2. На Живо
"""

import streamlit as st
st.set_page_config(page_title="AI Football Analytics", page_icon="⚽",
                   layout="wide", initial_sidebar_state="collapsed")

import json
from datetime import date, timedelta, datetime, timezone
from typing import Dict, List, Any, Optional

from api import (
    get_events, get_live_events, get_event_stats,
    get_event_odds, get_team_fixtures, get_h2h,
    get_leagues, get_prediction,
)
from ws_manager import get_ws_manager

# ── Gemini ───────────────────────────────────────────────────────
try:
    from google import genai as _gai
    _gemini = _gai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except Exception:
    _gemini = None


# ═════════════════════════════════════════════════════════════════
# TIMEZONE — Bulgaria EEST UTC+3 (summer) / EET UTC+2 (winter)
# ═════════════════════════════════════════════════════════════════
_BG = timezone(timedelta(hours=3))   # EEST (Nov→Mar use +2)

def bg_time(utc_str: str) -> str:
    """Return HH:MM in Bulgarian time from any UTC-ish string."""
    if not utc_str:
        return ""
    s = utc_str.strip().replace("Z", "").replace("z", "")
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M",    "%Y-%m-%d %H:%M"):
        try:
            dt = datetime.strptime(s[:16], fmt[:16])
            return (dt + timedelta(hours=3)).strftime("%H:%M")
        except ValueError:
            continue
    return s[11:16] if len(s) >= 16 else ""


# ═════════════════════════════════════════════════════════════════
# CSS
# ═════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

.stApp,[data-testid="stAppViewContainer"]{background:#0d1117!important;font-family:'Inter',sans-serif}
[data-testid="stSidebar"]{background:#0d1117}
.block-container{padding:.75rem 1.5rem 2rem;max-width:1400px}
#MainMenu,footer,header{visibility:hidden}

/* topbar */
.topbar{display:flex;align-items:center;justify-content:space-between;
  padding:.8rem 0;margin-bottom:1.2rem;border-bottom:1px solid #1e2737}
.logo{font-size:1.5rem;font-weight:900;color:#fff;letter-spacing:-.5px}
.logo span{color:#00d4aa}

/* tabs */
.stTabs [data-baseweb="tab-list"]{background:#161b27;border-radius:10px;
  padding:4px;gap:4px;border:1px solid #1e2737}
.stTabs [data-baseweb="tab"]{background:transparent;color:#6b7280;border-radius:7px;
  font-weight:600;font-size:.85rem;padding:.55rem 1.4rem}
.stTabs [aria-selected="true"]{background:#00d4aa!important;color:#0d1117!important}
.stTabs [data-baseweb="tab-panel"]{padding-top:1rem}

/* section header */
.sec-hd{font-size:.7rem;font-weight:700;color:#4b5563;text-transform:uppercase;
  letter-spacing:1.5px;padding-bottom:.5rem;margin:1rem 0 .6rem;border-bottom:1px solid #1e2737}

/* match row */
.mrow{display:flex;align-items:center;justify-content:space-between;
  background:#161b27;border:1px solid #1e2737;border-radius:10px;
  padding:.75rem 1rem;margin-bottom:.4rem;gap:.5rem}
.mrow:hover{border-color:#00d4aa}
.mrow.live{border-color:rgba(239,68,68,.4)}
.mrow-lg{font-size:.65rem;color:#6b7280;font-weight:600;white-space:nowrap;
  overflow:hidden;text-overflow:ellipsis;max-width:120px}
.mrow-teams{display:flex;align-items:center;gap:.4rem;flex:1;justify-content:center}
.team-name{font-size:.88rem;font-weight:600;color:#e2e8f0;text-align:right;flex:1}
.team-name.away{text-align:left}
.score-badge{background:#1e2737;border-radius:6px;padding:4px 12px;
  font-size:1rem;font-weight:800;color:#00d4aa;letter-spacing:2px;white-space:nowrap}
.score-badge.live{background:rgba(239,68,68,.12);color:#ef4444;
  border:1px solid rgba(239,68,68,.25)}
.score-badge.upcoming{color:#4b5563;font-size:.8rem}
.mrow-time{font-size:.72rem;color:#6b7280;white-space:nowrap;text-align:right;min-width:42px}
.minute-tag{font-size:.68rem;color:#ef4444;font-weight:700;
  background:rgba(239,68,68,.1);border-radius:4px;padding:2px 5px}

/* stat bars */
.stat-wrap{margin:.35rem 0}
.stat-meta{display:flex;justify-content:space-between;margin-bottom:2px}
.stat-name{font-size:.7rem;color:#6b7280}
.stat-vals{font-size:.7rem;color:#e2e8f0;font-weight:700}
.bar-track{width:100%;height:5px;background:#1e2737;border-radius:3px;
  overflow:hidden;display:flex}
.bar-home{height:100%;border-radius:3px 0 0 3px;
  background:linear-gradient(90deg,#00d4aa,#0ea5e9)}
.bar-away{height:100%;border-radius:0 3px 3px 0;
  background:linear-gradient(90deg,#f59e0b,#ef4444)}

/* form badges */
.form-row{display:flex;gap:4px;flex-wrap:wrap;margin:.3rem 0}
.fb{width:24px;height:24px;border-radius:4px;font-size:.6rem;font-weight:800;
  display:inline-flex;align-items:center;justify-content:center}
.fw{background:rgba(34,197,94,.2);color:#22c55e}
.fd{background:rgba(234,179,8,.2);color:#eab308}
.fl{background:rgba(239,68,68,.2);color:#ef4444}

/* tiles */
.tile{background:#161b27;border:1px solid #1e2737;border-radius:10px;
  padding:.8rem;text-align:center}
.tile-val{font-size:1.6rem;font-weight:800;color:#00d4aa}
.tile-lbl{font-size:.65rem;color:#6b7280;text-transform:uppercase;letter-spacing:.5px}

/* odds */
.odds-card{background:#161b27;border:1px solid #1e2737;border-radius:8px;padding:.6rem .8rem;text-align:center}
.odds-lbl{font-size:.65rem;color:#6b7280;margin-bottom:3px}
.odds-val{font-size:1rem;font-weight:700;color:#f59e0b}

/* AI chat */
.ai-msg-ai{background:#111827;border:1px solid #00d4aa;border-radius:8px;
  padding:.7rem 1rem;margin:.35rem 0;font-size:.85rem;color:#e2e8f0;line-height:1.65}
.ai-msg-user{background:#1a2035;border:1px solid #1e2737;border-radius:8px;
  padding:.6rem 1rem;margin:.35rem 0;font-size:.85rem;color:#9ca3af}
.ai-role{font-size:.65rem;color:#4b5563;margin-bottom:3px}

/* expander overrides */
details summary{color:#e2e8f0!important}
[data-testid="stExpander"]{background:#161b27!important;border:1px solid #1e2737!important;
  border-radius:10px!important;margin-bottom:.4rem!important}
[data-testid="stExpander"]:hover{border-color:#00d4aa!important}

/* inputs */
div[data-testid="stSelectbox"]>div,div[data-testid="stDateInput"]>div{
  background:#161b27!important;border-color:#1e2737!important;color:#e2e8f0!important}
.stTextInput input{background:#161b27!important;border-color:#1e2737!important;
  color:#e2e8f0!important;border-radius:8px!important}
.stButton>button{background:#00d4aa;color:#0d1117;font-weight:700;
  border:none;border-radius:8px;padding:.45rem 1rem}
.stButton>button:hover{background:#00b896}
label{color:#9ca3af!important;font-size:.8rem!important}
::-webkit-scrollbar{width:5px}
::-webkit-scrollbar-track{background:#0d1117}
::-webkit-scrollbar-thumb{background:#1e2737;border-radius:3px}
</style>
""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════
# DATA HELPERS
# ═════════════════════════════════════════════════════════════════

def _team(val: Any) -> Dict:
    """Normalize team field → always {"id":..., "name":...}"""
    if isinstance(val, dict):  return val
    if isinstance(val, str):   return {"id": None, "name": val}
    return {"id": None, "name": "?"}

def _league(m: Dict) -> str:
    for k in ("league", "tournament", "competition"):
        v = m.get(k)
        if isinstance(v, dict) and v.get("name"): return v["name"]
        if isinstance(v, str) and v: return v
    return ""

def _score(m: Dict):
    s = m.get("score")
    if isinstance(s, dict):
        return str(s.get("home", "")), str(s.get("away", ""))
    h = m.get("home_score", ""); a = m.get("away_score", "")
    return (str(h) if h is not None else ""), (str(a) if a is not None else "")

def _status(m: Dict) -> str:
    st_raw = m.get("status", m.get("event_status", ""))
    if isinstance(st_raw, dict): st_raw = st_raw.get("type", "")
    return str(st_raw).lower()

def _kickoff(m: Dict) -> str:
    for k in ("start_at", "kickoff_at", "event_date", "scheduled"):
        v = m.get(k)
        if v: return bg_time(str(v))
    return ""

def _minute(m: Dict) -> str:
    return str(m.get("minute", "") or (m.get("time") or {}).get("minute", "") or "")

def extract_stat(d: Dict, key: str) -> float:
    v = d.get(key, 0)
    if isinstance(v, dict): return float(v.get("value", 0) or 0)
    return float(v or 0)


# ═════════════════════════════════════════════════════════════════
# RENDER HELPERS
# ═════════════════════════════════════════════════════════════════

def render_match_row(m: Dict, live: bool = False):
    home_name = _team(m.get("home_team") or m.get("home")).get("name","?")
    away_name = _team(m.get("away_team") or m.get("away")).get("name","?")
    sh, sa    = _score(m)
    league    = _league(m)
    ko        = _kickoff(m)
    minute    = _minute(m)
    status    = _status(m)

    if live and minute:
        score_html = f'<span class="score-badge live">{sh} – {sa}</span>'
        time_html  = f'<span class="minute-tag">{minute}′</span>'
    elif sh and sa:
        score_html = f'<span class="score-badge">{sh} – {sa}</span>'
        time_html  = f'<span class="mrow-time">{ko}</span>'
    else:
        score_html = f'<span class="score-badge upcoming">{ko or "–"}</span>'
        time_html  = ""

    cls = "mrow live" if live else "mrow"
    st.markdown(f"""
    <div class="{cls}">
      <span class="mrow-lg" title="{league}">{league}</span>
      <div class="mrow-teams">
        <span class="team-name">{home_name}</span>
        {score_html}
        <span class="team-name away">{away_name}</span>
      </div>
      {time_html}
    </div>""", unsafe_allow_html=True)


def render_stat_bar(label: str, hv, av):
    try:
        h, a = float(hv or 0), float(av or 0)
        total = h + a
        ph = round(h/total*100) if total else 50
    except: h, a, ph = 0, 0, 50
    pa = 100 - ph
    st.markdown(f"""
    <div class="stat-wrap">
      <div class="stat-meta">
        <span class="stat-name">{label}</span>
        <span class="stat-vals">{int(h)} — {int(a)}</span>
      </div>
      <div class="bar-track">
        <div class="bar-home" style="width:{ph}%"></div>
        <div class="bar-away" style="width:{pa}%"></div>
      </div>
    </div>""", unsafe_allow_html=True)


def render_event_stats_panel(event_id: int, home_name: str, away_name: str):
    data = get_event_stats(event_id)
    if not data:
        st.caption("Статистиките не са налични за този мач.")
        return
    hs = data.get("home") or (data.get("stats") or {}).get("home") or {}
    as_ = data.get("away") or (data.get("stats") or {}).get("away") or {}
    pairs = [
        ("Овладяване (%)", "ball_possession"),
        ("Общо удари",     "total_shots"),
        ("В рамка",        "shots_on_target"),
        ("xG",             "xg"),
        ("Ъглови",         "corner_kicks"),
        ("Опасни атаки",   "dangerous_attack"),
        ("Атаки",          "attack"),
        ("Фаулове",        "fouls"),
        ("Жълти картони",  "yellow_cards"),
        ("Червени картони","red_cards"),
        ("Спасявания",     "goalkeeper_saves"),
        ("Офсайди",        "offsides"),
        ("Предавания",     "passes"),
    ]
    shown = False
    for lbl, key in pairs:
        h_v = extract_stat(hs, key); a_v = extract_stat(as_, key)
        if h_v or a_v:
            render_stat_bar(lbl, h_v, a_v)
            shown = True
    if not shown:
        st.caption("Статистиките не са налични.")


def render_form_badges(fixtures: List[Dict], team_id) -> str:
    badges = []
    for m in fixtures[:5]:
        sh, sa = _score(m)
        try: sh, sa = int(sh), int(sa)
        except: continue
        htid = _team(m.get("home_team") or m.get("home")).get("id")
        is_home = (htid == team_id) if team_id else True
        if sh == sa:   badges.append('<span class="fb fd">D</span>')
        elif (is_home and sh > sa) or (not is_home and sa > sh):
                       badges.append('<span class="fb fw">W</span>')
        else:          badges.append('<span class="fb fl">L</span>')
    return f'<div class="form-row">{"".join(badges)}</div>' if badges else ""


def render_odds_row(odds: Dict):
    mw   = (odds.get("odds") or odds).get("match_winner") or {}
    ou   = (odds.get("odds") or odds).get("over_under")   or {}
    btts = (odds.get("odds") or odds).get("btts")         or {}
    pairs = [("1", mw.get("home")), ("X", mw.get("draw")), ("2", mw.get("away")),
             ("O2.5", ou.get("over_25")), ("U2.5", ou.get("under_25")),
             ("GG", btts.get("yes")), ("NG", btts.get("no"))]
    valid = [(l,v) for l,v in pairs if v]
    if not valid: return
    cols = st.columns(len(valid))
    for col, (lbl, val) in zip(cols, valid):
        with col:
            st.markdown(f"""<div class="odds-card">
              <div class="odds-lbl">{lbl}</div>
              <div class="odds-val">{float(val):.2f}</div>
            </div>""", unsafe_allow_html=True)


def render_inline_ai(match_obj: Dict, chat_key: str,
                     home_name: str, away_name: str,
                     extra_ctx: str = ""):
    """Inline AI chat widget for a specific match."""
    if not _gemini:
        st.caption("GEMINI_API_KEY не е настроен.")
        return

    if chat_key not in st.session_state:
        st.session_state[chat_key] = []
    hist = st.session_state[chat_key]

    # Display history
    for msg in hist:
        cls  = "ai-msg-ai"   if msg["role"] == "assistant" else "ai-msg-user"
        icon = "🤖 AI"       if msg["role"] == "assistant" else "👤 Ти"
        st.markdown(f'<div class="{cls}"><div class="ai-role">{icon}</div>{msg["content"]}</div>',
                    unsafe_allow_html=True)

    # Quick buttons
    qb1, qb2, qb3, qb4 = st.columns(4)
    quick = {
        qb1: "📊 Обобщи мача",
        qb2: "⚽ Очаквам гол?",
        qb3: "💰 Стойностен залог?",
        qb4: "🎯 Тактики?",
    }
    for col, label in quick.items():
        if col.button(label, key=f"{chat_key}_{label}"):
            st.session_state[f"{chat_key}_pending"] = label

    # Text input
    user_q = st.text_input("Въпрос…", key=f"{chat_key}_inp",
                           placeholder="Питай AI за мача…",
                           label_visibility="collapsed")
    c1, c2 = st.columns([4, 1])
    send  = c1.button("Изпрати ↗", key=f"{chat_key}_send")
    if c2.button("Изчисти", key=f"{chat_key}_clr"):
        st.session_state[chat_key] = []
        st.rerun()

    question = None
    if send and user_q.strip():
        question = user_q.strip()
    elif f"{chat_key}_pending" in st.session_state:
        question = st.session_state.pop(f"{chat_key}_pending")

    if question:
        sh, sa = _score(match_obj)
        status = _status(match_obj)
        ko     = _kickoff(match_obj)
        min_   = _minute(match_obj)
        hist_ctx = ""
        if hist:
            hist_ctx = "\nИСТОРИЯ:\n" + "\n".join(
                f"{'AI' if m['role']=='assistant' else 'Ти'}: {m['content']}"
                for m in hist[-6:])
        prompt = f"""Ти си футболен анализатор. Говори САМО на БЪЛГАРСКИ. Бъди кратък и конкретен.

МАЧ: {home_name} срещу {away_name}
СТАТУС: {status}  РЕЗУЛТАТ: {sh}–{sa}  {f"Минута: {min_}'" if min_ else f"Начало: {ko} (BG)"}
{extra_ctx}{hist_ctx}

ВЪПРОС: {question}"""
        with st.spinner("AI анализира…"):
            try:
                resp = _gemini.models.generate_content(
                    model="gemini-3.1-flash-lite", contents=prompt)
                answer = resp.text
            except Exception as e:
                answer = f"Грешка: {e}"
        st.session_state[chat_key].append({"role": "user",      "content": question})
        st.session_state[chat_key].append({"role": "assistant", "content": answer})
        st.rerun()


# ═════════════════════════════════════════════════════════════════
# STARTUP
# ═════════════════════════════════════════════════════════════════
ws_mgr = get_ws_manager()
try:
    ws_mgr.start(st.secrets["BZZOIRO_API_KEY"])
except Exception:
    pass

st.markdown(f"""
<div class="topbar">
  <div class="logo">⚽ AI Football <span>Analytics</span></div>
  <div style="font-size:.8rem;color:#6b7280">{ws_mgr.status} &nbsp;|&nbsp; 🕐 BG (UTC+3)</div>
</div>""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════
# TABS
# ═════════════════════════════════════════════════════════════════
tab_schedule, tab_live = st.tabs(["📅 Програма", "🔴 На Живо"])


# ─────────────────────────────────────────────────────────────────
# TAB 1 — ПРОГРАМА
# Design: full-width expander per match.
#   Upcoming  → Form A | Form B | H2H | Коефициенти | 🤖 AI
#   Finished  → Статистики | Form A | Form B | H2H | 🤖 AI
# ─────────────────────────────────────────────────────────────────
with tab_schedule:

    # ── Filters ─────────────────────────────────────────────────
    fc1, fc2, fc3 = st.columns([1.5, 2, 1])
    with fc1:
        sel_date = st.date_input("Дата", value=date.today())
    with fc2:
        leagues_list = get_leagues()
        lnames = ["Всички"] + [l.get("name","") for l in leagues_list if l.get("name")]
        sel_lg = st.selectbox("Лига", lnames)
    with fc3:
        n_last = st.slider("Посл. мачове", 3, 15, 5)

    date_str  = sel_date.isoformat()
    league_id = None
    if sel_lg != "Всички":
        lobj = next((l for l in leagues_list if l.get("name") == sel_lg), None)
        if lobj: league_id = lobj.get("id")

    with st.spinner("Зареждане…"):
        events = get_events(date_from=date_str, date_to=date_str,
                            league_id=league_id, limit=100)

    if not events:
        st.info("Няма намерени мачове за тази дата.")
    else:
        # Group by league
        from collections import defaultdict
        by_league: Dict[str, List] = defaultdict(list)
        for m in events:
            by_league[_league(m) or "Без лига"].append(m)

        for lg_name, matches in by_league.items():
            st.markdown(f'<div class="sec-hd">{lg_name}</div>', unsafe_allow_html=True)

            for m in matches:
                eid       = m.get("id")
                home_obj  = _team(m.get("home_team") or m.get("home"))
                away_obj  = _team(m.get("away_team") or m.get("away"))
                home_name = home_obj.get("name","?")
                away_name = away_obj.get("name","?")
                home_id   = home_obj.get("id")
                away_id   = away_obj.get("id")
                sh, sa    = _score(m)
                ko        = _kickoff(m)
                status    = _status(m)
                minute    = _minute(m)

                is_live     = status in ("inprogress","live","1h","2h","ht","et","pen")
                is_finished = status in ("finished","ft","aet","pen_finished","ended")
                is_upcoming = not is_live and not is_finished

                # Expander label
                if is_live:
                    exp_label = f"🔴  {home_name}  {sh}–{sa}  {away_name}   ({minute}′)"
                elif is_finished:
                    exp_label = f"✅  {home_name}  {sh}–{sa}  {away_name}   {ko}"
                else:
                    exp_label = f"🕐  {home_name}  vs  {away_name}   {ko or '–'} BG"

                with st.expander(exp_label, expanded=False):

                    # ── Build context string for AI ───────────────
                    def _build_ai_ctx(hid, aid, eid, is_fin, n):
                        ctx = ""
                        if is_fin and eid:
                            d = get_event_stats(eid)
                            if d:
                                hs  = d.get("home") or {}
                                as_ = d.get("away") or {}
                                ctx += (f"\nСТАТИСТИКИ: {home_name} удари={extract_stat(hs,'total_shots')} "
                                        f"xG={extract_stat(hs,'xg')} поз={extract_stat(hs,'ball_possession')}% | "
                                        f"{away_name} удари={extract_stat(as_,'total_shots')} "
                                        f"xG={extract_stat(as_,'xg')} поз={extract_stat(as_,'ball_possession')}%")
                        if hid and aid:
                            h2h = get_h2h(hid, aid, last_n=5)
                            if h2h:
                                ctx += "\nH2H (последни 5): " + ", ".join(
                                    f"{_team(x.get('home_team') or x.get('home')).get('name','?')} "
                                    f"{_score(x)[0]}–{_score(x)[1]} "
                                    f"{_team(x.get('away_team') or x.get('away')).get('name','?')}"
                                    for x in h2h)
                        if hid:
                            hf = get_team_fixtures(hid, last_n=5)
                            if hf:
                                ctx += f"\nФОРМА {home_name}: " + " ".join(
                                    f"{_score(x)[0]}–{_score(x)[1]}" for x in hf[:5])
                        if aid:
                            af = get_team_fixtures(aid, last_n=5)
                            if af:
                                ctx += f"\nФОРМА {away_name}: " + " ".join(
                                    f"{_score(x)[0]}–{_score(x)[1]}" for x in af[:5])
                        return ctx

                    # ── Build tabs ────────────────────────────────
                    if is_finished:
                        inner = st.tabs([
                            "📊 Статистики",
                            f"🏠 {home_name[:15]}",
                            f"✈️ {away_name[:15]}",
                            "⚔️ H2H",
                            "💰 Коефициенти",
                            "🤖 AI",
                        ])
                        # 0 — Match stats
                        with inner[0]:
                            if eid:
                                render_event_stats_panel(eid, home_name, away_name)
                            else:
                                st.caption("Няма ID за статистики.")
                        # 1 & 2 — Team form
                        for tab_idx, (tid, tname) in enumerate(
                                [(home_id, home_name), (away_id, away_name)], start=1):
                            with inner[tab_idx]:
                                if not tid:
                                    st.caption("ID на отбора не е наличен.")
                                    continue
                                fixes = get_team_fixtures(tid, last_n=n_last)
                                if not fixes:
                                    st.caption("Няма минали мачове.")
                                    continue
                                st.markdown(render_form_badges(fixes, tid),
                                            unsafe_allow_html=True)
                                for fm in fixes:
                                    fid = fm.get("id")
                                    fh  = _team(fm.get("home_team") or fm.get("home")).get("name","?")
                                    fa  = _team(fm.get("away_team") or fm.get("away")).get("name","?")
                                    fsh, fsa = _score(fm)
                                    fko = _kickoff(fm)
                                    render_match_row(fm)
                                    if fid:
                                        with st.expander(f"Статистики: {fh} {fsh}–{fsa} {fa}  ({fko})",
                                                         expanded=False):
                                            render_event_stats_panel(fid, fh, fa)
                        # 3 — H2H
                        with inner[3]:
                            if home_id and away_id:
                                h2h = get_h2h(home_id, away_id, last_n=10)
                                if not h2h:
                                    st.info("Няма H2H мачове.")
                                else:
                                    hw = dw = aw = 0
                                    for hm in h2h:
                                        hmsh, hmsa = _score(hm)
                                        try: hmsh, hmsa = int(hmsh), int(hmsa)
                                        except: continue
                                        htid = _team(hm.get("home_team") or hm.get("home")).get("id")
                                        if hmsh == hmsa: dw += 1
                                        elif htid == home_id and hmsh > hmsa: hw += 1
                                        else: aw += 1
                                    tc1, tc2, tc3 = st.columns(3)
                                    tc1.markdown(f'<div class="tile"><div class="tile-val">{hw}</div>'
                                                 f'<div class="tile-lbl">{home_name[:12]}</div></div>',
                                                 unsafe_allow_html=True)
                                    tc2.markdown(f'<div class="tile"><div class="tile-val">{dw}</div>'
                                                 f'<div class="tile-lbl">Равни</div></div>',
                                                 unsafe_allow_html=True)
                                    tc3.markdown(f'<div class="tile"><div class="tile-val">{aw}</div>'
                                                 f'<div class="tile-lbl">{away_name[:12]}</div></div>',
                                                 unsafe_allow_html=True)
                                    st.markdown("")
                                    for hm in h2h:
                                        render_match_row(hm)
                            else:
                                st.caption("Липсват ID-та на отборите за H2H.")
                        # 4 — Odds
                        with inner[4]:
                            odds = get_event_odds(eid) if eid else {}
                            if odds: render_odds_row(odds)
                            else:    st.caption("Нема коефициенти.")
                        # 5 — AI
                        with inner[5]:
                            ctx = _build_ai_ctx(home_id, away_id, eid, True, n_last)
                            render_inline_ai(m, f"ai_fin_{eid}", home_name, away_name, ctx)

                    else:
                        # UPCOMING or LIVE in schedule
                        inner = st.tabs([
                            f"🏠 {home_name[:15]}",
                            f"✈️ {away_name[:15]}",
                            "⚔️ H2H",
                            "💰 Коефициенти",
                            "🤖 AI",
                        ])
                        # 0 & 1 — Team form
                        for tab_idx, (tid, tname) in enumerate(
                                [(home_id, home_name), (away_id, away_name)]):
                            with inner[tab_idx]:
                                if not tid:
                                    st.caption("ID на отбора не е наличен — API-то връща само имена за предстоящи мачове.")
                                    continue
                                fixes = get_team_fixtures(tid, last_n=n_last)
                                if not fixes:
                                    st.caption("Няма минали мачове.")
                                    continue
                                st.markdown(render_form_badges(fixes, tid),
                                            unsafe_allow_html=True)
                                for fm in fixes:
                                    fid = fm.get("id")
                                    fh  = _team(fm.get("home_team") or fm.get("home")).get("name","?")
                                    fa  = _team(fm.get("away_team") or fm.get("away")).get("name","?")
                                    fsh, fsa = _score(fm)
                                    fko = _kickoff(fm)
                                    render_match_row(fm)
                                    if fid:
                                        with st.expander(f"Статистики: {fh} {fsh}–{fsa} {fa}  ({fko})",
                                                         expanded=False):
                                            render_event_stats_panel(fid, fh, fa)
                        # 2 — H2H
                        with inner[2]:
                            if home_id and away_id:
                                h2h = get_h2h(home_id, away_id, last_n=10)
                                if not h2h:
                                    st.info("Няма H2H мачове.")
                                else:
                                    hw = dw = aw = 0
                                    for hm in h2h:
                                        hmsh, hmsa = _score(hm)
                                        try: hmsh, hmsa = int(hmsh), int(hmsa)
                                        except: continue
                                        htid = _team(hm.get("home_team") or hm.get("home")).get("id")
                                        if hmsh == hmsa: dw += 1
                                        elif htid == home_id and hmsh > hmsa: hw += 1
                                        else: aw += 1
                                    tc1, tc2, tc3 = st.columns(3)
                                    tc1.markdown(f'<div class="tile"><div class="tile-val">{hw}</div>'
                                                 f'<div class="tile-lbl">{home_name[:12]}</div></div>',
                                                 unsafe_allow_html=True)
                                    tc2.markdown(f'<div class="tile"><div class="tile-val">{dw}</div>'
                                                 f'<div class="tile-lbl">Равни</div></div>',
                                                 unsafe_allow_html=True)
                                    tc3.markdown(f'<div class="tile"><div class="tile-val">{aw}</div>'
                                                 f'<div class="tile-lbl">{away_name[:12]}</div></div>',
                                                 unsafe_allow_html=True)
                                    st.markdown("")
                                    for hm in h2h:
                                        render_match_row(hm)
                            else:
                                st.caption("Липсват ID-та на отборите за H2H.")
                        # 3 — Odds + prediction
                        with inner[3]:
                            odds = get_event_odds(eid) if eid else {}
                            if odds: render_odds_row(odds)
                            pred = get_prediction(eid) if eid else {}
                            if pred:
                                st.markdown("")
                                st.markdown("**ML Прогноза**")
                                pc1, pc2, pc3 = st.columns(3)
                                ph = pred.get("home_win_pct") or pred.get("home_probability")
                                pd_ = pred.get("draw_pct")    or pred.get("draw_probability")
                                pa  = pred.get("away_win_pct") or pred.get("away_probability")
                                if ph: pc1.metric("1", f"{float(ph):.0f}%")
                                if pd_: pc2.metric("X", f"{float(pd_):.0f}%")
                                if pa: pc3.metric("2", f"{float(pa):.0f}%")
                            if not odds and not pred:
                                st.caption("Нема коефициенти.")
                        # 4 — AI
                        with inner[4]:
                            ctx = _build_ai_ctx(home_id, away_id, eid, False, n_last)
                            render_inline_ai(m, f"ai_up_{eid}", home_name, away_name, ctx)


# ─────────────────────────────────────────────────────────────────
# TAB 2 — НА ЖИВО
# ─────────────────────────────────────────────────────────────────
with tab_live:
    import time as _time

    ws_mgr.drain()

    cc1, cc2, cc3 = st.columns([3, 2, 1])
    with cc1: st.markdown('<div class="sec-hd">Мачове на живо</div>', unsafe_allow_html=True)
    with cc2: auto_ref = st.toggle("🔄 Авто (15 сек)", value=False)
    with cc3: st.caption(ws_mgr.status)

    live_events = get_live_events()

    if not live_events:
        st.info("⏳ Няма мачове на живо в момента.")
    else:
        if "live_chats" not in st.session_state:
            st.session_state["live_chats"] = {}

        for lev in live_events:
            eid       = lev.get("id")
            home_obj  = _team(lev.get("home_team") or lev.get("home"))
            away_obj  = _team(lev.get("away_team") or lev.get("away"))
            home_name = home_obj.get("name","?")
            away_name = away_obj.get("name","?")

            if eid and eid not in ws_mgr.subscribed:
                ws_mgr.subscribe(eid)

            snap    = ws_mgr.snapshots.get(eid, {})
            _sc     = snap.get("score", {}) or {}
            sh      = _sc.get("home", lev.get("home_score","–")) or "–"
            sa      = _sc.get("away", lev.get("away_score","–")) or "–"
            minute  = (snap.get("time") or {}).get("minute", _minute(lev))
            league  = _league(lev)
            tick    = snap.get("livedata") or {}
            sit     = tick.get("situation","")
            sit_sid = tick.get("side","")
            sit_icons = {"attack":"⚡","goal":"⚽","corner":"🚩","free_kick":"🎯",
                         "penalty":"🔴","substitution":"🔄","dangerous_attack":"💥"}
            sit_str = f"{sit_icons.get(sit,'🏃')} {sit.replace('_',' ').title()} · {'🏠' if sit_sid=='home' else ('✈️' if sit_sid=='away' else '')}" if sit else ""

            exp_label = f"🔴  {home_name}  {sh}–{sa}  {away_name}   {f'{minute}′' if minute else ''}"

            with st.expander(exp_label, expanded=True):
                stats_col, ai_col = st.columns([1, 1], gap="large")

                # ── Live stats ────────────────────────────────────
                with stats_col:
                    hdr = f'{league}  {f"· {sit_str}" if sit_str else ""}'
                    st.markdown(f'<div class="sec-hd">{hdr}</div>', unsafe_allow_html=True)

                    ws_stats = snap.get("stats", {})
                    if ws_stats:
                        hs  = ws_stats.get("home", {})
                        as_ = ws_stats.get("away", {})
                        poss_h = extract_stat(hs, "ball_possession")
                        poss_a = extract_stat(as_, "ball_possession")
                        st.markdown(f"""
                        <div style="display:flex;justify-content:space-between;margin:.4rem 0">
                          <span style="font-size:1.4rem;font-weight:800;color:#00d4aa">{int(poss_h)}%</span>
                          <span style="font-size:.65rem;color:#6b7280;align-self:center">ОВЛАДЯВАНЕ</span>
                          <span style="font-size:1.4rem;font-weight:800;color:#f59e0b">{int(poss_a)}%</span>
                        </div>""", unsafe_allow_html=True)
                        for lbl, key in [
                            ("Удари",          "total_shots"),
                            ("В рамка",        "shots_on_target"),
                            ("xG",             "xg"),
                            ("Ъглови",         "corner_kicks"),
                            ("Опасни атаки",   "dangerous_attack"),
                            ("Фаулове",        "fouls"),
                            ("Жълти картони",  "yellow_cards"),
                        ]:
                            hv = extract_stat(hs, key); av = extract_stat(as_, key)
                            if hv or av: render_stat_bar(lbl, hv, av)
                    else:
                        st.caption("⏳ Изчакване на WebSocket данни…")
                        render_event_stats_panel(eid, home_name, away_name)

                    ws_odds = snap.get("odds")
                    if ws_odds:
                        st.markdown(""); render_odds_row(ws_odds)

                # ── AI chat ───────────────────────────────────────
                with ai_col:
                    ws_stats_now = snap.get("stats", {})
                    hs  = ws_stats_now.get("home", {}) if ws_stats_now else {}
                    as_ = ws_stats_now.get("away", {}) if ws_stats_now else {}
                    ws_odds_now = snap.get("odds", {}) or {}
                    mw = (ws_odds_now.get("odds") or ws_odds_now).get("match_winner", {}) or {}

                    live_ctx = ""
                    if ws_stats_now:
                        live_ctx = (
                            f"\nWEBSOCKET СТАТИСТИКИ: "
                            f"{home_name} удари={extract_stat(hs,'total_shots')} "
                            f"xG={extract_stat(hs,'xg')} "
                            f"поз={extract_stat(hs,'ball_possession')}% "
                            f"оп.атаки={extract_stat(hs,'dangerous_attack')} | "
                            f"{away_name} удари={extract_stat(as_,'total_shots')} "
                            f"xG={extract_stat(as_,'xg')} "
                            f"поз={extract_stat(as_,'ball_possession')}% "
                            f"оп.атаки={extract_stat(as_,'dangerous_attack')}"
                        )
                    if mw:
                        live_ctx += f"\nЖИВИ КОЕФИЦИЕНТИ: 1={mw.get('home','?')} X={mw.get('draw','?')} 2={mw.get('away','?')}"
                    if sit_str:
                        live_ctx += f"\nСИТУАЦИЯ: {sit_str}"

                    st.markdown(f'<div class="sec-hd">🤖 AI — {home_name} vs {away_name}</div>',
                                unsafe_allow_html=True)
                    render_inline_ai(lev, f"ai_live_{eid}",
                                     home_name, away_name, live_ctx)

    if auto_ref:
        _time.sleep(15)
        st.rerun()
