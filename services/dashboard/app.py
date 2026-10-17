"""Streamlit dashboard. Run: make dashboard  (needs the API running: make api)."""

import pandas as pd
import streamlit as st

from football_dashboard.client import ApiClient, ApiError
from football_dashboard.pitch import shot_map

st.set_page_config(page_title="Football Analytics", page_icon="⚽", layout="wide")

api = ApiClient.from_env()


@st.cache_data(ttl=600, show_spinner=False)
def load_teams() -> list[dict]:
    return api.teams(limit=100)


@st.cache_data(ttl=600, show_spinner=False)
def load_matches() -> list[dict]:
    return api.all_matches()


st.title("⚽ Football Analytics")
st.caption(
    "Historical data: StatsBomb Open Data (c) StatsBomb. Predictions are statistical estimates, "
    "not betting advice."
)

try:
    teams = load_teams()
    matches = load_matches()
except ApiError as exc:
    st.error(str(exc))
    st.stop()

team_by_name = {t["team_name"]: t["team_key"] for t in teams}
tab_form, tab_shots, tab_players, tab_pred = st.tabs(
    ["Team form", "Match shots", "Player comparison", "Prediction"]
)

with tab_form:
    col_a, col_b = st.columns([2, 1])
    name = col_a.selectbox("Team", sorted(team_by_name), key="form_team")
    last = col_b.slider("Last matches", 1, 10, 5)
    form = api.team_form(team_by_name[name], last)
    s = form["summary"]
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Record (W-D-L)", f"{s['wins']}-{s['draws']}-{s['losses']}")
    m2.metric("Points", s["points"])
    m3.metric("Goals", f"{s['goals_for']}:{s['goals_against']}")
    m4.metric("xG for", s["xg_for"])
    m5.metric("xG against", s["xg_against"])
    df = pd.DataFrame(form["matches"])
    if not df.empty:
        chart = df.set_index("match_date")[["xg_for", "xg_against"]].sort_index()
        st.bar_chart(chart)
        st.dataframe(
            df[
                [
                    "match_date",
                    "opponent",
                    "result",
                    "goals_for",
                    "goals_against",
                    "xg_for",
                    "xg_against",
                ]
            ],
            hide_index=True,
            use_container_width=True,
        )

with tab_shots:
    label = lambda m: (  # noqa: E731
        f"{m['match_date']}  {m['home_team']} {m['home_score']}-{m['away_score']} {m['away_team']}"
        f"  ({m['stage_name']})"
    )
    chosen = st.selectbox(
        "Match", sorted(matches, key=lambda m: m["match_date"], reverse=True), format_func=label
    )
    shootout = st.checkbox("Include penalty shootout", value=False)
    data = api.match_shots(chosen["match_key"], shootout)
    c1, c2 = st.columns(2)
    c1.metric(f"xG {chosen['home_team']}", data["total_xg_home"])
    c2.metric(f"xG {chosen['away_team']}", data["total_xg_away"])
    st.pyplot(shot_map(data["shots"], label(chosen)))
    st.caption("Circle size = xG. Stars are goals. Each team is drawn attacking its own goal.")

with tab_players:
    c1, c2 = st.columns(2)
    picked = []
    for col, key in ((c1, "p1"), (c2, "p2")):
        q = col.text_input("Search player", key=f"q_{key}", placeholder="e.g. Messi")
        options = api.players(q) if len(q) >= 2 else []
        choice = (
            col.selectbox("Player", options, format_func=lambda p: p["player_name"], key=f"s_{key}")
            if options
            else None
        )
        picked.append(choice)
    if all(picked) and picked[0]["player_key"] != picked[1]["player_key"]:
        try:
            cmp_ = api.compare_players(picked[0]["player_key"], picked[1]["player_key"])
            table = (
                pd.DataFrame(cmp_["players"]).set_index("player_name").drop(columns="player_key").T
            )
            st.dataframe(table, use_container_width=True)
        except ApiError as exc:
            st.warning(str(exc))
    else:
        st.info("Search and pick two different players.")

with tab_pred:
    c1, c2 = st.columns(2)
    home = c1.selectbox("Team A", sorted(team_by_name), key="pred_home")
    away = c2.selectbox("Team B", sorted(team_by_name), index=1, key="pred_away")
    if home == away:
        st.info("Pick two different teams.")
    else:
        try:
            out = api.predict(team_by_name[home], team_by_name[away])
            p = out["probabilities"]
            st.bar_chart(
                pd.Series(
                    {f"{home} win": p["home_win"], "Draw": p["draw"], f"{away} win": p["away_win"]}
                )
            )
            st.caption(
                f"Model: {out['model']['name']} · trained on {out['model']['training_matches']} "
                f"matches up to {out['model']['data_cutoff']} · walk-forward log-loss "
                f"{out['model']['walk_forward_log_loss']}"
            )
            st.warning(out["disclaimer"])
        except ApiError as exc:
            st.warning(str(exc))
