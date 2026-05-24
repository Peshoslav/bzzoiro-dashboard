"""
⚽ AI Football Analytics — main app
Tabs: 1. Програма  2. На Живо
"""
import streamlit as st
st.set_page_config(page_title="AI Football Analytics", page_icon="⚽",
                   layout="wide", initial_sidebar_state="collapsed")

from datetime import date, timedelta, datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict

# ── Gemini ────────────────────────────────────────────────────────
try:
    from google import genai as _gai
    _gemini = _gai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except Exception:
    _gemini = None

# ── CSS ───────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
.stApp,[data-testid="stAppViewContainer"]{background:#0d1117!important;font-family:'Inter',sans-serif}
.block-container{padding:.75rem 1.5rem 2rem;max-width:1400px}
#MainMenu,footer,header{visibility:hidden}
.topbar{display:flex;align-items:center;justify-content:space-between;
  padding:.8rem 0;margin-bottom:1.2rem;border-bottom:1px solid #1e2737}
.logo{font-size:1.5rem;font-weight:900;color:#fff}.logo span{color:#00d4aa}
.stTabs [data-baseweb="tab-list"]{background:#161b27;border-radius:10px;
  padding:4px;gap:4px;border:1px solid #1e2737}
.stTabs [data-baseweb="tab"]{background:transparent;color:#6b7280;border-radius:7px;
  font-weight:600;font-size:.85rem;padding:.55rem 1.4rem}
.stTabs [aria-selected="true"]{background:#00d4aa!important;color:#0d1117!important}
.stTabs [data-baseweb="tab-panel"]{padding-top:1rem}
.sec-hd{font-size:.7rem;font-weight:700;color:#4b5563;text-transform:uppercase;
  letter-spacing:1.5px;padding-bottom:.5rem;margin:1rem 0 .6rem;border-bottom:1px solid #1e2737}
.mrow{display:flex;align-items:center;background:#161b27;border:1px solid #1e2737;
  border-radius:10px;padding:.7rem 1rem;margin-bottom:.35rem;gap:.5rem}
.mrow-lg{font-size:.65rem;color:#6b7280;font-weight:600;min-width:120px;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.mrow-teams{display:flex;align-items:center;gap:.5rem;flex:1;justify-content:center}
.tn{font-size:.9rem;font-weight:600;color:#e2e8f0;flex:1;text-align:right}
.tn.a{text-align:left}
.sb{background:#1e2737;border-radius:6px;padding:4px 14px;font-size:1rem;
  font-weight:800;color:#00d4aa;letter-spacing:2px;white-space:nowrap}
.sb.live{background:rgba(239,68,68,.12);color:#ef4444;border:1px solid rgba(239,68,68,.25)}
.sb.up{color:#4b5563;font-size:.82rem;padding:4px 10px}
.mrow-time{font-size:.72rem;color:#6b7280;min-width:42px;text-align:right}
.min-tag{font-size:.68rem;color:#ef4444;font-weight:700;
  background:rgba(239,68,68,.1);border-radius:4px;padding:2px 5px}
.stat-wrap{margin:.35rem 0}
.stat-meta{display:flex;justify-content:space-between;margin-bottom:2px}
.sn{font-size:.7rem;color:#6b7280}.sv{font-size:.7rem;color:#e2e8f0;font-weight:700}
.bar-track{width:100%;height:5px;background:#1e2737;border-radius:3px;overflow:hidden;display:flex}
.bar-h{height:100%;border-radius:3px 0 0 3px;background:linear-gradient(90deg,#00d4aa,#0ea5e9)}
.bar-a{height:100%;border-radius:0 3px 3px 0;background:linear-gradient(90deg,#f59e0b,#ef4444)}
.form-row{display:flex;gap:4px;flex-wrap:wrap;margin:.3rem 0}
.fb{width:24px;height:24px;border-radius:4px;font-size:.6rem;font-weight:800;
  display:inline-flex;align-items:center;justify-content:center}
.fw{background:rgba(34,197,94,.2);color:#22c55e}
.fd{background:rgba(234,179,8,.2);color:#eab308}
.fl{background:rgba(239,68,68,.2);color:#ef4444}
.tile{background:#161b27;border:1px solid #1e2737;border-radius:10px;
  padding:.8rem;text-align:center}
.tile-val{font-size:1.6rem;font-weight:800;color:#00d4aa}
.tile-lbl{font-size:.65rem;color:#6b7280;text-transform:uppercase;letter-spacing:.5px}
.oc{background:#161b27;border:1px solid #1e2737;border-radius:8px;
  padding:.6rem .8rem;text-align:center}
.ol{font-size:.65rem;color:#6b7280;margin-bottom:3px}
.ov{font-size:1rem;font-weight:700;color:#f59e0b}
.ai-a{background:#111827;border:1px solid #00d4aa;border-radius:8px;
  padding:.7rem 1rem;margin:.35rem 0;font-size:.85rem;color:#e2e8f0;line-height:1.7;
  white-space:pre-wrap}
.ai-u{background:#1a2035;border:1px solid #1e2737;border-radius:8px;
  padding:.6rem 1rem;margin:.35rem 0;font-size:.85rem;color:#9ca3af}
.ai-role{font-size:.65rem;color:#4b5563;margin-bottom:3px}
.tool-badge{display:inline-block;background:rgba(0,212,170,.1);
  border:1px solid rgba(0,212,170,.3);border-radius:4px;
  padding:2px 8px;font-size:.65rem;color:#00d4aa;margin:.2rem 0}
[data-testid="stExpander"]{background:#161b27!important;
  border:1px solid #1e2737!important;border-radius:10px!important;margin-bottom:.4rem!important}
[data-testid="stExpander"]:hover{border-color:#00d4aa!important}
div[data-testid="stSelectbox"]>div,div[data-testid="stDateInput"]>div{
  background:#161b27!important;border-color:#1e2737!important;color:#e2e8f0!important}
.stTextInput input{background:#161b27!important;border-color:#1e2737!important;
  color:#e2e8f0!important;border-radius:8px!important}
.stButton>button{background:#00d4aa;color:#0d1117;font-weight:700;
  border:none;border-radius:8px;padding:.45rem 1rem}
.stButton>button:hover{background:#00b896}
label{color:#9ca3af!important;font-size:.8rem!important}
::-webkit-scrollbar{width:5px}::-webkit-scrollbar-track{background:#0d1117}
::-webkit-scrollbar-thumb{background:#1e2737;border-radius:3px}
</style>
""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════
# PURE HELPERS
# ═════════════════════════════════════════════════════════════════
def bg_time(utc_str: str) -> str:
    if not utc_str: return ""
    s = utc_str.strip().rstrip("Zz")
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M",    "%Y-%m-%d %H:%M"):
        try:
            dt = datetime.strptime(s[:16], fmt[:16])
            return (dt + timedelta(hours=3)).strftime("%H:%M")
        except ValueError: continue
    return s[11:16] if len(s) >= 16 else ""

def _team(val: Any) -> Dict:
    if isinstance(val, dict): return val
    if isinstance(val, str):  return {"id": None, "name": val}
    return {"id": None, "name": "?"}

def _league(m: Dict) -> str:
    for k in ("league","tournament","competition"):
        v = m.get(k)
        if isinstance(v, dict) and v.get("name"): return v["name"]
        if isinstance(v, str)  and v:             return v
    return ""

def _score(m: Dict):
    s = m.get("score")
    if isinstance(s, dict): return str(s.get("home","")), str(s.get("away",""))
    h = m.get("home_score",""); a = m.get("away_score","")
    return (str(h) if h is not None else ""), (str(a) if a is not None else "")

def _status(m: Dict) -> str:
    v = m.get("status", m.get("event_status",""))
    if isinstance(v, dict): v = v.get("type","")
    return str(v).lower()

def _kickoff(m: Dict) -> str:
    for k in ("start_at","kickoff_at","event_date","scheduled"):
        v = m.get(k)
        if v: return bg_time(str(v))
    return ""

def _minute(m: Dict) -> str:
    return str(m.get("minute","") or (m.get("time") or {}).get("minute","") or "")

def _sort_key(m: Dict):
    """Upcoming first (0), live second (1), finished last (2)."""
    s = _status(m)
    if s in ("notstarted","scheduled","tbd","upcoming",""):     order = 0
    elif s in ("inprogress","live","1h","2h","ht","et","pen"): order = 1
    else:                                                       order = 2
    ko = ""
    for k in ("start_at","kickoff_at","event_date","scheduled"):
        v = m.get(k)
        if v: ko = str(v); break
    return (order, ko)

def extract_stat(d: Dict, key: str) -> float:
    v = d.get(key, 0)
    if isinstance(v, dict): return float(v.get("value",0) or 0)
    return float(v or 0)


# ═════════════════════════════════════════════════════════════════
# RENDER HELPERS
# ═════════════════════════════════════════════════════════════════
def render_match_row(m: Dict, live: bool = False):
    hn = _team(m.get("home_team") or m.get("home")).get("name","?")
    an = _team(m.get("away_team") or m.get("away")).get("name","?")
    sh, sa = _score(m); ko = _kickoff(m); min_ = _minute(m)
    lg = _league(m)
    if live and min_:
        sc = f'<span class="sb live">{sh}–{sa}</span>'
        ti = f'<span class="min-tag">{min_}′</span>'
    elif sh and sa:
        sc = f'<span class="sb">{sh}–{sa}</span>'
        ti = f'<span class="mrow-time">{ko}</span>'
    else:
        sc = f'<span class="sb up">{ko or "–"}</span>'
        ti = ""
    st.markdown(f"""<div class="mrow">
      <span class="mrow-lg" title="{lg}">{lg}</span>
      <div class="mrow-teams">
        <span class="tn">{hn}</span>{sc}<span class="tn a">{an}</span>
      </div>{ti}</div>""", unsafe_allow_html=True)

def render_stat_bar(label: str, hv, av):
    try:
        h, a = float(hv or 0), float(av or 0)
        total = h + a; ph = round(h/total*100) if total else 50
    except: h, a, ph = 0, 0, 50
    st.markdown(f"""<div class="stat-wrap">
      <div class="stat-meta"><span class="sn">{label}</span>
        <span class="sv">{int(h)} — {int(a)}</span></div>
      <div class="bar-track">
        <div class="bar-h" style="width:{ph}%"></div>
        <div class="bar-a" style="width:{100-ph}%"></div>
      </div></div>""", unsafe_allow_html=True)

def render_event_stats_panel(event_id, home_name: str, away_name: str):
    from api import get_event_stats
    if not event_id: st.caption("Няма event_id."); return
    data = get_event_stats(event_id)
    if not data: st.caption("Статистиките не са налични."); return
    hs  = data.get("home") or (data.get("stats") or {}).get("home") or {}
    as_ = data.get("away") or (data.get("stats") or {}).get("away") or {}
    shown = False
    for lbl, key in [("Овладяване (%)","ball_possession"),("Общо удари","total_shots"),
                     ("В рамка","shots_on_target"),("xG","xg"),("Ъглови","corner_kicks"),
                     ("Опасни атаки","dangerous_attack"),("Атаки","attack"),
                     ("Фаулове","fouls"),("Жълти картони","yellow_cards"),
                     ("Червени картони","red_cards"),("Спасявания","goalkeeper_saves"),
                     ("Офсайди","offsides"),("Предавания","passes")]:
        hv = extract_stat(hs, key); av = extract_stat(as_, key)
        if hv or av: render_stat_bar(lbl, hv, av); shown = True
    if not shown: st.caption("Статистиките не са налични.")

def render_form_badges(fixtures: List[Dict], team_id=None, team_name=None) -> str:
    badges = []
    for m in fixtures[:5]:
        sh, sa = _score(m)
        try: sh, sa = int(sh), int(sa)
        except: continue
        home_v = _team(m.get("home_team") or m.get("home"))
        htid   = home_v.get("id"); htn = home_v.get("name","")
        is_home = (htid == team_id if team_id else
                   (team_name.lower() in htn.lower() if team_name else True))
        if sh == sa:                                         badges.append('<span class="fb fd">D</span>')
        elif (is_home and sh > sa) or (not is_home and sa > sh):
                                                             badges.append('<span class="fb fw">W</span>')
        else:                                                badges.append('<span class="fb fl">L</span>')
    return f'<div class="form-row">{"".join(badges)}</div>' if badges else ""

def render_odds_row(odds: Dict):
    mw   = (odds.get("odds") or odds).get("match_winner") or {}
    ou   = (odds.get("odds") or odds).get("over_under")   or {}
    btts = (odds.get("odds") or odds).get("btts")         or {}
    pairs = [("1",mw.get("home")),("X",mw.get("draw")),("2",mw.get("away")),
             ("O2.5",ou.get("over_25")),("U2.5",ou.get("under_25")),
             ("GG",btts.get("yes")),("NG",btts.get("no"))]
    valid = [(l,v) for l,v in pairs if v]
    if not valid: return
    cols = st.columns(len(valid))
    for col,(lbl,val) in zip(cols,valid):
        with col:
            st.markdown(f'<div class="oc"><div class="ol">{lbl}</div>'
                        f'<div class="ov">{float(val):.2f}</div></div>',
                        unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════
# AI CHAT — Gemini with Tool Calling
# ═════════════════════════════════════════════════════════════════
def render_inline_ai(match_obj: Dict, chat_key: str,
                     home_name: str, away_name: str,
                     event_id=None, extra_ctx: str = ""):
    if not _gemini:
        st.caption("GEMINI_API_KEY не е настроен.")
        return

    if chat_key not in st.session_state:
        st.session_state[chat_key] = []
    hist = st.session_state[chat_key]

    # ── Show history ──────────────────────────────────────────────
    for msg in hist:
        if msg["role"] == "tool_call":
            st.markdown(f'<div class="tool-badge">🔧 {msg["content"]}</div>',
                        unsafe_allow_html=True)
            continue
        cls  = "ai-a" if msg["role"] == "assistant" else "ai-u"
        icon = "🤖 AI" if msg["role"] == "assistant" else "👤 Ти"
        st.markdown(f'<div class="{cls}"><div class="ai-role">{icon}</div>'
                    f'{msg["content"]}</div>', unsafe_allow_html=True)

    # ── Quick buttons ─────────────────────────────────────────────
    q1, q2, q3, q4 = st.columns(4)
    for col, lbl in [(q1,"📊 Обобщи"),(q2,"⚽ Ще има ли гол?"),
                     (q3,"💰 Стойностен залог?"),(q4,"👥 Стартов 11?")]:
        if col.button(lbl, key=f"{chat_key}_q{lbl}"):
            st.session_state[f"{chat_key}_pend"] = lbl

    user_q = st.text_input("Въпрос…", key=f"{chat_key}_inp",
                            placeholder="Питай AI — може да търси линкъп, прогнози, класиране…",
                            label_visibility="collapsed")
    c1, c2 = st.columns([4,1])
    send = c1.button("Изпрати ↗", key=f"{chat_key}_send")
    if c2.button("Изчисти", key=f"{chat_key}_clr"):
        st.session_state[chat_key] = []
        st.rerun()

    question = None
    if send and user_q.strip(): question = user_q.strip()
    elif f"{chat_key}_pend" in st.session_state:
        question = st.session_state.pop(f"{chat_key}_pend")

    if question:
        sh, sa = _score(match_obj); ko = _kickoff(match_obj); min_ = _minute(match_obj)
        sys_prompt = (
            f"Ти си експертен футболен анализатор. Говори САМО на БЪЛГАРСКИ. "
            f"Бъди конкретен и структуриран.\n\n"
            f"ТЕКУЩ МАЧ: {home_name} срещу {away_name} (event_id={event_id})\n"
            f"СТАТУС: {_status(match_obj)}  РЕЗУЛТАТ: {sh}–{sa}  "
            f"{f'Минута: {min_}' if min_ else f'Начало (BG): {ko}'}\n"
            f"{extra_ctx}\n\n"
            f"Имаш достъп до инструменти за търсене на реални данни от API-то "
            f"(прогнози, коефициенти, линкъп, инциденти, статистики на играчи, "
            f"форма на отбор, класиране, H2H). "
            f"Ако не знаеш нещо — потърси с инструмент. "
            f"Когато цитираш данни от инструмент, спомени откъде идват."
        )
        # Filter history — keep only user/assistant, not tool_call badges
        clean_hist = [m for m in hist if m["role"] in ("user","assistant")]

        with st.spinner("🤖 AI анализира…"):
            from gemini_tools import run_gemini_with_tools
            answer = run_gemini_with_tools(
                _gemini, sys_prompt, question, history=clean_hist
            )

        st.session_state[chat_key].append({"role":"user",      "content": question})
        st.session_state[chat_key].append({"role":"assistant", "content": answer})
        st.rerun()


# ═════════════════════════════════════════════════════════════════
# MATCH DETAIL — called only after "Зареди" button
# ═════════════════════════════════════════════════════════════════
def render_match_detail(m: Dict, eid, home_name: str, away_name: str,
                        home_id, away_id, is_finished: bool):
    from api import (get_event_stats, get_event_odds, get_prediction,
                     get_team_fixtures, get_h2h)

    # Per-match slider for number of recent fixtures
    n_last = st.slider("Последни мачове за форма", 3, 15, 5,
                       key=f"nlast_{eid}")

    # Quick AI context string (no blocking calls — reuse cached data)
    ctx = (f"home_id={home_id} away_id={away_id} event_id={eid} "
           f"home={home_name} away={away_name}")

    if is_finished:
        tabs = st.tabs(["📊 Статистики", f"🏠 {home_name[:14]}",
                        f"✈️ {away_name[:14]}", "⚔️ H2H",
                        "💰 Коефициенти", "🤖 AI"])
        off = 1
        with tabs[0]: render_event_stats_panel(eid, home_name, away_name)
    else:
        tabs = st.tabs([f"🏠 {home_name[:14]}", f"✈️ {away_name[:14]}",
                        "⚔️ H2H", "💰 Прогноза & Коефициенти", "🤖 AI"])
        off = 0

    # ── Team form tabs ─────────────────────────────────────────────
    for i, (tid, tname) in enumerate([(home_id, home_name),(away_id, away_name)]):
        with tabs[off + i]:
            with st.spinner(f"Зареждане на мачове за {tname}…"):
                fixes = get_team_fixtures(team_id=tid, team_name=tname,
                                          last_n=n_last)
            if not fixes:
                st.info("Няма намерени минали мачове.")
                continue
            st.markdown(render_form_badges(fixes, team_id=tid, team_name=tname),
                        unsafe_allow_html=True)
            for fm in fixes:
                fid = fm.get("id")
                fh  = _team(fm.get("home_team") or fm.get("home")).get("name","?")
                fa  = _team(fm.get("away_team") or fm.get("away")).get("name","?")
                fsh, fsa = _score(fm)
                render_match_row(fm)
                if fid:
                    with st.expander(
                        f"📊 {fh} {fsh}–{fsa} {fa}  {_kickoff(fm)}",
                        expanded=False):
                        render_event_stats_panel(fid, fh, fa)

    # ── H2H ───────────────────────────────────────────────────────
    with tabs[off + 2]:
        with st.spinner("Зареждане на H2H…"):
            h2h_list = get_h2h(home_id, away_id,
                                home_name=home_name, away_name=away_name,
                                last_n=10)
        if not h2h_list:
            st.info("Няма намерени H2H мачове.")
        else:
            hw = dw = aw = 0
            for hm in h2h_list:
                hmsh, hmsa = _score(hm)
                try: hmsh, hmsa = int(hmsh), int(hmsa)
                except: continue
                htid = _team(hm.get("home_team") or hm.get("home")).get("id")
                htn  = _team(hm.get("home_team") or hm.get("home")).get("name","")
                is_h = (htid == home_id if home_id else
                        home_name.lower() in htn.lower())
                if hmsh == hmsa:                              dw += 1
                elif (is_h and hmsh > hmsa) or (not is_h and hmsa > hmsh): hw += 1
                else:                                         aw += 1
            c1,c2,c3 = st.columns(3)
            for col,val,lbl in [(c1,hw,home_name[:12]),(c2,dw,"Равни"),(c3,aw,away_name[:12])]:
                col.markdown(f'<div class="tile"><div class="tile-val">{val}</div>'
                             f'<div class="tile-lbl">{lbl}</div></div>',
                             unsafe_allow_html=True)
            st.markdown("")
            for hm in h2h_list: render_match_row(hm)

    # ── Odds / prediction ──────────────────────────────────────────
    with tabs[off + 3]:
        if eid:
            odds = get_event_odds(eid)
            if odds: render_odds_row(odds)
            if not is_finished:
                pred = get_prediction(eid)
                if pred:
                    st.markdown("**ML Прогноза**")
                    pc1,pc2,pc3 = st.columns(3)
                    ph  = pred.get("home_win_pct")  or pred.get("home_probability")
                    pd_ = pred.get("draw_pct")       or pred.get("draw_probability")
                    pa  = pred.get("away_win_pct")  or pred.get("away_probability")
                    if ph:  pc1.metric("1", f"{float(ph):.0f}%")
                    if pd_: pc2.metric("X", f"{float(pd_):.0f}%")
                    if pa:  pc3.metric("2", f"{float(pa):.0f}%")
            if not odds: st.caption("Няма налични коефициенти.")

    # ── AI ────────────────────────────────────────────────────────
    with tabs[off + 4]:
        tag = "fin" if is_finished else "up"
        render_inline_ai(m, f"ai_{tag}_{eid}", home_name, away_name,
                         event_id=eid, extra_ctx=ctx)


# ═════════════════════════════════════════════════════════════════
# STARTUP — WebSocket
# ═════════════════════════════════════════════════════════════════
from ws_manager import get_ws_manager
ws_mgr = get_ws_manager()
try:
    ws_mgr.start(st.secrets["BZZOIRO_API_KEY"])
except Exception:
    pass

st.markdown(f"""<div class="topbar">
  <div class="logo">⚽ AI Football <span>Analytics</span></div>
  <div style="font-size:.8rem;color:#6b7280">{ws_mgr.status} &nbsp;|&nbsp; 🕐 BG (UTC+3)</div>
</div>""", unsafe_allow_html=True)

tab_schedule, tab_live = st.tabs(["📅 Програма", "🔴 На Живо"])


# ═════════════════════════════════════════════════════════════════
# TAB 1 — ПРОГРАМА
# ═════════════════════════════════════════════════════════════════
with tab_schedule:
    from api import get_leagues, get_events

    fc1, fc2 = st.columns([1.5, 2])
    with fc1: sel_date = st.date_input("Дата", value=date.today())
    with fc2:
        leagues_list = get_leagues()
        lnames = ["Всички"] + [l.get("name","") for l in leagues_list if l.get("name")]
        sel_lg = st.selectbox("Лига", lnames)

    date_str  = sel_date.isoformat()
    league_id = None
    if sel_lg != "Всички":
        lobj = next((l for l in leagues_list if l.get("name") == sel_lg), None)
        if lobj: league_id = lobj.get("id")

    with st.spinner("Зареждане на програмата…"):
        events = get_events(date_from=date_str, date_to=date_str,
                            league_id=league_id, limit=100)

    if not events:
        st.info("Няма намерени мачове за тази дата.")
    else:
        # Sort: upcoming first, live second, finished last
        events_sorted = sorted(events, key=_sort_key)

        by_league: Dict[str, List] = defaultdict(list)
        for m in events_sorted:
            by_league[_league(m) or "Без лига"].append(m)

        # Sort leagues so those with upcoming matches appear first
        def _league_sort(lg_items):
            lg_name, matches = lg_items
            return min(_sort_key(m)[0] for m in matches)
        sorted_leagues = sorted(by_league.items(), key=_league_sort)

        for lg_name, matches in sorted_leagues:
            st.markdown(f'<div class="sec-hd">{lg_name}</div>', unsafe_allow_html=True)

            for m in matches:
                eid       = m.get("id")
                home_obj  = _team(m.get("home_team") or m.get("home"))
                away_obj  = _team(m.get("away_team") or m.get("away"))
                home_name = home_obj.get("name","?")
                away_name = away_obj.get("name","?")
                sh, sa    = _score(m)
                ko        = _kickoff(m)
                status    = _status(m)
                minute    = _minute(m)

                is_live     = status in ("inprogress","live","1h","2h","ht","et","pen","in_progress","playing","1st_half","2nd_half","halftime","extra_time","penalties","paused")
                is_finished = status in ("finished","ft","aet","pen_finished","ended","complete")

                if is_live:
                    exp_label = f"🔴  {home_name}  {sh}–{sa}  {away_name}  ·  {minute}′"
                elif is_finished:
                    exp_label = f"✅  {home_name}  {sh}–{sa}  {away_name}  ·  {ko}"
                else:
                    exp_label = f"🕐  {home_name}  vs  {away_name}  ·  {ko or '?'} BG"

                with st.expander(exp_label, expanded=False):
                    load_key = f"ld_{eid}_{date_str}"

                    if not st.session_state.get(load_key):
                        st.caption("Кликни за да заредиш форма, H2H и статистики.")
                        if st.button("📊 Зареди детайли", key=f"load_{eid}_{date_str}",
                                     use_container_width=True):
                            st.session_state[load_key] = {
                                "home_id": home_obj.get("id"),
                                "away_id": away_obj.get("id"),
                            }
                            st.rerun()
                    else:
                        ids     = st.session_state[load_key]
                        home_id = ids.get("home_id")
                        away_id = ids.get("away_id")
                        render_match_detail(
                            m, eid, home_name, away_name,
                            home_id, away_id, is_finished
                        )


# ═════════════════════════════════════════════════════════════════
# TAB 2 — НА ЖИВО
# ═════════════════════════════════════════════════════════════════
with tab_live:
    import time as _time
    from api import get_live_events, get_event_stats, get_event_odds

    ws_mgr.drain()

    cc1, cc2 = st.columns([4, 1])
    with cc1: st.markdown('<div class="sec-hd">Мачове на живо</div>', unsafe_allow_html=True)
    with cc2: auto_ref = st.toggle("🔄 15 сек", value=False)
    st.caption(ws_mgr.status)

    live_events = get_live_events()

    if not live_events:
        st.info("⏳ Няма мачове на живо в момента.")
    else:
        for lev in live_events:
            eid       = lev.get("id")
            home_obj  = _team(lev.get("home_team") or lev.get("home"))
            away_obj  = _team(lev.get("away_team") or lev.get("away"))
            home_name = home_obj.get("name","?")
            away_name = away_obj.get("name","?")

            if eid and eid not in ws_mgr.subscribed:
                ws_mgr.subscribe(eid)

            snap    = ws_mgr.snapshots.get(eid, {})
            _sc     = snap.get("score") or {}
            sh      = str(_sc.get("home", lev.get("home_score","–")) or "–")
            sa      = str(_sc.get("away", lev.get("away_score","–")) or "–")
            minute  = (snap.get("time") or {}).get("minute", _minute(lev))
            tick    = snap.get("livedata") or {}
            sit     = tick.get("situation","")
            sit_sid = tick.get("side","")
            sit_icons = {"attack":"⚡","goal":"⚽","corner":"🚩",
                         "free_kick":"🎯","penalty":"🔴","substitution":"🔄",
                         "dangerous_attack":"💥","ball_safe":"🛡️"}
            sit_str = (f"{sit_icons.get(sit,'🏃')} {sit.replace('_',' ').title()} "
                       f"· {'🏠' if sit_sid=='home' else '✈️' if sit_sid=='away' else ''}"
                       ) if sit else ""

            exp_label = f"🔴  {home_name}  {sh}–{sa}  {away_name}  {f'· {minute}′' if minute else ''}"

            with st.expander(exp_label, expanded=True):
                sc, ai = st.columns([1,1], gap="large")

                with sc:
                    lg = _league(lev)
                    hdr = f"{lg}{'  ·  ' + sit_str if sit_str else ''}"
                    st.markdown(f'<div class="sec-hd">{hdr}</div>', unsafe_allow_html=True)

                    ws_stats = snap.get("stats",{})
                    if ws_stats:
                        hs  = ws_stats.get("home",{})
                        as_ = ws_stats.get("away",{})
                        ph  = int(extract_stat(hs,"ball_possession"))
                        pa  = int(extract_stat(as_,"ball_possession"))
                        st.markdown(
                            f'<div style="display:flex;justify-content:space-between;margin:.4rem 0">'
                            f'<span style="font-size:1.4rem;font-weight:800;color:#00d4aa">{ph}%</span>'
                            f'<span style="font-size:.65rem;color:#6b7280;align-self:center">ОВЛАДЯВАНЕ</span>'
                            f'<span style="font-size:1.4rem;font-weight:800;color:#f59e0b">{pa}%</span>'
                            f'</div>', unsafe_allow_html=True)
                        for lbl, key in [
                            ("Удари","total_shots"),("В рамка","shots_on_target"),
                            ("xG","xg"),("Ъглови","corner_kicks"),
                            ("Опасни атаки","dangerous_attack"),
                            ("Фаулове","fouls"),("Жълти картони","yellow_cards")]:
                            hv = extract_stat(hs,key); av = extract_stat(as_,key)
                            if hv or av: render_stat_bar(lbl, hv, av)
                    else:
                        st.caption("⏳ Изчакване на WebSocket данни…")
                        render_event_stats_panel(eid, home_name, away_name)

                    ws_odds = snap.get("odds")
                    if ws_odds: st.markdown(""); render_odds_row(ws_odds)

                with ai:
                    ws_stats_now = snap.get("stats",{})
                    hs2  = ws_stats_now.get("home",{}) if ws_stats_now else {}
                    as_2 = ws_stats_now.get("away",{}) if ws_stats_now else {}
                    live_ctx = ""
                    if ws_stats_now:
                        live_ctx = (
                            f"\nLIVE WS: {home_name} "
                            f"удари={extract_stat(hs2,'total_shots')} "
                            f"xG={extract_stat(hs2,'xg')} "
                            f"поз={extract_stat(hs2,'ball_possession')}% | "
                            f"{away_name} "
                            f"удари={extract_stat(as_2,'total_shots')} "
                            f"xG={extract_stat(as_2,'xg')} "
                            f"поз={extract_stat(as_2,'ball_possession')}%"
                        )
                    if sit_str: live_ctx += f"\nСИТУАЦИЯ: {sit_str}"
                    mw = ((snap.get("odds") or {}).get("odds") or {}).get("match_winner",{}) or {}
                    if mw: live_ctx += f"\nЖИВИ КОЕФИЦИЕНТИ: 1={mw.get('home','?')} X={mw.get('draw','?')} 2={mw.get('away','?')}"

                    st.markdown(f'<div class="sec-hd">🤖 AI — {home_name} vs {away_name}</div>',
                                unsafe_allow_html=True)
                    render_inline_ai(lev, f"ai_live_{eid}", home_name, away_name,
                                     event_id=eid, extra_ctx=live_ctx)

    if auto_ref:
        _time.sleep(15)
        st.rerun()
