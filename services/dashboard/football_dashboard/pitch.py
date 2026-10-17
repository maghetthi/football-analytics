"""Shot map on a 120x80 StatsBomb pitch. Every shot is drawn attacking the same goal (right)."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.patches import Arc, Rectangle  # noqa: E402

PITCH_GREEN = "#2e7d32"


def _draw_pitch(ax) -> None:
    ax.set_facecolor(PITCH_GREEN)
    line = {"color": "white", "linewidth": 1.2, "fill": False}
    ax.add_patch(Rectangle((0, 0), 120, 80, **line))
    ax.plot([60, 60], [0, 80], color="white", linewidth=1.2)
    ax.add_patch(Arc((60, 40), 18.3, 18.3, **{k: v for k, v in line.items() if k != "fill"}))
    for x0 in (0, 102):  # penalty areas
        ax.add_patch(Rectangle((x0, 18), 18, 44, **line))
    for x0 in (0, 114):  # six-yard boxes
        ax.add_patch(Rectangle((x0, 30), 6, 20, **line))
    ax.set_xlim(-2, 122)
    ax.set_ylim(82, -2)  # StatsBomb y grows downwards
    ax.set_aspect("equal")
    ax.axis("off")


def shot_map(shots: list[dict], title: str = "") -> Figure:
    """Circle area ~ xG; goals are gold stars. Home and away shots are mirrored to one goal."""
    fig, ax = plt.subplots(figsize=(8, 5.4))
    _draw_pitch(ax)
    teams = sorted({s["team_name"] for s in shots})
    colors = dict(zip(teams, ("#ffffff", "#1565c0"), strict=False))
    for s in shots:
        if s["location_x"] is None:
            continue
        x, y = s["location_x"], s["location_y"]
        if teams and s["team_name"] == teams[-1] and len(teams) > 1:
            x, y = 120 - x, 80 - y  # second team attacks the left goal
        ax.scatter(
            x,
            y,
            s=60 + 900 * s["xg"],
            marker="*" if s["is_goal"] else "o",
            c="gold" if s["is_goal"] else colors.get(s["team_name"], "white"),
            edgecolors="black",
            alpha=0.9,
            zorder=3,
        )
    ax.set_title(title, color="black")
    fig.tight_layout()
    return fig
