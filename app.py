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

    # ── Confidence breakdown (3 components) ──────────────────────
    conf       = p["confidence"]
    d_conf     = p.get("data_confidence",  0)
    m_conf     = p.get("model_confidence", 0)
    h2h_align  = p.get("h2h_alignment",    0)
    conf_label = p.get("conf_label", "—")
    conf_color = "#22c55e" if conf>=75 else "#f59e0b" if conf>=55 else "#ef4444" if conf>=35 else "#6b7280"

    align_str  = ("✅ Съгласуване" if h2h_align > 0.2 else
                  "❌ Разминаване" if h2h_align < -0.1 else
                  "➖ Неутрален")
    align_color= "#22c55e" if h2h_align>0.2 else "#ef4444" if h2h_align<-0.1 else "#6b7280"

    st.markdown(f"""
    <div style="background:#0d1117;border:1px solid #1e2737;border-radius:10px;
                padding:.8rem 1rem;margin-bottom:1rem">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.6rem">
        <span style="font-size:.75rem;font-weight:700;color:#9ca3af">
          СИГУРНОСТ НА ПРОГНОЗАТА
        </span>
        <span style="font-size:1.1rem;font-weight:900;color:{conf_color}">
          {conf}% &nbsp;<span style="font-size:.75rem;font-weight:600">{conf_label}</span>
        </span>
      </div>
      <div style="height:8px;background:#1e2737;border-radius:4px;margin-bottom:.7rem">
        <div style="width:{conf}%;height:100%;border-radius:4px;
                    background:linear-gradient(90deg,{conf_color}88,{conf_color})"></div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:.4rem">
        <div style="background:#161b27;border-radius:6px;padding:.4rem .5rem">
          <div style="font-size:.6rem;color:#6b7280">📊 Данни</div>
          <div style="font-size:.85rem;font-weight:700;color:#0ea5e9">{d_conf}%</div>
          <div style="font-size:.6rem;color:#4b5563">
            {p['home_matches_used']}+{p['away_matches_used']} мача
          </div>
        </div>
        <div style="background:#161b27;border-radius:6px;padding:.4rem .5rem">
          <div style="font-size:.6rem;color:#6b7280">🎯 Категоричност</div>
          <div style="font-size:.85rem;font-weight:700;color:#a78bfa">{m_conf}%</div>
          <div style="font-size:.6rem;color:#4b5563">концентрация на вероятности</div>
        </div>
        <div style="background:#161b27;border-radius:6px;padding:.4rem .5rem">
          <div style="font-size:.6rem;color:#6b7280">⚔️ H2H</div>
          <div style="font-size:.75rem;font-weight:700;color:{align_color}">{align_str}</div>
          <div style="font-size:.6rem;color:#4b5563">{p.get('h2h_used',0)} мача H2H</div>
        </div>
      </div>
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

    # ── Match Importance ──────────────────────────────────────────
    try:
        from match_importance import get_match_importance
        league_name = _league(m)
        league_id_mi = None
        for lg in get_leagues():
            if league_name.lower() in (lg.get("name") or "").lower():
                league_id_mi = lg.get("id"); break
        imp = get_match_importance(league_name, league_id_mi,
                                   home_name, away_name, home_id, away_id)
        if imp.get("available"):
            ic1, ic2 = st.columns(2)
            for col, prefix, tname in [(ic1,"home",home_name),(ic2,"away",away_name)]:
                sc  = imp[f"{prefix}_score"]
                lbl = imp[f"{prefix}_label"]
                emj = imp[f"{prefix}_emoji"]
                bar_color = ("#ef4444" if sc >= 75 else
                             "#f59e0b" if sc >= 45 else "#4b5563")
                col.markdown(
                    f'<div style="background:#161b27;border:1px solid #1e2737;'
                    f'border-radius:8px;padding:.6rem .8rem;margin-bottom:.4rem">'
                    f'<div style="font-size:.65rem;color:#6b7280;margin-bottom:3px">'
                    f'{emj} {tname[:18]} — Важност</div>'
                    f'<div style="display:flex;align-items:center;gap:.4rem">'
                    f'<div style="flex:1;background:#1e2737;border-radius:3px;height:6px">'
                    f'<div style="width:{sc}%;background:{bar_color};'
                    f'border-radius:3px;height:100%"></div></div>'
                    f'<span style="font-size:.8rem;font-weight:700;color:{bar_color}">'
                    f'{sc}</span></div>'
                    f'<div style="font-size:.7rem;color:{bar_color};margin-top:2px">'
                    f'{lbl}</div></div>',
                    unsafe_allow_html=True)
    except Exception:
        pass


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


# ═════════════════════════════════════════════════════════════════
# AUTO-SAVE PREDICTIONS + CHECK RESULTS — runs on EVERY rerun
# Must be outside any tab so it executes regardless of active tab.
# ═════════════════════════════════════════════════════════════════
def _run_predictions_background(force: bool = False):
    """
    Save all predictions and update results — max 2 Gist writes per run.
    Cooldown: runs at most once every 10 minutes (unless force=True).
    Prevents GitHub secondary rate limits on frequent Streamlit reruns.
    """
    from datetime import datetime as _dt
    import time as _t

    COOLDOWN_SEC = 600   # 10 minutes between Gist writes

    if not force:
        last_run = st.session_state.get("_pred_last_run", 0)
        if _t.time() - last_run < COOLDOWN_SEC:
            return   # too soon — skip silently

    # Mark start time immediately so concurrent reruns don't pile up
    st.session_state["_pred_last_run"] = _t.time()
    from predictions_db import (is_configured, save_predictions_batch,
                                 update_results_batch)
    if not is_configured():
        return

    from api import get_events as _ge, get_team_fixtures as _gtf, get_h2h as _gh2h
    from predictor import predict_match as _pm
    from datetime import date, timedelta

    log   = st.session_state.setdefault("_pred_log", [])
    today = date.today()
    yesterday = today - timedelta(days=1)

    # ── Build prediction batch ─────────────────────────────────────
    try:
        today_events = _ge(date_from=today.isoformat(),
                           date_to=today.isoformat(), limit=100)
        log.append(f"OK Заредени {len(today_events)} мача за {today.isoformat()}")
    except Exception as e:
        log.append(f"ERR get_events: {e}"); today_events = []

    batch = []; skipped_finished = 0; calc_errors = 0
    for _ev in today_events:
        _eid = _ev.get("id")
        if not _eid: continue
        _st  = (_ev.get("status","") or "").lower()
        if _st in ("finished","ft","ended","complete","aet","pen_finished"):
            skipped_finished += 1; continue
        _ho  = _team(_ev.get("home_team") or _ev.get("home"))
        _ao  = _team(_ev.get("away_team") or _ev.get("away"))
        _hn  = _ho.get("name","?"); _an = _ao.get("name","?")
        _hid = _ho.get("id");       _aid = _ao.get("id")
        try:
            _hfx  = _gtf(team_id=_hid, team_name=_hn, last_n=15)
            _afx  = _gtf(team_id=_aid, team_name=_an, last_n=15)
            _h2h  = _gh2h(_hid, _aid, home_name=_hn, away_name=_an, last_n=8)
            _pred = _pm(_hn, _an, _hfx, _afx, _h2h)
            batch.append({"event_id": _eid, "home": _hn, "away": _an,
                          "league": _league(_ev), "kickoff_bg": _kickoff(_ev),
                          "prediction": _pred})
        except Exception as e:
            log.append(f"ERR predict {_hn} vs {_an}: {e}"); calc_errors += 1

    # Single Gist write for all predictions
    if batch:
        saved, skipped_dup, err = save_predictions_batch(batch)
        if err:
            log.append(f"ERR save_batch: {err}")
        else:
            log.append(f"OK Записани:{saved} Дублирани:{skipped_dup} "
                       f"Завършили:{skipped_finished} Грешки:{calc_errors}")
    else:
        log.append(f"OK Нищо ново (завършили:{skipped_finished} грешки:{calc_errors})")

    # ── Build results batch ────────────────────────────────────────
    results_batch = []
    for check_date in [today.isoformat(), yesterday.isoformat()]:
        try:
            finished = _ge(date_from=check_date, date_to=check_date,
                           status="finished", limit=100)
            log.append(f"OK Завършили на {check_date}: {len(finished)}")
        except Exception as e:
            log.append(f"ERR finished {check_date}: {e}"); finished = []
        for _ev in finished:
            _eid = _ev.get("id")
            if not _eid: continue
            _sh, _sa = _score(_ev)
            try:
                results_batch.append({"event_id": _eid,
                                      "target_date": check_date,
                                      "home_goals": int(_sh),
                                      "away_goals": int(_sa)})
            except (ValueError, TypeError):
                pass

    # Single Gist write for all results
    if results_batch:
        updated, err = update_results_batch(results_batch)
        if err:
            log.append(f"ERR update_batch: {err}")
        elif updated:
            log.append(f"OK Резултати обновени: {updated}")
            st.toast(f"✅ {updated} прогнози проверени с реални резултати")

    st.session_state["_pred_log"] = log[-60:]


_run_predictions_background()

tab_schedule, tab_live, tab_results = st.tabs(
    ["📅 Програма", "🔴 На Живо", "📊 Резултати от прогнози"])


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


# ── Auto-record today's predictions (runs inside Tab 1 context) ──
# We silently record Dixon-Coles predictions for all upcoming matches
# so Tab 3 has data to work with at end of day.
with tab_schedule:
    try:
        from predictions_db import record_prediction
        from predictor import predict_match
        _today_str = date.today().isoformat()
        _upcoming = [m for m in events
                     if _status(m) not in
                     ("finished","ft","aet","pen_finished","ended","complete",
                      "inprogress","live","1h","2h","ht","et","pen")]
        for _m in _upcoming[:20]:   # cap at 20 to avoid hammering API
            _eid  = _m.get("id")
            if not _eid: continue
            _ho   = _team(_m.get("home_team") or _m.get("home"))
            _ao   = _team(_m.get("away_team") or _m.get("away"))
            _hn   = _ho.get("name","?")
            _an   = _ao.get("name","?")
            _hid  = _ho.get("id"); _aid = _ao.get("id")
            try:
                _hfx = get_team_fixtures(team_id=_hid, team_name=_hn, last_n=15)
                _afx = get_team_fixtures(team_id=_aid, team_name=_an, last_n=15)
                _h2h = get_h2h(_hid, _aid, home_name=_hn, away_name=_an, last_n=8)
                _pred = predict_match(_hn, _an, _hfx, _afx, _h2h)
                record_prediction(
                    event_id=_eid, home_name=_hn, away_name=_an,
                    league=_league(_m), kickoff_bg=_kickoff(_m),
                    pred=_pred, match_date=_today_str,
                )
            except Exception:
                pass
    except Exception:
        pass


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
    from api import get_live_events, get_event_stats

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

                # ── КОЙ НАТИСКА? — uses ws_stats primary, REST fallback ──
                # Get stats from the snapshot (already loaded above)
                ser       = ws_mgr.series.get(eid, {})

                # Primary: WS snapshot stats (available for most matches)
                _snap_stats = snap.get("stats", {})
                if _snap_stats:
                    _hs  = _snap_stats.get("home", {})
                    _as_ = _snap_stats.get("away", {})
                else:
                    # Fallback: REST stats (for matches where WS stats frame
                    # hasn't arrived yet but REST has data)
                    _rest = get_event_stats(eid) if eid else {}
                    _hs  = _rest.get("home", {}) if _rest else {}
                    _as_ = _rest.get("away", {}) if _rest else {}

                # Extract values — prefer WS series history for xG (cumulative)
                # but fall back to snapshot value
                att_h_val   = extract_stat(_hs, "dangerous_attack")
                att_a_val   = extract_stat(_as_, "dangerous_attack")
                shots_h_val = extract_stat(_hs, "shots_on_target")
                shots_a_val = extract_stat(_as_, "shots_on_target")
                # xG: use series last value if available, else snapshot
                xg_h_ser = ser.get("xg_home", [])
                xg_a_ser = ser.get("xg_away", [])
                xg_h_val = xg_h_ser[-1] if xg_h_ser else extract_stat(_hs, "xg")
                xg_a_val = xg_a_ser[-1] if xg_a_ser else extract_stat(_as_, "xg")

                # Only skip if we have absolutely nothing
                has_any = any([att_h_val, att_a_val, shots_h_val,
                               shots_a_val, xg_h_val, xg_a_val,
                               extract_stat(_hs, "total_shots"),
                               extract_stat(_hs, "ball_possession")])

                if has_any:
                    # total_shots as fallback if no dangerous_attack data
                    if not att_h_val and not att_a_val:
                        att_h_val = extract_stat(_hs,  "total_shots")
                        att_a_val = extract_stat(_as_, "total_shots")
                        att_label = "Общо удари"
                    else:
                        att_label = "Опасни атаки"

                    def _two_bar(lbl, h_val, a_val,
                                 h_color="#00d4aa", a_color="#f59e0b",
                                 fmt=lambda x: str(int(x)), tooltip=""):
                        total = h_val + a_val or 1
                        ph    = max(4, min(96, int(h_val / total * 100)))
                        pa    = 100 - ph
                        return (
                            f'<div style="margin:.55rem 0" title="{tooltip}">'
                            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">'
                            f'<span style="font-size:.95rem;font-weight:800;color:{h_color}">{fmt(h_val)}</span>'
                            f'<span style="font-size:.65rem;color:#6b7280;text-transform:uppercase;letter-spacing:1px;text-align:center;flex:1;padding:0 6px">{lbl}</span>'
                            f'<span style="font-size:.95rem;font-weight:800;color:{a_color}">{fmt(a_val)}</span>'
                            f'</div>'
                            f'<div style="display:flex;height:10px;border-radius:5px;overflow:hidden;gap:2px">'
                            f'<div style="width:{ph}%;background:{h_color};border-radius:5px 0 0 5px;opacity:.85"></div>'
                            f'<div style="width:{pa}%;background:{a_color};border-radius:0 5px 5px 0;opacity:.85"></div>'
                            f'</div></div>'
                        )

                    st.markdown('<div class="sec-hd">⚽ КОЙ НАТИСКА?</div>',
                                unsafe_allow_html=True)

                    legend = (
                        '<div style="display:flex;justify-content:space-between;'
                        'margin-bottom:.5rem;font-size:.72rem;font-weight:700">'
                        f'<span style="color:#00d4aa">🏠 {home_name}</span>'
                        f'<span style="color:#f59e0b">✈️ {away_name}</span></div>'
                    )
                    bars_html = legend
                    bars_html += _two_bar(att_label, att_h_val, att_a_val,
                        tooltip="Колко пъти всеки отбор е заплашил вратата")
                    if shots_h_val or shots_a_val:
                        bars_html += _two_bar("Удари в рамка", shots_h_val, shots_a_val,
                            tooltip="Удари, които вратарят е трябвало да спасява")
                    if xg_h_val or xg_a_val:
                        bars_html += _two_bar("xG (качество на ударите)", xg_h_val, xg_a_val,
                            fmt=lambda x: f"{x:.2f}",
                            tooltip="1.0 xG = трябваше да е гол. По-голямо = по-опасно.")
                    poss_h = extract_stat(_hs, "ball_possession")
                    poss_a = extract_stat(_as_, "ball_possession")
                    if poss_h or poss_a:
                        bars_html += _two_bar("Овладяване %", poss_h, poss_a,
                            fmt=lambda x: f"{int(x)}%")

                    dom_base_h = att_h_val or poss_h
                    dom_base_a = att_a_val or poss_a
                    if dom_base_h + dom_base_a > 0:
                        dom_pct   = int(dom_base_h / (dom_base_h + dom_base_a) * 100)
                        dom_name  = home_name if dom_pct >= 50 else away_name
                        dom_val   = dom_pct if dom_pct >= 50 else 100 - dom_pct
                        dom_color = "#00d4aa" if dom_pct >= 50 else "#f59e0b"
                        bars_html += (
                            '<div style="margin-top:.7rem;padding:.6rem .8rem;'
                            'background:rgba(0,0,0,.2);border-radius:8px;'
                            f'border-left:3px solid {dom_color}">'
                            '<span style="font-size:.72rem;color:#6b7280">Доминира: </span>'
                            f'<span style="font-size:.9rem;font-weight:700;color:{dom_color}">{dom_name}</span>'
                            f'<span style="font-size:.72rem;color:#6b7280"> ({dom_val}%)</span></div>'
                        )
                    st.markdown(bars_html, unsafe_allow_html=True)


                    # ── Timeline from WS series (only if enough points) ──
                    mins_list = ser.get("minutes", [])
                    if len(mins_list) >= 4 and xg_h_list and xg_a_list:
                        st.markdown(
                            '<div class="sec-hd" style="margin-top:.8rem">📈 КАК СЕ РАЗВИВА МАЧЪТ</div>',
                            unsafe_allow_html=True)
                        n = len(mins_list); segs = 6; seg_len = max(1, n // segs)
                        tl_parts = ['<div style="display:flex;gap:3px;margin-top:.3rem">']
                        for s in range(segs):
                            start = s * seg_len; end = min(start + seg_len, n)
                            if start >= n: break
                            seg_xg_h = xg_h_list[end-1] - (xg_h_list[start] if start > 0 else 0)
                            seg_xg_a = xg_a_list[end-1] - (xg_a_list[start] if start > 0 else 0)
                            seg_min  = mins_list[start]; seg_max = mins_list[end-1]
                            if seg_xg_h > seg_xg_a * 1.3:
                                color = "#00d4aa"; icon = "▲"; tip = f"{home_name} натиска"
                            elif seg_xg_a > seg_xg_h * 1.3:
                                color = "#f59e0b"; icon = "▲"; tip = f"{away_name} натиска"
                            else:
                                color = "#4b5563"; icon = "▬"; tip = "Равностойно"
                            tl_parts.append(
                                f'<div style="flex:1;text-align:center;padding:.4rem .2rem;'
                                f'background:rgba(0,0,0,.2);border-radius:6px;'
                                f'border-bottom:3px solid {color}" title="{tip}">'
                                f'<div style="font-size:.6rem;color:#6b7280">{seg_min}\'–{seg_max}\'</div>'
                                f'<div style="font-size:.9rem;color:{color}">{icon}</div></div>'
                            )
                        tl_parts.append('</div>')
                        tl_parts.append(
                            f'<div style="display:flex;gap:10px;margin-top:.4rem;font-size:.65rem;color:#6b7280">'
                            f'<span style="color:#00d4aa">▲ {home_name}</span>'
                            f'<span style="color:#f59e0b">▲ {away_name}</span>'
                            f'<span style="color:#4b5563">▬ Равно</span></div>'
                        )
                        st.markdown("".join(tl_parts), unsafe_allow_html=True)

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


# ═════════════════════════════════════════════════════════════════
# TAB 3 — РЕЗУЛТАТИ ОТ ПРОГНОЗИ
# ═════════════════════════════════════════════════════════════════
with tab_results:
    from predictions_db import (
        is_configured, save_prediction, update_result,
        save_predictions_batch, update_results_batch,
        load_predictions_for_date, load_predictions_range,
        compute_stats,
    )
    from api import get_events as _get_events

    # ── Setup check ───────────────────────────────────────────────
    if not is_configured():
        st.markdown('''
<div style="background:#161b27;border:1px solid #1e2737;border-radius:12px;padding:1.5rem">
  <div style="font-size:1rem;font-weight:700;color:#e2e8f0;margin-bottom:.8rem">
    🔧 Нужна е настройка за съхранение на прогнози
  </div>
  <div style="font-size:.85rem;color:#9ca3af;line-height:1.8">
    <b>Стъпка 1:</b> Отиди на github.com → Settings → Developer Settings →
    Personal Access Tokens → New token → отбележи scope: <code>gist</code><br>
    <b>Стъпка 2:</b> Създай нов Secret Gist на gist.github.com с файл
    <code>predictions.json</code> и съдържание <code>{}</code><br>
    <b>Стъпка 3:</b> Добави в Streamlit Secrets:
  </div>
</div>''', unsafe_allow_html=True)
        st.code('''GITHUB_TOKEN = "ghp_xxxxxxxxxxxx"   # токен с gist scope
GIST_ID      = "abc123def456"       # ID от URL-а на Gist''')
        st.stop()

    today_str = date.today().isoformat()

    # ── Diagnostic panel ─────────────────────────────────────────
    with st.expander("🔧 Диагностика (разгъни ако нищо не се записва)", expanded=False):
        log = st.session_state.get("_pred_log", [])
        if log:
            for line in log[-30:]:
                color = ("#22c55e" if line.startswith("OK") or "OK" in line[:3]
                         else "#ef4444" if line.startswith("ERR")
                         else "#f59e0b" if line.startswith("WARN")
                         else "#9ca3af")
                st.markdown(f'<span style="font-size:.78rem;color:{color};'
                            f'font-family:monospace">{line}</span>',
                            unsafe_allow_html=True)
        else:
            st.caption("Лог е празен — background функцията още не е изпълнена.")

        # PATCH connectivity test
        if st.button("✏️ Тествай PATCH (запис)", key="test_patch"):
            from predictions_db import _gist_id, _headers, _load_raw
            import requests as _req
            gid = _gist_id()
            st.code(f"PATCH към GIST_ID: {gid!r}")
            try:
                # Read current content first
                current = _load_raw()
                # Write it back unchanged — safest possible test
                payload = {"files": {"predictions.json": {
                    "content": __import__('json').dumps(current, ensure_ascii=False)
                }}}
                r = _req.patch(
                    f"https://api.github.com/gists/{gid}",
                    headers=_headers(), json=payload, timeout=10
                )
                st.code(f"PATCH → HTTP {r.status_code}")
                if r.status_code == 200:
                    st.success("✅ PATCH работи!")
                else:
                    try: detail = r.json().get("message", r.text[:300])
                    except: detail = r.text[:300]
                    st.error(f"❌ {detail}")
            except Exception as e:
                st.error(f"Exception: {e}")
            st.session_state["_pred_log"] = []
            _run_predictions_background()
            st.rerun()

        # Gist connectivity test
        if st.button("🔌 Тествай връзката с Gist", key="test_gist"):
            from predictions_db import _load_raw, _gist_id
            import requests
            gid = _gist_id()
            st.code(f"GIST_ID = {repr(gid)}")
            if gid:
                try:
                    import streamlit as _st
                    token = _st.secrets.get("GITHUB_TOKEN","")
                    st.code(f"GITHUB_TOKEN = {'SET ('+str(len(token))+' chars)' if token else 'NOT SET'}")
                    r = requests.get(
                        f"https://api.github.com/gists/{gid}",
                        headers={"Authorization": f"token {token}",
                                 "Accept": "application/vnd.github.v3+json"},
                        timeout=8)
                    st.code(f"GET /gists/{gid[:8]}... → HTTP {r.status_code}")
                    if r.status_code == 200:
                        files = r.json().get("files", {})
                        st.code(f"Files in Gist: {list(files.keys())}")
                        content = files.get("predictions.json",{}).get("content","")
                        st.code(f"predictions.json content ({len(content)} chars): {content[:200]}")
                    else:
                        st.error(f"Gist API грешка: {r.text[:300]}")
                except Exception as e:
                    st.error(f"Грешка: {e}")

    # ── Filters ───────────────────────────────────────────────────
    st.markdown('<div class="sec-hd">Филтри</div>', unsafe_allow_html=True)
    fc1, fc2, fc3, fc4 = st.columns([1.5, 1.5, 1.5, 1])
    with fc1:
        view_mode = st.radio("Период", ["Днес","Последни 7 дни",
                                         "Последни 30 дни","Всички"],
                             horizontal=True)
    with fc2:
        min_conf = st.slider("Минимална сигурност (%)", 0, 90, 0, step=5,
                             help="Изключва прогнози с по-ниска сигурност от избраната")
    with fc3:
        show_only = st.selectbox("Покажи", ["Всички","Само проверени","Само чакащи"])
    with fc4:
        st.markdown("")
        export_btn = st.button("⬇️ Изтегли CSV")

    # ── Load data ─────────────────────────────────────────────────
    days_map = {"Днес":0,"Последни 7 дни":7,"Последни 30 дни":30,"Всички":365}
    days_back = days_map[view_mode]
    if days_back == 0:
        all_preds = load_predictions_for_date(today_str)
        for p in all_preds: p.setdefault("date", today_str)
    else:
        all_preds = load_predictions_range(days_back)

    # Filter by confidence
    preds = [p for p in all_preds
             if (p.get("prediction",{}).get("confidence") or 0) >= min_conf]

    # Filter finished/pending
    if show_only == "Само проверени":
        preds = [p for p in preds if p.get("result")]
    elif show_only == "Само чакащи":
        preds = [p for p in preds if not p.get("result")]

    # ── Stats summary ─────────────────────────────────────────────
    stats = compute_stats(preds, min_confidence=min_conf)
    if stats["n"] > 0:
        st.markdown('<div class="sec-hd">📈 Обща точност</div>',
                    unsafe_allow_html=True)
        m1,m2,m3,m4,m5 = st.columns(5)
        metrics = [
            (m1, f"{stats['outcome_pct']}%",  f"1X2 точни ({stats['n']} мача)"),
            (m2, f"{stats['btts_pct']}%",     "BTTS точни"),
            (m3, f"{stats['over25_pct']}%",   "О2.5 точни"),
            (m4, f"{stats['scoreline_pct']}%","Точен резултат"),
            (m5, f"{stats.get('avg_xg_error') or '—'}","Средна xG грешка"),
        ]
        for col, val, lbl in metrics:
            col.markdown(f'<div class="tile"><div class="tile-val">{val}</div>'
                         f'<div class="tile-lbl">{lbl}</div></div>',
                         unsafe_allow_html=True)
        st.markdown("")

        # Confidence breakdown
        conf_bands = [(75,100,"Висока","#22c55e"),
                      (55,74, "Умерена","#f59e0b"),
                      (35,54, "Ниска","#ef4444"),
                      (0, 34, "Много ниска","#6b7280")]
        band_rows = []
        for lo,hi,lbl,col in conf_bands:
            band_preds = [p for p in preds
                          if lo <= (p.get("prediction",{}).get("confidence") or 0) <= hi]
            bs = compute_stats(band_preds)
            if bs["n"] > 0:
                band_rows.append((lbl, col, bs["n"], bs.get("outcome_pct","—")))
        if band_rows:
            st.markdown('<div class="sec-hd">Точност по сигурност</div>',
                        unsafe_allow_html=True)
            bcols = st.columns(len(band_rows))
            for col,(lbl,color,n,pct) in zip(bcols, band_rows):
                col.markdown(
                    f'<div class="tile" style="border-color:{color}30">'+
                    f'<div class="tile-val" style="color:{color}">{pct}%</div>'+
                    f'<div class="tile-lbl">{lbl} ({n})</div></div>',
                    unsafe_allow_html=True)
            st.markdown("")

    # ── CSV export ────────────────────────────────────────────────
    if export_btn and preds:
        import csv, io
        buf = io.StringIO()
        fieldnames = ["date","home","away","league","kickoff_bg",
                      "confidence","conf_label","home_win","draw","away_win",
                      "home_xg","away_xg","btts","over25",
                      "result_home","result_away","outcome_correct",
                      "btts_correct","over25_correct"]
        w = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for p in preds:
            pr = p.get("prediction",{}); res = p.get("result",{}); acc = p.get("accuracy",{})
            w.writerow({
                "date": p.get("date",""), "home": p.get("home",""),
                "away": p.get("away",""), "league": p.get("league",""),
                "kickoff_bg": p.get("kickoff_bg",""),
                "confidence":  pr.get("confidence",""),
                "conf_label":  pr.get("conf_label",""),
                "home_win":    pr.get("home_win",""), "draw": pr.get("draw",""),
                "away_win":    pr.get("away_win",""),
                "home_xg":     pr.get("home_xg",""),  "away_xg": pr.get("away_xg",""),
                "btts":        pr.get("btts",""),      "over25":  pr.get("over25",""),
                "result_home": (res or {}).get("home_goals",""),
                "result_away": (res or {}).get("away_goals",""),
                "outcome_correct": (acc or {}).get("outcome_correct",""),
                "btts_correct":    (acc or {}).get("btts_correct",""),
                "over25_correct":  (acc or {}).get("over25_correct",""),
            })
        st.download_button("📥 predictions.csv", buf.getvalue(),
                           "predictions.csv", "text/csv")

    # ── Prediction list ───────────────────────────────────────────
    st.markdown('<div class="sec-hd">Прогнози</div>', unsafe_allow_html=True)
    if not preds:
        st.info("Няма прогнози за избрания период / филтър.")
    else:
        preds_sorted = sorted(preds,
            key=lambda p: (
                0 if p.get("accuracy") else (1 if p.get("result") else 2),
                -(p.get("date","") or "").replace("-",""),
            ))
        for p in preds_sorted:
            pr   = p.get("prediction",{}) or {}
            acc  = p.get("accuracy",{})  or {}
            res  = p.get("result",{})    or {}
            oc   = acc.get("outcome_correct")
            if oc is True:    row_icon="✅"; row_col="#22c55e"
            elif oc is False: row_icon="❌"; row_col="#ef4444"
            else:             row_icon="⏳"; row_col="#6b7280"
            conf     = pr.get("confidence",0)
            conf_lbl = pr.get("conf_label","?")
            conf_c   = "#22c55e" if conf>=75 else "#f59e0b" if conf>=50 else "#ef4444"
            hw = int((pr.get("home_win") or 0)*100)
            dw = int((pr.get("draw") or 0)*100)
            aw = 100-hw-dw
            pred_out = acc.get("predicted_outcome","?")
            out_map  = {"home": f"🏠 {p.get('home','')[:12]}",
                        "draw": "⚖️ Равен",
                        "away": f"✈️ {p.get('away','')[:12]}"}
            pred_str = out_map.get(pred_out, pred_out)
            result_str = (f" · {res.get('home_goals','')}–{res.get('away_goals','')}"
                          if res else "")
            xg_str = (f"xG {pr['home_xg']}–{pr['away_xg']}  "
                      if pr.get("home_xg") and pr.get("away_xg") else "")
            sc = pr.get("top_scoreline") or {}
            sc_str = (f"Топ:{sc.get('h','?')}–{sc.get('a','?')}  " if sc else "")
            extras = []
            if acc.get("btts_correct") is not None:
                extras.append("BTTS ✅" if acc["btts_correct"] else "BTTS ❌")
            if acc.get("over25_correct") is not None:
                extras.append("O2.5 ✅" if acc["over25_correct"] else "O2.5 ❌")
            extra_str = "  ".join(extras)
            card = (
                f'<div style="background:#161b27;border:1px solid #1e2737;border-radius:8px;'
                f'border-left:3px solid {row_col};padding:.75rem 1rem;margin:.3rem 0">'
                f'<div style="display:flex;justify-content:space-between;align-items:flex-start">'
                f'<div><span style="font-size:.65rem;color:#6b7280">'
                f'{p.get("date","")} · {p.get("league","")[:22]} · {p.get("kickoff_bg","")}'
                f'</span><br>'
                f'<span style="font-size:.92rem;font-weight:700;color:#e2e8f0">'
                f'{p.get("home","")} vs {p.get("away","")}</span></div>'
                f'<div style="text-align:right">'
                f'<span style="font-size:1.2rem">{row_icon}</span><br>'
                f'<span style="font-size:.72rem;font-weight:700;color:{conf_c}">'
                f'{conf}% · {conf_lbl}</span></div></div>'
                f'<div style="margin-top:.5rem;display:flex;gap:3px;height:7px;border-radius:4px;overflow:hidden">'
                f'<div style="flex:{hw};background:#00d4aa;opacity:.8"></div>'
                f'<div style="flex:{dw};background:#4b5563"></div>'
                f'<div style="flex:{aw};background:#f59e0b;opacity:.8"></div></div>'
                f'<div style="display:flex;justify-content:space-between;font-size:.68rem;color:#6b7280;margin-top:2px">'
                f'<span>🏠 {hw}%</span><span>{dw}%</span><span>{aw}% ✈️</span></div>'
                f'<div style="margin-top:.4rem;font-size:.78rem">'
                f'<span style="color:#00d4aa">↪ {pred_str}</span>'
                f'<span style="color:#9ca3af"> · {xg_str}{sc_str}{result_str}</span>'
                + (f'<span style="color:#9ca3af;margin-left:.4rem">{extra_str}</span>' if extra_str else '')
                + '</div></div>'
            )
            st.markdown(card, unsafe_allow_html=True)


    # ── AI analysis of prediction performance ─────────────────────
    if stats.get("n",0) >= 3:
        st.markdown("")
        st.markdown('<div class="sec-hd">🤖 AI Анализ на прогнозите</div>',
                    unsafe_allow_html=True)
        if "results_chat" not in st.session_state:
            st.session_state["results_chat"] = []
        r_hist = st.session_state["results_chat"]
        for msg in r_hist:
            cls  = "ai-a" if msg["role"]=="assistant" else "ai-u"
            icon = "🤖 AI" if msg["role"]=="assistant" else "👤 Ти"
            st.markdown(f'<div class="{cls}"><div class="ai-role">{icon}</div>'
                        f'{msg["content"]}</div>', unsafe_allow_html=True)
        rq = st.text_input("Въпрос за прогнозите…",
                           key="res_q",
                           placeholder="Кои мачове прогнозирам най-добре? Как да подобря?",
                           label_visibility="collapsed")
        rc1,rc2 = st.columns([4,1])
        r_send  = rc1.button("Изпрати ↗", key="res_send")
        if rc2.button("Изчисти", key="res_clr"):
            st.session_state["results_chat"] = []; st.rerun()

        if r_send and rq.strip() and _gemini:
            r_ctx = (
                f"Статистики за {stats['n']} завършени мача:\n"
                f"  1X2 точност: {stats['outcome_pct']}%\n"
                f"  BTTS точност: {stats['btts_pct']}%\n"
                f"  O2.5 точност: {stats['over25_pct']}%\n"
                f"  Точен резултат: {stats['scoreline_pct']}%\n"
                f"  Средна xG грешка: {stats.get('avg_xg_error','—')}\n"
                f"\nПоследни 5 прогнози:\n" +
                "\n".join(
                    f"  {p.get('home','')} vs {p.get('away','')} "
                    f"→ {(p.get('accuracy') or {}).get('predicted_outcome','?')}"
                    f" {'✅' if (p.get('accuracy') or {}).get('outcome_correct') else '❌'}"
                    f" сигурност={(p.get('prediction') or {}).get('confidence',0)}%"
                    for p in (preds or [])[-5:])
            )
            sys_p = ("Ти си анализатор на прогностични модели. "
                     "Говори САМО на БЪЛГАРСКИ. Бъди конкретен и полезен.")
            with st.spinner("AI анализира…"):
                from gemini_tools import run_gemini_with_tools
                r_answer = run_gemini_with_tools(
                    _gemini, sys_p,
                    f"ДАННИ:\n{r_ctx}\n\nВЪПРОС: {rq.strip()}",
                    history=[m for m in r_hist if m["role"] in ("user","assistant")],
                )
            st.session_state["results_chat"].append({"role":"user","content":rq.strip()})
            st.session_state["results_chat"].append({"role":"assistant","content":r_answer})
            st.rerun()
