"""Dark-theme visuals: animated conflict graph + timetable grid per algorithm, benchmark charts.

Every slot has ONE colour, used for graph nodes, timetable rows and the legend.
"""
from collections import Counter
from math import ceil

import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.colors import hsv_to_rgb
from matplotlib.patches import Patch, Rectangle

BG, PANEL, INK, MUTED = "#0b1220", "#131c2f", "#e8edf7", "#8b97ad"
EMPTY, IDLE_EDGE, DARK = "#26324d", "#4a5878", "#0b1220"
PALETTE = ["#4dd0e1", "#ff6b8b", "#ffd166", "#7bdc8c", "#b794f6", "#ff9f5a",
           "#5aa9ff", "#f2a1e8", "#c3e66b", "#2ec4b6", "#ff8a80", "#cfd8dc"]
ALGO_STYLE = {"DSatur": ("#4dd0e1", "o"), "Welsh-Powell": ("#ffd166", "s"), "Exact B&B": ("#ff6b8b", "D")}


def slot_color(slot):
    if slot < len(PALETTE):
        return PALETTE[slot]
    return hsv_to_rgb(((slot * 0.61803398875) % 1.0, 0.55, 0.95))


# ------------------------------------------------------------------ helpers
def _network(graph):
    net = nx.Graph()
    net.add_nodes_from(range(graph.n))
    net.add_edges_from(graph.edges)
    return net


def _layout(net, n):
    if n == 1:
        return {0: (0.0, 0.0)}
    if n > 300:
        return nx.circular_layout(net)
    return nx.spring_layout(net, seed=7, iterations=120)


def _positions(assignment):
    """course -> (slot, hall). Courses in a slot are listed by id, exactly like the CSV."""
    slots = [[] for _ in range(max(assignment) + 1)]
    for course, slot in enumerate(assignment):
        slots[slot].append(course)
    return {c: (s, h) for s, members in enumerate(slots) for h, c in enumerate(members)}


def _columns(graph, assignment):
    cols = min(graph.capacity, graph.n)
    return cols if cols <= 12 else max(Counter(assignment).values())


def _status(result):
    if result["proven_optimal"]:
        why = "lower bound met" if result["slots"] == result["lower_bound"] else "search exhausted"
        return f"proven optimal ({why})"
    if result.get("timed_out"):
        return "time limit hit - best found"
    return f"not proven optimal (bound {result['lower_bound']})"


def _style_axis(ax, title, xlabel, ylabel):
    ax.set_facecolor(PANEL)
    ax.set_title(title, loc="left", color=INK, fontsize=12, fontweight="bold")
    ax.set_xlabel(xlabel, color=MUTED)
    ax.set_ylabel(ylabel, color=MUTED)
    ax.tick_params(colors=MUTED)
    ax.grid(color="#222d46", linewidth=.8)
    for spine in ax.spines.values():
        spine.set_visible(False)


# -------------------------------------------------------------------- panel
class _Panel:
    """One algorithm: coloured conflict graph (left) + timetable grid (right)."""

    def __init__(self, graph, result, ax_graph, ax_grid, net, layout):
        self.n, self.result = graph.n, result
        self.order = list(result["order"])
        self.assign = result["assignment"]
        self.rank = {c: i for i, c in enumerate(self.order)}
        self.pos = _positions(self.assign)
        slots, n = result["slots"], graph.n
        name = result["name"]

        # --- conflict graph
        ax_graph.set_facecolor(PANEL)
        ax_graph.set_xticks([]); ax_graph.set_yticks([])
        for spine in ax_graph.spines.values():
            spine.set_visible(False)
        nx.draw_networkx_edges(net, layout, ax=ax_graph, edge_color="#3d4d6e",
                               width=1.1 if n <= 60 else .5, alpha=.85)
        size = max(120, min(900, 18000 / max(n, 1)))
        self.nodes = nx.draw_networkx_nodes(net, layout, ax=ax_graph, node_color=[EMPTY] * n, node_size=size,
                                            edgecolors=IDLE_EDGE, linewidths=1.5)
        self.labels = {}
        if n <= 80:
            self.labels = nx.draw_networkx_labels(net, layout, ax=ax_graph, labels={v: str(v + 1) for v in range(n)},
                                                  font_size=max(6, 11 - n // 12), font_weight="bold", font_color=MUTED)
        ax_graph.margins(.1)
        color = ALGO_STYLE.get(name, (INK,))[0]
        ax_graph.set_title(f"{name}  |  {slots} slots  |  {result['seconds'] * 1000:.3f} ms",
                           loc="left", color=color, fontsize=12, fontweight="bold")
        ax_graph.text(.015, .965, _status(result), transform=ax_graph.transAxes, color=MUTED, fontsize=8, va="top")
        self.note = ax_graph.text(.985, .965, "", transform=ax_graph.transAxes, color=INK, fontsize=8,
                                  va="top", ha="right")
        if slots <= 24:
            ax_graph.legend(handles=[Patch(facecolor=slot_color(s), label=f"Slot {s + 1}") for s in range(slots)],
                            loc="lower center", ncol=min(8, slots), frameon=False, labelcolor=INK, fontsize=7,
                            bbox_to_anchor=(.5, -.01))

        # --- timetable grid
        cols = _columns(graph, self.assign)
        ax_grid.set_facecolor(PANEL)
        ax_grid.set_xlim(0, cols); ax_grid.set_ylim(slots, 0)
        self.rects = {}
        for s in range(slots):
            for h in range(cols):
                rect = Rectangle((h, s), 1, 1, facecolor=EMPTY, edgecolor=PANEL, linewidth=2.5)
                ax_grid.add_patch(rect)
                self.rects[(s, h)] = rect
        fs = max(5, min(11, 160 / max(slots, cols, 1)))
        self.texts = {c: ax_grid.text(h + .5, s + .5, "", ha="center", va="center", fontsize=fs,
                                      fontweight="bold", color=DARK) for c, (s, h) in self.pos.items()}
        ax_grid.set_yticks([s + .5 for s in range(slots)])
        ax_grid.set_yticklabels([f"Slot {s + 1}" for s in range(slots)], fontsize=8)
        for label, s in zip(ax_grid.get_yticklabels(), range(slots)):
            label.set_color(slot_color(s))
        if cols <= 12:
            ax_grid.set_xticks([h + .5 for h in range(cols)])
            ax_grid.set_xticklabels([f"Hall {h + 1}" for h in range(cols)], fontsize=7, color=MUTED)
        else:
            ax_grid.set_xticks([])
        ax_grid.tick_params(length=0)
        for spine in ax_grid.spines.values():
            spine.set_visible(False)
        ax_grid.set_title(f"Timetable  (R = {graph.capacity} exams per slot)", loc="left", color=INK,
                          fontsize=11, fontweight="bold")

    def update(self, step):
        current = self.order[step - 1] if 0 < step < self.n else None
        faces, edges, widths = [], [], []
        for c in range(self.n):
            done = self.rank[c] < step
            faces.append(slot_color(self.assign[c]) if done else EMPTY)
            edges.append("white" if c == current else IDLE_EDGE)
            widths.append(3.2 if c == current else 1.5)
            if c in self.labels:
                self.labels[c].set_color(DARK if done else MUTED)
            s, h = self.pos[c]
            self.rects[(s, h)].set_facecolor(slot_color(s) if done else EMPTY)
            self.texts[c].set_text(str(c + 1) if done else "")
        self.nodes.set_facecolor(faces)
        self.nodes.set_edgecolor(edges)
        self.nodes.set_linewidth(widths)
        if step == 0:
            self.note.set_text("ready")
        elif step >= self.n:
            self.note.set_text(f"complete: {self.result['slots']} slots")
        else:
            self.note.set_text(f"step {step}/{self.n}: course {current + 1} -> Slot {self.assign[current] + 1}")


# ------------------------------------------------------------ schedule view
def show_schedule_comparison(graph, results, animate=True, show=True, save_png=None, save_gif=None, interval=450):
    """One row per algorithm. Animates course-by-course assignment, ends on the full schedules."""
    rows = len(results)
    fig, axes = plt.subplots(rows, 2, figsize=(14, 4.4 * rows), facecolor=BG, squeeze=False,
                             gridspec_kw={"width_ratios": [1.25, 1]})
    net = _network(graph)
    layout = _layout(net, graph.n)
    panels = [_Panel(graph, r, axes[i, 0], axes[i, 1], net, layout) for i, r in enumerate(results)]
    fig.suptitle(f"EXAM TIMETABLE SCHEDULING   N={graph.n} courses   M={len(graph.edges)} conflicts   "
                 f"R={graph.capacity} per slot   lower bound={results[-1]['lower_bound']}",
                 color=INK, fontsize=14, fontweight="bold")
    fig.text(.5, .008, "Same colour = same time slot in graph, timetable and legend. White ring = course just assigned.",
             ha="center", color=MUTED, fontsize=9)
    fig.tight_layout(rect=(0, .025, 1, .96))

    n = graph.n
    stride = max(1, ceil(n / 90))
    frames = ceil(n / stride) + 6          # + hold on the finished timetable

    def draw(frame):
        for panel in panels:
            panel.update(min(n, frame * stride))
        return []

    def make_anim():
        return FuncAnimation(fig, draw, frames=frames, init_func=lambda: draw(0), interval=interval, repeat=False)

    if save_gif:
        make_anim().save(str(save_gif), writer=PillowWriter(fps=max(1, round(1000 / interval))), dpi=70,
                         savefig_kwargs={"facecolor": BG})
    draw(frames)
    if save_png:
        fig.savefig(str(save_png), dpi=150, facecolor=BG)
    if show:
        if animate:
            anim = make_anim()      # keep a reference, otherwise it is garbage collected
            plt.show()
            del anim
        else:
            plt.show()
    plt.close(fig)


# ---------------------------------------------------------------- benchmark
def show_benchmark_chart(rows, density, capacity, save_path=None, show=True):
    """rows: [{'n', 'slots': {algo: avg}, 'time': {algo: avg seconds}, 'lower': avg, 'timeouts': int}]."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.6), facecolor=BG)
    sizes = [r["n"] for r in rows]
    _style_axis(ax1, "Slots used", "Number of courses (N)", "Time slots")
    _style_axis(ax2, "Running time (log scale)", "Number of courses (N)", "Milliseconds")
    for name, (color, marker) in ALGO_STYLE.items():
        ax1.plot(sizes, [r["slots"][name] for r in rows], marker=marker, color=color, lw=2.4, label=name)
        ax2.plot(sizes, [max(r["time"][name] * 1000, 1e-3) for r in rows], marker=marker, color=color, lw=2.4,
                 label=name)
    ax1.plot(sizes, [r["lower"] for r in rows], "--", color=MUTED, lw=1.6, label="Lower bound")
    hit = [r for r in rows if r["timeouts"]]
    if hit:
        ax2.scatter([r["n"] for r in hit], [max(r["time"]["Exact B&B"] * 1000, 1e-3) for r in hit],
                    marker="x", s=130, color="white", zorder=6, label="Exact hit time limit")
    ax2.set_yscale("log")
    for ax in (ax1, ax2):
        ax.legend(frameon=False, labelcolor=INK)
    fig.suptitle(f"ALGORITHM COMPARISON   random conflict density {density:.2f}   R={capacity}",
                 color=INK, fontsize=14, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, .93))
    if save_path:
        fig.savefig(str(save_path), dpi=150, facecolor=BG)
    if show:
        plt.show()
    plt.close(fig)
