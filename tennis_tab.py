"""
🎾 Tennis tab — пълно UI за тенис раздела в bzzoiro-dashboard.
Импортира се от app.py като: from tennis_tab import render_tennis_tab
"""
from __future__ import annotations
import streamlit as st
from datetime import date, timedelta
from typing import Dict, List, Optional

from tennis_api import (
    tennis_get_matches, tennis_get_live, tennis_get_rankings,
    tennis_get_upcoming_predictions, tennis_get_h2h,
    tennis_get_prediction, parse_tennis_match,
)
from tennis_predictor import predict_winner, predict_games

# ── CSS допълнения за тенис ───────────────────────────────────────
TENNIS_CSS = """
<style>
.t-row{display:flex;align-items:center;background:#161b27;border:1px solid #1e2737;
  border-radius:10px;padding:.65rem 1rem;margin-bottom:.3rem;gap:.5rem}
.t-tourn{font-size:.62rem;color:#6b7280;font-weight:600;min-width:130px;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.t-players{display:flex;align-items:center;gap:.4rem;flex:1;justify-content:center}
.t-pname{font-size:.88rem;font-weight:600;color:#e2e8f0;flex:1;text-align:right}
.t-pname.a{text-align:left}
.t-score{background:#1e2737;border-radius:6px;padding:3px 12px;font-size:.95rem;
  font-weight:800;color:#00d4aa;letter-spacing:2px;white-space:nowrap}
.t-score.live{background:rgba(239,68,68,.12);color:#ef4444;border:1px solid rgba(239,68,68,.25)}
.t-score.up{color:#4b5563;font-size:.78rem;padding:3px 8px}
.t-surf{font-size:.6rem;padding:2px 6px;border-radius:4px;font-weight:700}
.t-surf.Hard{background:rgba(14,165,233,.15);color:#0ea5e9}
.t-surf.Clay{background:rgba(245,158,11,.15);color:#f59e0b}
.t-surf.Grass{background:rgba(34,197,94,.15);color:#22c55e}
.t-surf.Carpet{background:rgba(167,139,250,.15);color:#a78bfa}
.prob-bar{display:flex;border-radius:8px;overflow:hidden;height:38px;margin:.5rem 0}
.rank-row{display:flex;align-items:center;gap:.5rem;padding:.4rem .6rem;
  border-bottom:1px solid #1e2737;font-size:.82rem}
.rank-pos{min-width:32px;font-weight:800;color:#00d4aa}
.rank-name{flex:1;color:#e2e8f0;font-weight:600}
.rank-pts{color:#6b7280;font-size:.75rem}
.rank-mv{font-size:.7rem;font-weight:700}
</style>
"""

def _surf_badge(surface: str) -> str:
    s = surface.capitalize()
    if s not in ("Hard","Clay","Grass","Carpet"): s = "Hard"
    labels = {"Hard":"🔵 Хард","Clay":"🟠 Клей","Grass":"🟢 Трева","Carpet":"🟣 Килим"}
    return f'<span class="t-surf {s}">{labels.get(s,s)}</span>'

def _bg_time(utc_str: str) -> str:
    if not utc_str: return ""
    from datetime import datetime
    s = str(utc_str).strip().rstrip("Zz")
    for fmt in ("%Y-%m-%dT%H:%M:%S","%Y-%m-%d %H:%M:%S","%Y-%m-%dT%H:%M"):
        try:
            dt = datetime.strptime(s[:16], fmt[:16])
            from datetime import timedelta as td
            return (dt + td(hours=3)).strftime("%H:%M")
        except: continue
    return s[11:16] if len(s) >= 16 else ""

def render_match_row_tennis(tm: Dict):
    """Рендира един тенис мач ред."""
    status = tm["status"]
    is_live = status in {"inprogress","live","playing","in_progress",
                         "1st_set","2nd_set","3rd_set","set1","set2","set3"}
    is_fin  = status in {"finished","ended","complete","closed"}

    sc1 = tm["p1_sets"]; sc2 = tm["p2_sets"]
    surf_badge = _surf_badge(tm["surface"])

    if is_live:
        score_html = f'<span class="t-score live">{sc1}–{sc2}</span>'
        pt = tm["current_pt"]
        time_html  = f'<span style="font-size:.65rem;color:#ef4444;font-weight:700;background:rgba(239,68,68,.1);border-radius:4px;padding:2px 5px">● LIVE{f" {pt}" if pt else ""}</span>'
    elif is_fin and sc1 != "" and sc2 != "":
        score_html = f'<span class="t-score">{sc1}–{sc2}</span>'
        time_html  = ""
    else:
        ko = _bg_time(tm["scheduled"])
        score_html = f'<span class="t-score up">{ko or "–"}</span>'
        time_html  = ""

    srv = ""
    if is_live and tm.get("is_srv_p1") is not None:
        srv = "🎾 " if tm["is_srv_p1"] else ""
        srv2 = "" if tm["is_srv_p1"] else "🎾 "
    else:
        srv = srv2 = ""

    rnd = f'<span style="font-size:.6rem;color:#4b5563">{tm["round"]}</span>' if tm["round"] else ""

    st.markdown(f"""<div class="t-row">
      <span class="t-tourn" title="{tm['tournament']}">{tm['tournament'][:22]}</span>
      {surf_badge}
      <div class="t-players">
        <span class="t-pname">{srv}{tm['p1_name']}</span>
        {score_html}
        <span class="t-pname a">{srv2}{tm['p2_name']}</span>
      </div>
      {rnd}{time_html}
    </div>""", unsafe_allow_html=True)

def render_match_detail_tennis(tm: Dict):
    """Разгъване с прогнози, H2H и Bzzoiro predictions."""
    mid  = tm["id"]
    p1   = tm["p1_name"]; p2 = tm["p2_name"]
    surf = tm["surface"]
    circ = tm["circuit"]
    bo   = 5 if "Grand Slam" in tm.get("tournament","") else 3

    tabs = st.tabs(["🧮 Прогноза", "⚔️ H2H", "📊 Bzzoiro ML"])

    # ── TAB 1: Наша прогноза ──────────────────────────────────────
    with tabs[0]:
        bz_pred = tennis_get_prediction(mid) if mid else {}

        # Вземаме rank и elo от Bzzoiro prediction ако са налични
        p1_rank = bz_pred.get("player1_rank") or bz_pred.get("p1_rank")
        p2_rank = bz_pred.get("player2_rank") or bz_pred.get("p2_rank")
        # За Elo нямаме директно от API — използваме rank като proxy
        p1_elo  = 1500 - float(p1_rank or 100) * 2 if p1_rank else 1500
        p2_elo  = 1500 - float(p2_rank or 100) * 2 if p2_rank else 1500

        result = predict_winner(
            p1_rank=p1_rank, p2_rank=p2_rank,
            p1_rank_pts=None, p2_rank_pts=None,
            p1_elo=p1_elo, p2_elo=p2_elo,
            p1_adj_elo=p1_elo, p2_adj_elo=p2_elo,
            surface=surf, circuit=circ, best_of=bo,
        )

        if result:
            p1p = int(result["p1_win_prob"] * 100)
            p2p = 100 - p1p
            conf= result["confidence"]
            conf_color = "#22c55e" if conf>=65 else "#f59e0b" if conf>=40 else "#6b7280"

            st.markdown(f'''<div style="background:#0d1117;border:1px solid #1e2737;
              border-radius:10px;padding:.8rem 1rem;margin-bottom:.8rem">
              <div style="display:flex;justify-content:space-between;margin-bottom:.4rem">
                <span style="font-size:.72rem;color:#9ca3af;font-weight:700">МЛ ПРОГНОЗА</span>
                <span style="font-size:.85rem;font-weight:800;color:{conf_color}">
                  Сигурност: {conf}%</span>
              </div>
              <div style="height:6px;background:#1e2737;border-radius:3px;margin-bottom:.6rem">
                <div style="width:{conf}%;height:100%;border-radius:3px;
                  background:linear-gradient(90deg,{conf_color}88,{conf_color})"></div>
              </div>
              <div style="font-size:.65rem;color:#4b5563">⚙️ {result["model_used"]}</div>
            </div>''', unsafe_allow_html=True)

            st.markdown(f"""<div class="prob-bar">
              <div style="flex:{p1p};background:linear-gradient(135deg,#00d4aa,#0ea5e9);
                display:flex;align-items:center;justify-content:center">
                <span style="font-size:.9rem;font-weight:800;color:#0d1117">{p1p}%</span>
              </div>
              <div style="flex:{p2p};background:linear-gradient(135deg,#f59e0b,#ef4444);
                display:flex;align-items:center;justify-content:center">
                <span style="font-size:.9rem;font-weight:800;color:#0d1117">{p2p}%</span>
              </div>
            </div>
            <div style="display:flex;justify-content:space-between;
              font-size:.72rem;color:#6b7280;margin-bottom:1rem">
              <span>🎾 {p1}</span><span>🎾 {p2}</span>
            </div>""", unsafe_allow_html=True)

            # Games prediction
            g_result = predict_games(
                elo_diff=p1_elo-p2_elo, adj_elo_diff=p1_elo-p2_elo,
                rank_diff=(p2_rank or 100)-(p1_rank or 100),
                rank_ratio=(p1_rank or 100)/((p2_rank or 100)+1),
                surface=surf, best_of=bo,
            )
            if g_result:
                st.markdown('<div style="font-size:.7rem;font-weight:700;color:#4b5563;'
                            'text-transform:uppercase;letter-spacing:1px;'
                            'margin:.8rem 0 .4rem;border-top:1px solid #1e2737;'
                            'padding-top:.8rem">Под/Над геймове</div>',
                            unsafe_allow_html=True)
                eg = g_result["expected_games"]
                cols = st.columns(4)
                tiles = [
                    (f"{eg:.1f}", "Очаквани геймове"),
                    (f"{int(g_result.get('over_205',0)*100)}%", "Над 20.5"),
                    (f"{int(g_result.get('over_215',0)*100)}%", "Над 21.5"),
                    (f"{int(g_result.get('over_225',0)*100)}%", "Над 22.5"),
                ]
                for col,(val,lbl) in zip(cols, tiles):
                    col.markdown(f'<div style="background:#161b27;border:1px solid #1e2737;'
                                 f'border-radius:8px;padding:.6rem;text-align:center">'
                                 f'<div style="font-size:1.2rem;font-weight:800;color:#00d4aa">{val}</div>'
                                 f'<div style="font-size:.62rem;color:#6b7280">{lbl}</div></div>',
                                 unsafe_allow_html=True)
        else:
            st.info("🤖 ML моделите не са заредени. Провери дали .pkl файловете са в /models/ папката.")
            st.caption("Използвай Bzzoiro ML таба за прогноза.")

    # ── TAB 2: H2H ────────────────────────────────────────────────
    with tabs[1]:
        if mid:
            h2h_data = tennis_get_h2h(mid)
            h2h_matches = (h2h_data.get("h2h") or
                           h2h_data.get("previous_matches") or [])
            p1_recent   = h2h_data.get("player1_recent") or []
            p2_recent   = h2h_data.get("player2_recent") or []

            if h2h_matches:
                p1w = p2w = 0
                for hm in h2h_matches:
                    w = hm.get("winner") or {}
                    wn = w.get("name","") if isinstance(w,dict) else str(w)
                    if p1.lower() in wn.lower(): p1w += 1
                    else: p2w += 1
                c1,c2 = st.columns(2)
                c1.markdown(f'<div style="background:#161b27;border:1px solid #1e2737;'
                            f'border-radius:8px;padding:.6rem;text-align:center">'
                            f'<div style="font-size:1.4rem;font-weight:800;color:#00d4aa">{p1w}</div>'
                            f'<div style="font-size:.65rem;color:#6b7280">{p1[:14]}</div></div>',
                            unsafe_allow_html=True)
                c2.markdown(f'<div style="background:#161b27;border:1px solid #1e2737;'
                            f'border-radius:8px;padding:.6rem;text-align:center">'
                            f'<div style="font-size:1.4rem;font-weight:800;color:#f59e0b">{p2w}</div>'
                            f'<div style="font-size:.65rem;color:#6b7280">{p2[:14]}</div></div>',
                            unsafe_allow_html=True)
                st.markdown("")
                for hm in h2h_matches[:8]:
                    tm2 = parse_tennis_match(hm)
                    render_match_row_tennis(tm2)
            else:
                st.info("Няма намерени H2H мачове.")

            if p1_recent or p2_recent:
                st.markdown("**Последни мачове:**")
                c1, c2 = st.columns(2)
                with c1:
                    st.caption(p1)
                    for rm in p1_recent[:5]:
                        render_match_row_tennis(parse_tennis_match(rm))
                with c2:
                    st.caption(p2)
                    for rm in p2_recent[:5]:
                        render_match_row_tennis(parse_tennis_match(rm))
        else:
            st.info("H2H не е наличен.")

    # ── TAB 3: Bzzoiro ML ─────────────────────────────────────────
    with tabs[2]:
        bz = tennis_get_prediction(mid) if mid else {}
        if bz:
            p1_prob = bz.get("player1_probability") or bz.get("p1_win_prob") or bz.get("home_win_prob")
            p2_prob = bz.get("player2_probability") or bz.get("p2_win_prob") or bz.get("away_win_prob")
            conf    = bz.get("confidence", 0)

            if p1_prob and p2_prob:
                p1pct = int(float(p1_prob) * 100) if float(p1_prob) <= 1 else int(float(p1_prob))
                p2pct = 100 - p1pct
                st.markdown(f"""<div class="prob-bar">
                  <div style="flex:{p1pct};background:linear-gradient(135deg,#00d4aa,#0ea5e9);
                    display:flex;align-items:center;justify-content:center">
                    <span style="font-size:.9rem;font-weight:800;color:#0d1117">{p1pct}%</span>
                  </div>
                  <div style="flex:{p2pct};background:linear-gradient(135deg,#f59e0b,#ef4444);
                    display:flex;align-items:center;justify-content:center">
                    <span style="font-size:.9rem;font-weight:800;color:#0d1117">{p2pct}%</span>
                  </div>
                </div>
                <div style="display:flex;justify-content:space-between;
                  font-size:.72rem;color:#6b7280;margin-bottom:.8rem">
                  <span>🎾 {p1}</span><span>🎾 {p2}</span>
                </div>""", unsafe_allow_html=True)

            # Over/Under от Bzzoiro
            ou_keys = [
                ("over_20_5_games","Над 20.5"),("over_21_5_games","Над 21.5"),
                ("over_22_5_games","Над 22.5"),("over_2_5_sets","Над 2.5 сета"),
                ("p1_wins_first_set","P1 печели 1-ви сет"),
            ]
            ou_vals = [(lbl, bz.get(k)) for k,lbl in ou_keys if bz.get(k) is not None]
            if ou_vals:
                st.markdown('<div style="font-size:.7rem;font-weight:700;color:#4b5563;'
                            'text-transform:uppercase;letter-spacing:1px;margin:.6rem 0 .4rem">'
                            'Bzzoiro Over/Under</div>', unsafe_allow_html=True)
                cols = st.columns(len(ou_vals))
                for col,(lbl,val) in zip(cols, ou_vals):
                    pct = int(float(val)*100) if float(val)<=1 else int(float(val))
                    color = "#22c55e" if pct>=60 else "#f59e0b" if pct>=45 else "#6b7280"
                    col.markdown(f'<div style="background:#161b27;border:1px solid #1e2737;'
                                 f'border-radius:8px;padding:.5rem;text-align:center">'
                                 f'<div style="font-size:1rem;font-weight:800;color:{color}">{pct}%</div>'
                                 f'<div style="font-size:.6rem;color:#6b7280">{lbl}</div></div>',
                                 unsafe_allow_html=True)
            if conf:
                st.caption(f"Bzzoiro confidence: {conf}/100")
        else:
            st.info("Bzzoiro прогноза не е налична за този мач.")

# ── Rankings панел ────────────────────────────────────────────────
def render_rankings(circuit: str = "ATP"):
    rankings = tennis_get_rankings(circuit, limit=50)
    if not rankings:
        st.info(f"Ранглистата за {circuit} не е налична.")
        return
    st.markdown(f'<div style="font-size:.7rem;font-weight:700;color:#4b5563;'
                f'text-transform:uppercase;letter-spacing:1px;margin-bottom:.5rem">'
                f'{circuit} Ранглиста</div>', unsafe_allow_html=True)
    for r in rankings[:20]:
        player = r.get("player") or {}
        name   = player.get("name","?") if isinstance(player,dict) else str(player)
        pos    = r.get("position","")
        pts    = r.get("points","")
        prev   = r.get("previous_position") or r.get("prev_position")
        if prev and pos:
            try:
                delta = int(prev) - int(pos)
                mv_color = "#22c55e" if delta > 0 else "#ef4444" if delta < 0 else "#6b7280"
                mv = f'<span class="rank-mv" style="color:{mv_color}">{"▲" if delta>0 else "▼" if delta<0 else "–"}{abs(delta) if delta else ""}</span>'
            except: mv = ""
        else: mv = ""
        st.markdown(f'<div class="rank-row"><span class="rank-pos">#{pos}</span>'
                    f'<span class="rank-name">{name}</span>'
                    f'<span class="rank-pts">{pts} pts</span>{mv}</div>',
                    unsafe_allow_html=True)

# ── Главна функция ────────────────────────────────────────────────
def render_tennis_tab():
    st.markdown(TENNIS_CSS, unsafe_allow_html=True)

    # Sub-tabs
    sub = st.tabs(["📅 Програма", "⚡ На Живо", "🏆 Ранглиста", "🔮 Прогнози"])

    # ── Програма ─────────────────────────────────────────────────
    with sub[0]:
        c1, c2, c3 = st.columns([2,2,2])
        sel_date = c1.date_input("Дата", value=date.today(), key="t_date")
        circuit  = c2.selectbox("Тур", ["Всички","ATP","WTA"], key="t_circ")
        n_days   = c3.selectbox("Период", [1,3,7], format_func=lambda x: f"{x} {'ден' if x==1 else 'дни'}", key="t_nd")

        d_from = sel_date.isoformat()
        d_to   = (sel_date + timedelta(days=n_days-1)).isoformat()
        circ_p = None if circuit == "Всички" else circuit

        with st.spinner("Зареждане на мачове…"):
            matches = tennis_get_matches(d_from, d_to, circuit=circ_p, limit=150)

        if not matches:
            st.info("Няма намерени мачове за избрания период.")
        else:
            parsed = [parse_tennis_match(m) for m in matches]
            # Групиране по турнир
            by_tourn: Dict[str, List] = {}
            for tm in parsed:
                by_tourn.setdefault(tm["tournament"] or "Без турнир", []).append(tm)

            for tourn, tms in by_tourn.items():
                surf = tms[0]["surface"]
                st.markdown(f'<div style="display:flex;align-items:center;gap:.5rem;'
                            f'font-size:.72rem;font-weight:700;color:#9ca3af;'
                            f'text-transform:uppercase;letter-spacing:1px;'
                            f'margin:1rem 0 .4rem;border-bottom:1px solid #1e2737;'
                            f'padding-bottom:.4rem">{tourn} {_surf_badge(surf)}</div>',
                            unsafe_allow_html=True)
                for tm in tms:
                    render_match_row_tennis(tm)
                    if tm["id"]:
                        with st.expander(f"🎾 {tm['p1_name']} vs {tm['p2_name']} — детайли", expanded=False):
                            render_match_detail_tennis(tm)

    # ── На Живо ──────────────────────────────────────────────────
    with sub[1]:
        if st.button("🔄 Обнови", key="t_refresh"):
            st.cache_data.clear()

        with st.spinner("Зареждане на живи мачове…"):
            live = tennis_get_live()

        if not live:
            st.info("Няма живи мачове в момента.")
        else:
            st.markdown(f'<div style="font-size:.8rem;color:#ef4444;font-weight:700;'
                        f'margin-bottom:.8rem">● {len(live)} мача на живо</div>',
                        unsafe_allow_html=True)
            for m in live:
                tm = parse_tennis_match(m)
                render_match_row_tennis(tm)
                if tm["id"]:
                    with st.expander(f"🎾 {tm['p1_name']} vs {tm['p2_name']} — детайли", expanded=False):
                        render_match_detail_tennis(tm)

    # ── Ранглиста ─────────────────────────────────────────────────
    with sub[2]:
        c1, c2 = st.columns(2)
        with c1:
            render_rankings("ATP")
        with c2:
            render_rankings("WTA")

    # ── Прогнози ──────────────────────────────────────────────────
    with sub[3]:
        circ_pred = st.selectbox("Тур", ["ATP","WTA"], key="t_pred_circ")
        with st.spinner("Зареждане на прогнози…"):
            preds = tennis_get_upcoming_predictions(circuit=circ_pred, limit=30)

        if not preds:
            st.info("Няма налични прогнози.")
        else:
            for p in preds:
                # Parse match from prediction
                m_data = p.get("match") or p
                tm = parse_tennis_match(m_data)
                p1p = p.get("player1_probability") or p.get("p1_win_prob", 0.5)
                p2p = 1 - float(p1p) if float(p1p) <= 1 else 1 - float(p1p)/100
                p1pct = int(float(p1p)*100) if float(p1p)<=1 else int(float(p1p))
                p2pct = 100-p1pct
                conf  = p.get("confidence", 0)
                conf_color = "#22c55e" if conf>=70 else "#f59e0b" if conf>=50 else "#6b7280"

                st.markdown(f'''<div style="background:#161b27;border:1px solid #1e2737;
                  border-radius:10px;padding:.7rem 1rem;margin-bottom:.5rem">
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.4rem">
                    <span style="font-size:.72rem;color:#6b7280">{tm["tournament"][:30]}</span>
                    {_surf_badge(tm["surface"])}
                    <span style="font-size:.72rem;font-weight:700;color:{conf_color}">Conf: {conf}</span>
                  </div>
                  <div style="display:flex;align-items:center;gap:.5rem">
                    <span style="font-size:.88rem;font-weight:700;color:#e2e8f0;flex:1;text-align:right">
                      {tm["p1_name"]}</span>
                    <div style="display:flex;gap:2px;min-width:80px;height:26px">
                      <div style="flex:{p1pct};background:#00d4aa;border-radius:4px 0 0 4px;
                        display:flex;align-items:center;justify-content:center">
                        <span style="font-size:.72rem;font-weight:800;color:#0d1117">{p1pct}%</span></div>
                      <div style="flex:{p2pct};background:#f59e0b;border-radius:0 4px 4px 0;
                        display:flex;align-items:center;justify-content:center">
                        <span style="font-size:.72rem;font-weight:800;color:#0d1117">{p2pct}%</span></div>
                    </div>
                    <span style="font-size:.88rem;font-weight:700;color:#e2e8f0;flex:1">
                      {tm["p2_name"]}</span>
                  </div>
                </div>''', unsafe_allow_html=True)
