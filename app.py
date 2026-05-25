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


def render_prediction_panel(home_name: str, away_name: str,
                             home_id, away_id,
                             home_fixtures: List[Dict],
                             away_fixtures: List[Dict],
                             h2h_matches:  List[Dict]):
    """
    Full Dixon-Coles prediction panel.
    Designed to replace / supplement the empty API prediction section.
    """
    from predictor import predict_match

    if len(home_fixtures) < 1 and len(away_fixtures) < 1:
        st.info("Няма достатъчно форм данни за прогноза.")
        return

    with st.spinner("Изчисляване на прогноза…"):
        p = predict_match(
            home_name, away_name,
            home_fixtures, away_fixtures,
            h2h_matches,
        )

    if p["warning"]:
        st.warning(p["warning"])

    # ── Confidence bar ────────────────────────────────────────────
    conf       = p["confidence"]
    conf_color = "#22c55e" if conf >= 70 else "#f59e0b" if conf >= 40 else "#ef4444"
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:.6rem;margin-bottom:.8rem">
      <span style="font-size:.7rem;color:#6b7280;min-width:80px">Надеждност</span>
      <div style="flex:1;background:#1e2737;border-radius:4px;height:7px">
        <div style="width:{conf}%;background:{conf_color};
                    border-radius:4px;height:100%"></div>
      </div>
      <span style="font-size:.75rem;font-weight:700;color:{conf_color}">{conf}%</span>
    </div>
    <div style="font-size:.65rem;color:#4b5563;margin-bottom:1rem">
      Базирано на {p['home_matches_used']} мача ({home_name}) и
      {p['away_matches_used']} мача ({away_name})
      {f"+ {len(h2h_matches)} H2H" if h2h_matches else ""}
    </div>""", unsafe_allow_html=True)

    # ── Win probability big display ───────────────────────────────
    hw = int(p["home_win"] * 100)
    dw = int(p["draw"]     * 100)
    aw = 100 - hw - dw

    st.markdown(f"""
    <div style="display:flex;gap:3px;border-radius:10px;overflow:hidden;
                margin-bottom:.5rem;height:44px">
      <div style="flex:{hw};background:linear-gradient(135deg,#00d4aa,#0ea5e9);
                  display:flex;align-items:center;justify-content:center">
        <span style="font-size:.95rem;font-weight:800;color:#0d1117">{hw}%</span>
      </div>
      <div style="flex:{dw};background:#2d3748;
                  display:flex;align-items:center;justify-content:center;min-width:32px">
        <span style="font-size:.85rem;font-weight:700;color:#e2e8f0">{dw}%</span>
      </div>
      <div style="flex:{aw};background:linear-gradient(135deg,#f59e0b,#ef4444);
                  display:flex;align-items:center;justify-content:center">
        <span style="font-size:.95rem;font-weight:800;color:#0d1117">{aw}%</span>
      </div>
    </div>
    <div style="display:flex;justify-content:space-between;
                font-size:.7rem;color:#6b7280;margin-bottom:1rem">
      <span>🏠 {home_name}</span><span>Равен</span><span>✈️ {away_name}</span>
    </div>""", unsafe_allow_html=True)

    # ── xG & market tiles ─────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    tiles = [
        (c1, f"{p['home_xg']:.2f}", f"xG {home_name[:10]}"),
        (c2, f"{p['away_xg']:.2f}", f"xG {away_name[:10]}"),
        (c3, f"{int(p['btts']*100)}%", "BTTS"),
        (c4, f"{int(p['over25']*100)}%", "Над 2.5 гола"),
    ]
    for col, val, lbl in tiles:
        col.markdown(f'<div class="tile"><div class="tile-val">{val}</div>'
                     f'<div class="tile-lbl">{lbl}</div></div>',
                     unsafe_allow_html=True)

    # ── Over/Under breakdown ──────────────────────────────────────
    st.markdown("")
    st.markdown('<div class="sec-hd">Брой голове</div>', unsafe_allow_html=True)
    ou_cols = st.columns(6)
    ou_data = [
        ("O0.5", p["over05"]),  ("O1.5", p["over15"]),
        ("O2.5", p["over25"]),  ("O3.5", p["over35"]),
        ("U2.5", p["under25"]), ("BTTS", p["btts"]),
    ]
    for col, (lbl, prob) in zip(ou_cols, ou_data):
        pct = int(prob * 100)
        color = "#22c55e" if pct >= 65 else "#f59e0b" if pct >= 45 else "#6b7280"
        col.markdown(
            f'<div class="oc"><div class="ol">{lbl}</div>'
            f'<div class="ov" style="color:{color}">{pct}%</div></div>',
            unsafe_allow_html=True)

    # ── Top scorelines ────────────────────────────────────────────
    st.markdown("")
    st.markdown('<div class="sec-hd">Най-вероятни резултати</div>',
                unsafe_allow_html=True)

    top = p["top_scorelines"][:8]
    max_prob = top[0]["prob"] if top else 0.01

    for sc in top:
        pct   = int(sc["prob"] * 100)
        bar_w = int(sc["prob"] / max_prob * 100)
        if sc["h"] > sc["a"]:   winner = "🏠"; wcolor = "#00d4aa"
        elif sc["h"] < sc["a"]: winner = "✈️"; wcolor = "#f59e0b"
        else:                   winner = "⚖️"; wcolor = "#9ca3af"
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:.5rem;margin:.2rem 0">
          <span style="min-width:40px;font-size:.9rem;font-weight:800;
                       color:#e2e8f0;text-align:center">{sc['h']}–{sc['a']}</span>
          <span style="font-size:.8rem">{winner}</span>
          <div style="flex:1;background:#1e2737;border-radius:3px;height:6px">
            <div style="width:{bar_w}%;background:{wcolor};
                        border-radius:3px;height:100%;opacity:.8"></div>
          </div>
          <span style="min-width:32px;font-size:.75rem;font-weight:700;
                       color:{wcolor};text-align:right">{pct}%</span>
        </div>""", unsafe_allow_html=True)

    st.caption(f"Среден брой голове в извадката: "
               f"{p['league_avg_goals']:.1f} на мач  ·  "
               f"Dixon-Coles модел с time-decay и H2H тегла")


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


def render_shotmap(shots: list, home_name: str, away_name: str):
    """SVG football pitch with shots plotted by xG."""
    import html as _html

    home_shots = [s for s in shots if s.get("is_home") or s.get("team","").lower() in home_name.lower()]
    away_shots = [s for s in shots if not (s.get("is_home") or s.get("team","").lower() in home_name.lower())]

    def _dot(s, flip=False):
        x = float(s.get("player_coordinates_x") or s.get("x") or 50)
        y = float(s.get("player_coordinates_y") or s.get("y") or 50)
        if flip: x, y = 100-x, 100-y
        xg  = float(s.get("xg") or s.get("expected_goals") or 0)
        r   = max(5, min(18, int(xg * 40)))
        goal = str(s.get("shot_type","") or s.get("outcome","")).lower() in ("goal","scored")
        color = "#22c55e" if goal else ("#00d4aa" if not flip else "#f59e0b")
        stroke = "#fff" if goal else "none"
        sw = 2 if goal else 0
        tip = f"{s.get('player_name','?')} xG:{xg:.2f}"
        # Scale to SVG 700×460 pitch (attacking = right side)
        sx = int(x / 100 * 700)
        sy = int(y / 100 * 460)
        return (f'<circle cx="{sx}" cy="{sy}" r="{r}" '
                f'fill="{color}" fill-opacity="0.75" '
                f'stroke="{stroke}" stroke-width="{sw}">'
                f'<title>{_html.escape(tip)}</title></circle>')

    home_dots = "".join(_dot(s) for s in home_shots)
    away_dots = "".join(_dot(s, flip=True) for s in away_shots)

    home_xg = sum(float(s.get("xg") or s.get("expected_goals") or 0) for s in home_shots)
    away_xg = sum(float(s.get("xg") or s.get("expected_goals") or 0) for s in away_shots)

    svg = f"""
    <svg viewBox="0 0 700 460" xmlns="http://www.w3.org/2000/svg"
         style="width:100%;max-width:700px;background:#1a2a1a;border-radius:10px;display:block;margin:0 auto">
      <!-- pitch outline -->
      <rect x="20" y="20" width="660" height="420" fill="none" stroke="#2d5a27" stroke-width="2"/>
      <!-- halfway line -->
      <line x1="350" y1="20" x2="350" y2="440" stroke="#2d5a27" stroke-width="1.5"/>
      <!-- centre circle -->
      <circle cx="350" cy="230" r="60" fill="none" stroke="#2d5a27" stroke-width="1.5"/>
      <circle cx="350" cy="230" r="3" fill="#2d5a27"/>
      <!-- left penalty area -->
      <rect x="20" y="130" width="132" height="200" fill="none" stroke="#2d5a27" stroke-width="1.5"/>
      <!-- left 6-yard box -->
      <rect x="20" y="185" width="44" height="90" fill="none" stroke="#2d5a27" stroke-width="1.5"/>
      <!-- left goal -->
      <rect x="8" y="200" width="12" height="60" fill="#1e3a1e" stroke="#2d5a27" stroke-width="1.5"/>
      <!-- right penalty area -->
      <rect x="548" y="130" width="132" height="200" fill="none" stroke="#2d5a27" stroke-width="1.5"/>
      <!-- right 6-yard box -->
      <rect x="636" y="185" width="44" height="90" fill="none" stroke="#2d5a27" stroke-width="1.5"/>
      <!-- right goal -->
      <rect x="680" y="200" width="12" height="60" fill="#1e3a1e" stroke="#2d5a27" stroke-width="1.5"/>
      <!-- shots -->
      {home_dots}{away_dots}
      <!-- legend -->
      <circle cx="40" cy="453" r="6" fill="#22c55e" fill-opacity=".8"/>
      <text x="50" y="457" fill="#9ca3af" font-size="11" font-family="Inter,sans-serif">Гол</text>
      <circle cx="90" cy="453" r="6" fill="#00d4aa" fill-opacity=".8"/>
      <text x="100" y="457" fill="#9ca3af" font-size="11" font-family="Inter,sans-serif">{home_name[:15]}</text>
      <circle cx="200" cy="453" r="6" fill="#f59e0b" fill-opacity=".8"/>
      <text x="210" y="457" fill="#9ca3af" font-size="11" font-family="Inter,sans-serif">{away_name[:15]}</text>
    </svg>"""

    col1, col2 = st.columns(2)
    col1.markdown(f'<div class="tile"><div class="tile-val">{home_xg:.2f}</div>'
                  f'<div class="tile-lbl">{home_name[:15]} xG</div></div>',
                  unsafe_allow_html=True)
    col2.markdown(f'<div class="tile"><div class="tile-val">{away_xg:.2f}</div>'
                  f'<div class="tile-lbl">{away_name[:15]} xG</div></div>',
                  unsafe_allow_html=True)
    st.markdown(svg, unsafe_allow_html=True)
    st.caption(f"⚪ Размерът на точката = xG стойност  ·  Зелено = гол  "
               f"·  {len(home_shots)} удара vs {len(away_shots)} удара")


def render_incidents(incidents: list, home_name: str, away_name: str):
    """Chronological match timeline: goals, cards, subs."""
    icons = {
        "goal":         "⚽", "own_goal":       "⚽🔴",
        "yellow_card":  "🟨", "yellow_red_card":"🟧",
        "red_card":     "🟥", "substitution":   "🔄",
        "var":          "📺", "penalty":        "🎯",
        "missed_penalty": "❌",
    }
    sorted_inc = sorted(incidents, key=lambda x: float(x.get("time") or x.get("minute") or 0))
    rows = []
    for inc in sorted_inc:
        t     = inc.get("time") or inc.get("minute") or "?"
        itype = (inc.get("incident_type") or inc.get("type") or "").lower().replace(" ","_")
        icon  = icons.get(itype, "•")
        player = inc.get("player_name") or inc.get("player","")
        team   = inc.get("team","")
        is_home = (team.lower() in home_name.lower()
                   if team else inc.get("is_home", True))
        desc = inc.get("description") or inc.get("text") or itype.replace("_"," ").title()

        if is_home:
            rows.append(f"""
            <div style="display:flex;align-items:center;gap:.5rem;margin:.25rem 0">
              <span style="min-width:35px;font-size:.75rem;color:#6b7280;font-weight:600">{t}′</span>
              <span style="font-size:1.1rem">{icon}</span>
              <span style="font-size:.85rem;color:#e2e8f0"><b>{player}</b> <span style="color:#6b7280">{desc}</span></span>
              <span style="flex:1"></span>
            </div>""")
        else:
            rows.append(f"""
            <div style="display:flex;align-items:center;gap:.5rem;margin:.25rem 0">
              <span style="min-width:35px;font-size:.75rem;color:#6b7280;font-weight:600">{t}′</span>
              <span style="flex:1"></span>
              <span style="font-size:.85rem;color:#e2e8f0;text-align:right"><span style="color:#6b7280">{desc}</span> <b>{player}</b></span>
              <span style="font-size:1.1rem">{icon}</span>
            </div>""")

    if not rows:
        st.caption("Няма инциденти.")
        return

    header = (f'<div style="display:flex;justify-content:space-between;'
              f'font-size:.72rem;font-weight:700;color:#4b5563;'
              f'text-transform:uppercase;letter-spacing:1px;margin-bottom:.5rem">'
              f'<span>{home_name}</span><span>{away_name}</span></div>')
    st.markdown(header + "".join(rows), unsafe_allow_html=True)


def render_bookmaker_odds(data: Dict, home_name: str, away_name: str):
    """Bookmaker-by-bookmaker odds comparison table."""
    import pandas as pd

    # Handle various API response shapes
    if not data or not isinstance(data, dict):
        return False   # signal: no data

    # Try to extract list of bookmakers
    books = None
    for key in ("bookmakers", "results", "data"):
        v = data.get(key)
        if isinstance(v, list) and v:
            books = v
            break

    # If no list found, the whole dict might be consensus odds — not bookmaker comparison
    if not books:
        return False

    rows = []
    for bk in books:
        if not isinstance(bk, dict):
            continue
        name = bk.get("bookmaker_name") or bk.get("name") or bk.get("id","?")
        mw   = bk.get("match_winner") or bk.get("1x2") or {}
        ou   = bk.get("over_under") or {}
        btts = bk.get("btts") or {}
        if not isinstance(mw,   dict): mw   = {}
        if not isinstance(ou,   dict): ou   = {}
        if not isinstance(btts, dict): btts = {}
        row = {
            "Букмейкър": str(name),
            "1":    mw.get("home"),
            "X":    mw.get("draw"),
            "2":    mw.get("away"),
            "O2.5": ou.get("over_25") or ou.get("over"),
            "U2.5": ou.get("under_25") or ou.get("under"),
            "GG":   btts.get("yes"),
            "NG":   btts.get("no"),
        }
        if any(v for k, v in row.items() if k != "Букмейкър"):
            rows.append(row)

    if not rows:
        return False

    df = pd.DataFrame(rows).set_index("Букмейкър")
    numeric_cols = [c for c in df.columns]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")

    def _highlight_max(s):
        is_max = s == s.max()
        return ["background-color:rgba(0,212,170,0.15);color:#00d4aa;font-weight:700"
                if v else "color:#e2e8f0" for v in is_max]

    styled = (df.style
              .apply(_highlight_max, subset=numeric_cols, axis=0)
              .format("{:.2f}", na_rep="–")
              .set_table_styles([
                  {"selector": "th",
                   "props": "background:#161b27;color:#6b7280;font-size:.75rem;padding:6px 10px"},
                  {"selector": "td",
                   "props": "background:#0d1117;font-size:.82rem;padding:5px 10px;border-bottom:1px solid #1e2737"},
              ]))
    st.dataframe(styled, use_container_width=True)
    st.caption("🟢 = най-добра стойност за колоната")
    return True
# ═════════════════════════════════════════════════════════════════
# MATCH DETAIL — called only after "Зареди" button
# ═════════════════════════════════════════════════════════════════
def render_match_detail(m: Dict, eid, home_name: str, away_name: str,
                        home_id, away_id, is_finished: bool):
    from api import (get_event_stats, get_event_odds, get_prediction,
                     get_team_fixtures, get_h2h, get_event_incidents,
                     get_event_shotmap, get_event_lineups, get_odds_comparison)

    # Per-match slider for number of recent fixtures
    n_last = st.slider("Последни мачове за форма", 3, 15, 5,
                       key=f"nlast_{eid}")

    # ── Build AI context (lineups for AI only, not shown in UI) ───
    lineup_ctx = ""
    if eid:
        lu = get_event_lineups(eid)
        if lu:
            def _fmt_lineup(side_data):
                if not side_data: return "—"
                players = side_data.get("players") or side_data.get("lineup") or []
                if isinstance(players, list):
                    starters = [p.get("name","?") for p in players
                                if p.get("type","").lower() in ("starter","playing","")
                                or p.get("starter", True)]
                    return ", ".join(starters[:11]) if starters else "—"
                return "—"
            h_lu = lu.get("home") or lu.get("homeTeam") or {}
            a_lu = lu.get("away") or lu.get("awayTeam") or {}
            lineup_ctx = (f"\nЛИНКЪП {home_name}: {_fmt_lineup(h_lu)}"
                          f"\nЛИНКЪП {away_name}: {_fmt_lineup(a_lu)}")

    ctx = (f"home_id={home_id} away_id={away_id} event_id={eid} "
           f"home={home_name} away={away_name}{lineup_ctx}")

    # Add Dixon-Coles prediction to AI context (computed lazily, cached)
    try:
        from predictor import predict_match
        _hfx = get_team_fixtures(team_id=home_id, team_name=home_name, last_n=15)
        _afx = get_team_fixtures(team_id=away_id, team_name=away_name, last_n=15)
        _h2h = get_h2h(home_id, away_id, home_name=home_name, away_name=away_name, last_n=8)
        _pred = predict_match(home_name, away_name, _hfx, _afx, _h2h)
        ctx += (
            f"\n\nДИКСОН-КОУЛС ПРОГНОЗА:"
            f"\n  {home_name} победа: {int(_pred['home_win']*100)}%"
            f"  Равен: {int(_pred['draw']*100)}%"
            f"  {away_name} победа: {int(_pred['away_win']*100)}%"
            f"\n  xG: {home_name}={_pred['home_xg']}  {away_name}={_pred['away_xg']}"
            f"\n  BTTS: {int(_pred['btts']*100)}%"
            f"  Над 2.5 гола: {int(_pred['over25']*100)}%"
            f"\n  Топ резултат: "
            f"{_pred['top_scorelines'][0]['h']}–{_pred['top_scorelines'][0]['a']} "
            f"({int(_pred['top_scorelines'][0]['prob']*100)}%)"
            f"\n  Надеждност на модела: {_pred['confidence']}%"
        )
    except Exception:
        pass

    if is_finished:
        # FINISHED: Stats | Home | Away | H2H | Shotmap | Incidents | Odds | AI
        tabs = st.tabs(["📊 Статистики", f"🏠 {home_name[:13]}",
                        f"✈️ {away_name[:13]}", "⚔️ H2H",
                        "🎯 Удари", "📋 Инциденти",
                        "💰 Коефициенти", "🤖 AI"])
        off = 1
        with tabs[0]: render_event_stats_panel(eid, home_name, away_name)
    else:
        # UPCOMING: Home | Away | H2H | Odds & Prediction | AI (no Shotmap/Incidents)
        tabs = st.tabs([f"🏠 {home_name[:13]}", f"✈️ {away_name[:13]}",
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

    if is_finished:
        # ── Shotmap (finished only) ───────────────────────────────
        with tabs[off + 3]:
            shots = get_event_shotmap(eid) if eid else []
            if shots: render_shotmap(shots, home_name, away_name)
            else:     st.caption("Картата на ударите не е налична.")

        # ── Incidents (finished only) ─────────────────────────────
        with tabs[off + 4]:
            incidents = get_event_incidents(eid) if eid else []
            if incidents: render_incidents(incidents, home_name, away_name)
            else:         st.caption("Инцидентите не са налични.")

        odds_tab_idx = off + 5
        ai_tab_idx   = off + 6
    else:
        odds_tab_idx = off + 3
        ai_tab_idx   = off + 4

    # ── Odds / Prediction tab ─────────────────────────────────────
    with tabs[odds_tab_idx]:

        # ── 1. Dixon-Coles model prediction (always shown) ────────
        st.markdown('<div class="sec-hd">🧮 Статистическа прогноза (Dixon-Coles)</div>',
                    unsafe_allow_html=True)
        # Load form data (already cached from team tabs — free re-call)
        home_fx = get_team_fixtures(team_id=home_id, team_name=home_name, last_n=15)
        away_fx = get_team_fixtures(team_id=away_id, team_name=away_name, last_n=15)
        h2h_fx  = get_h2h(home_id, away_id,
                           home_name=home_name, away_name=away_name,
                           last_n=8)
        render_prediction_panel(home_name, away_name,
                                home_id, away_id,
                                home_fx, away_fx, h2h_fx)

        # ── 2. Bookmaker odds for comparison ──────────────────────
        st.markdown("")
        st.markdown('<div class="sec-hd">💰 Букмейкърски коефициенти</div>',
                    unsafe_allow_html=True)
        shown_odds = False
        if eid:
            bk_data = get_odds_comparison(eid)
            if bk_data:
                shown_odds = render_bookmaker_odds(bk_data, home_name, away_name) or False
            if not shown_odds:
                odds = get_event_odds(eid)
                if odds:
                    render_odds_row(odds)
                    shown_odds = True
        if not shown_odds:
            st.caption("Букмейкърски коефициенти не са налични от API-то.")

    # ── AI ────────────────────────────────────────────────────────
    with tabs[ai_tab_idx]:
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
# ═════════════════════════════════════════════════════════════════
# TAB 2 — НА ЖИВО
# Uses @st.fragment(run_every=N) — only THIS section reruns,
# not the whole page. AI chat, Програма tab, etc. are untouched.
# ═════════════════════════════════════════════════════════════════

# Refresh interval options (seconds) — chosen outside the fragment
# so the user can change it without the fragment resetting.
with tab_live:
    _ri_col1, _ri_col2 = st.columns([3, 1])
    with _ri_col1:
        st.markdown('<div class="sec-hd">Мачове на живо</div>', unsafe_allow_html=True)
    with _ri_col2:
        _refresh_interval = st.select_slider(
            "Обновяване",
            options=[3, 5, 10, 20, 30, 60],
            value=5,
            format_func=lambda x: f"⚡ {x}с" if x <= 5 else f"🔄 {x}с",
            label_visibility="collapsed",
        )


@st.fragment(run_every=_refresh_interval)
def live_tab_fragment():
    """
    This fragment reruns every `_refresh_interval` seconds independently.
    The rest of the app (Програма, AI chat history) is NOT re-executed.
    """
    from api import get_live_events

    # Drain WebSocket queue — get latest frames since last run
    new_frames = ws_mgr.drain()

    # Status bar
    _s1, _s2 = st.columns([4, 1])
    with _s1:
        if new_frames:
            st.caption(f"{ws_mgr.status}  ·  +{len(new_frames)} нови кадъра")
        else:
            st.caption(ws_mgr.status)
    with _s2:
        # Last updated timestamp
        from datetime import datetime
        st.caption(datetime.now().strftime("%H:%M:%S"))

    live_events = get_live_events()

    if not live_events:
        st.info("⏳ Няма мачове на живо в момента.")
        return

    for lev in live_events:
        eid       = lev.get("id")
        home_obj  = _team(lev.get("home_team") or lev.get("home"))
        away_obj  = _team(lev.get("away_team") or lev.get("away"))
        home_name = home_obj.get("name","?")
        away_name = away_obj.get("name","?")

        # Subscribe to WebSocket for this match
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
        sit_str = (
            f"{sit_icons.get(sit,'🏃')} {sit.replace('_',' ').title()} "
            f"· {'🏠' if sit_sid=='home' else '✈️' if sit_sid=='away' else ''}"
        ) if sit else ""

        exp_label = (f"🔴  {home_name}  {sh}–{sa}  {away_name}"
                     f"  {f'· {minute}′' if minute else ''}")

        with st.expander(exp_label, expanded=True):
            stats_col, ai_col = st.columns([1, 1], gap="large")

            # ── Left: live stats ──────────────────────────────────
            with stats_col:
                lg  = _league(lev)
                hdr = f"{lg}{'  ·  ' + sit_str if sit_str else ''}"
                st.markdown(f'<div class="sec-hd">{hdr}</div>',
                            unsafe_allow_html=True)

                ws_stats = snap.get("stats", {})
                if ws_stats:
                    hs  = ws_stats.get("home", {})
                    as_ = ws_stats.get("away", {})
                    ph  = int(extract_stat(hs,  "ball_possession"))
                    pa  = int(extract_stat(as_, "ball_possession"))
                    st.markdown(
                        f'<div style="display:flex;justify-content:space-between;margin:.4rem 0">'
                        f'<span style="font-size:1.4rem;font-weight:800;color:#00d4aa">{ph}%</span>'
                        f'<span style="font-size:.65rem;color:#6b7280;align-self:center">ОВЛАДЯВАНЕ</span>'
                        f'<span style="font-size:1.4rem;font-weight:800;color:#f59e0b">{pa}%</span>'
                        f'</div>', unsafe_allow_html=True)
                    for lbl, key in [
                        ("Удари",         "total_shots"),
                        ("В рамка",       "shots_on_target"),
                        ("xG",            "xg"),
                        ("Ъглови",        "corner_kicks"),
                        ("Опасни атаки",  "dangerous_attack"),
                        ("Атаки",         "attack"),
                        ("Фаулове",       "fouls"),
                        ("Жълти картони", "yellow_cards"),
                        ("Спасявания",    "goalkeeper_saves"),
                    ]:
                        hv = extract_stat(hs, key)
                        av = extract_stat(as_, key)
                        if hv or av:
                            render_stat_bar(lbl, hv, av)
                else:
                    st.caption("⏳ Изчакване на WebSocket данни…")
                    # Fallback to REST stats while WS warms up
                    render_event_stats_panel(eid, home_name, away_name)

                # Live odds from WebSocket
                ws_odds = snap.get("odds")
                if ws_odds:
                    st.markdown("")
                    render_odds_row(ws_odds)

                # ── Simple visual panels from WS series ───────────
                ser       = ws_mgr.series.get(eid, {})
                xg_h_list = ser.get("xg_home", [])
                xg_a_list = ser.get("xg_away", [])
                att_h_list = ser.get("att_home", [])
                att_a_list = ser.get("att_away", [])

                if xg_h_list and xg_a_list:
                    xg_h_val  = xg_h_list[-1]
                    xg_a_val  = xg_a_list[-1]
                    att_h_val = att_h_list[-1] if att_h_list else 0
                    att_a_val = att_a_list[-1] if att_a_list else 0

                    # ── Helper: simple two-sided bar ───────────────
                    def _two_bar(lbl, h_val, a_val, h_color="#00d4aa", a_color="#f59e0b",
                                 fmt=lambda x: str(int(x)),
                                 tooltip=""):
                        total = h_val + a_val or 1
                        ph    = max(4, min(96, int(h_val / total * 100)))
                        pa    = 100 - ph
                        return f"""
<div style="margin:.55rem 0" title="{tooltip}">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
    <span style="font-size:.95rem;font-weight:800;color:{h_color}">{fmt(h_val)}</span>
    <span style="font-size:.65rem;color:#6b7280;text-transform:uppercase;
                 letter-spacing:1px;text-align:center;flex:1;padding:0 6px">{lbl}</span>
    <span style="font-size:.95rem;font-weight:800;color:{a_color}">{fmt(a_val)}</span>
  </div>
  <div style="display:flex;height:10px;border-radius:5px;overflow:hidden;gap:2px">
    <div style="width:{ph}%;background:{h_color};border-radius:5px 0 0 5px;opacity:.85"></div>
    <div style="width:{pa}%;background:{a_color};border-radius:0 5px 5px 0;opacity:.85"></div>
  </div>
</div>"""

                    # ── xG panel ──────────────────────────────────
                    # Explain xG simply
                    xg_label = "Качество на ударите (xG)"
                    xg_tip   = ("xG = очаквани голове. По-голямото число означава "
                                "по-опасни удари. 1.0 xG = трябва да е гол.")
                    shots_h  = ser.get("shots_home", [])
                    shots_a  = ser.get("shots_away", [])
                    shots_h_val = shots_h[-1] if shots_h else 0
                    shots_a_val = shots_a[-1] if shots_a else 0

                    st.markdown(
                        '<div class="sec-hd">⚽ КОЙ НАТИСКА?</div>',
                        unsafe_allow_html=True)

                    bars_html = ""
                    bars_html += _two_bar(
                        "Опасни атаки", att_h_val, att_a_val,
                        tooltip="Колко пъти всеки отбор е заплашил вратата")
                    bars_html += _two_bar(
                        "Удари в рамка", shots_h_val, shots_a_val,
                        tooltip="Удари, които вратарят е трябвало да спасява")
                    bars_html += _two_bar(
                        xg_label, xg_h_val, xg_a_val,
                        fmt=lambda x: f"{x:.2f}",
                        tooltip=xg_tip)

                    # Who is dominating indicator
                    if att_h_val + att_a_val > 0:
                        dom_pct  = int(att_h_val / (att_h_val + att_a_val) * 100)
                        dom_name = home_name if dom_pct >= 50 else away_name
                        dom_val  = dom_pct if dom_pct >= 50 else 100 - dom_pct
                        dom_color = "#00d4aa" if dom_pct >= 50 else "#f59e0b"
                        bars_html += f"""
<div style="margin-top:.7rem;padding:.6rem .8rem;
            background:rgba(0,0,0,.2);border-radius:8px;
            border-left:3px solid {dom_color}">
  <span style="font-size:.72rem;color:#6b7280">Доминира: </span>
  <span style="font-size:.9rem;font-weight:700;color:{dom_color}">{dom_name}</span>
  <span style="font-size:.72rem;color:#6b7280"> ({dom_val}% от атаките)</span>
</div>"""

                    # Team name legend
                    bars_html = f"""
<div style="display:flex;justify-content:space-between;
            margin-bottom:.5rem;font-size:.72rem;font-weight:700">
  <span style="color:#00d4aa">🏠 {home_name}</span>
  <span style="color:#f59e0b">✈️ {away_name}</span>
</div>""" + bars_html

                    st.markdown(bars_html, unsafe_allow_html=True)

                    # ── xG trend: simple emoji timeline ───────────
                    mins_list = ser.get("minutes", [])
                    if len(mins_list) >= 4:
                        st.markdown(
                            '<div class="sec-hd" style="margin-top:.8rem">'
                            '📈 КАК СЕ РАЗВИВА МАЧЪТ</div>',
                            unsafe_allow_html=True)

                        # Divide match into segments and show who led in each
                        n       = len(mins_list)
                        segs    = 6  # split into 6 segments
                        seg_len = max(1, n // segs)
                        timeline_html = '<div style="display:flex;gap:3px;margin-top:.3rem">'

                        for s in range(segs):
                            start = s * seg_len
                            end   = min(start + seg_len, n)
                            if start >= n:
                                break
                            seg_xg_h = xg_h_list[end-1] - (xg_h_list[start] if start > 0 else 0)
                            seg_xg_a = xg_a_list[end-1] - (xg_a_list[start] if start > 0 else 0)
                            seg_min  = mins_list[start]
                            seg_max  = mins_list[end-1]

                            if seg_xg_h > seg_xg_a * 1.3:
                                color = "#00d4aa"; icon = "▲"
                                tip   = f"{home_name} натиска"
                            elif seg_xg_a > seg_xg_h * 1.3:
                                color = "#f59e0b"; icon = "▲"
                                tip   = f"{away_name} натиска"
                            else:
                                color = "#4b5563"; icon = "▬"
                                tip   = "Равностойно"

                            timeline_html += f"""
<div style="flex:1;text-align:center;padding:.4rem .2rem;
            background:rgba(0,0,0,.2);border-radius:6px;
            border-bottom:3px solid {color}" title="{tip}">
  <div style="font-size:.6rem;color:#6b7280">{seg_min}′–{seg_max}′</div>
  <div style="font-size:.9rem;color:{color}">{icon}</div>
</div>"""

                        timeline_html += "</div>"
                        timeline_html += f"""
<div style="display:flex;gap:10px;margin-top:.4rem;font-size:.65rem;color:#6b7280">
  <span style="color:#00d4aa">▲ {home_name}</span>
  <span style="color:#f59e0b">▲ {away_name}</span>
  <span style="color:#4b5563">▬ Равно</span>
</div>"""
                        st.markdown(timeline_html, unsafe_allow_html=True)


            # ── Right: AI chat ────────────────────────────────────
            with ai_col:
                # Build live context for Gemini from latest WS snapshot
                ws_stats_now = snap.get("stats", {})
                hs2  = ws_stats_now.get("home", {}) if ws_stats_now else {}
                as_2 = ws_stats_now.get("away", {}) if ws_stats_now else {}
                live_ctx = ""
                if ws_stats_now:
                    live_ctx = (
                        f"\nLIVE WS ДАННИ: "
                        f"{home_name} — "
                        f"удари={extract_stat(hs2,'total_shots')} "
                        f"xG={extract_stat(hs2,'xg'):.2f} "
                        f"поз={extract_stat(hs2,'ball_possession'):.0f}% "
                        f"оп.атаки={extract_stat(hs2,'dangerous_attack')} | "
                        f"{away_name} — "
                        f"удари={extract_stat(as_2,'total_shots')} "
                        f"xG={extract_stat(as_2,'xg'):.2f} "
                        f"поз={extract_stat(as_2,'ball_possession'):.0f}% "
                        f"оп.атаки={extract_stat(as_2,'dangerous_attack')}"
                    )
                if sit_str:
                    live_ctx += f"\nСИТУАЦИЯ: {sit_str}"
                mw = ((snap.get("odds") or {}).get("odds") or {}).get("match_winner", {}) or {}
                if mw:
                    live_ctx += (f"\nЖИВИ КОЕФИЦИЕНТИ: "
                                 f"1={mw.get('home','?')} "
                                 f"X={mw.get('draw','?')} "
                                 f"2={mw.get('away','?')}")

                st.markdown(
                    f'<div class="sec-hd">🤖 AI — {home_name} vs {away_name}</div>',
                    unsafe_allow_html=True)

                # Full WS history context for AI
                ws_ai_ctx = ws_mgr.get_ai_context(eid, home_name, away_name)
                render_inline_ai(lev, f"ai_live_{eid}", home_name, away_name,
                                 event_id=eid, extra_ctx=ws_ai_ctx)


# Run the fragment inside the tab
with tab_live:
    live_tab_fragment()
