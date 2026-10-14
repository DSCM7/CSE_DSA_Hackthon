"""Interactive Matplotlib visualisation of the Keys-and-Doors maze.

What you see
  * white = open, black = wall, green = start, red = exit, and every key/door pair
    has its own colour (keys are round badges, doors carry a padlock);
  * the shortest route is tinted on the board and a purple trail follows the runner;
  * picking up a key makes its tile fade out and ticks the KEY RING panel;
  * walking into a door turns it white and its padlock swings open.

Controls: Play/Pause, Restart, step back / forward, speed slider.
Keyboard: SPACE play/pause, LEFT / RIGHT step, R restart.
"""
from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, field

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.collections import PatchCollection
from matplotlib.colors import to_rgb
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Ellipse, FancyBboxPatch, Rectangle

from maze_solver import DOOR_LETTERS, KEY_LETTERS, describe_route

# Pair colours avoid green (start), red (exit), white (open) and black (wall).
PAIR_COLORS = {"a": "#f2b705", "b": "#2f80ed", "c": "#9b51e0",
               "d": "#ff7a2f", "e": "#f472b6", "f": "#8d5a3b"}
WALL, OPEN, PATH = "#1f2937", "#ffffff", "#e6e0fd"
START, EXIT, TRAIL = "#2ea66a", "#e5484d", "#6d4fd8"
INK, MUTED, BG, GOOD = "#1f2a3c", "#6b7a90", "#eaf0f8", "#168452"
UNREACHED = "#fde8e9"
GRID_LINE = "#cfd7e4"


def _mix(a, b, t):
    a, b = to_rgb(a), to_rgb(b)
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def _text_on(color):
    r, g, b = to_rgb(color)
    return "white" if .299 * r + .587 * g + .114 * b < .55 else INK


def _lock_shape(cx, cy, s, opened):
    """Padlock geometry (y axis points down).  Returns body rectangle + shackle polyline."""
    radius, leg, lift = .17 * s, .08 * s, .11 * s
    arc = [(cx + radius * math.cos(math.pi - math.pi * k / 14),
            cy - leg - radius * math.sin(math.pi - math.pi * k / 14)) for k in range(15)]
    if opened:
        line = [(cx - radius, cy)] + [(x, y - lift) for x, y in arc]
    else:
        line = [(cx - radius, cy)] + arc + [(cx + radius, cy)]
    body = (cx - .27 * s, cy, .54 * s, .38 * s)
    return body, line


@dataclass
class Frame:
    x: float
    y: float
    step: int
    trail: int
    message: str
    held: frozenset
    keys_fade: dict = field(default_factory=dict)     # (r, c) -> 0..1 how far a key tile has faded
    doors_open: dict = field(default_factory=dict)    # (r, c) -> 0..1 how far a door has opened


def build_frames(maze, route, steps):
    """Timeline: short interpolated moves plus slower pick-up / unlock beats."""
    sub = 4 if len(route) <= 60 else 3 if len(route) <= 140 else 2
    frames, arrival = [], {0: 0}
    held, keys_fade, doors_open = set(), {}, {}

    def add(x, y, step, message, trail):
        frames.append(Frame(x, y, step, trail, message, frozenset(held), dict(keys_fade), dict(doors_open)))

    add(route[0][1] + .5, route[0][0] + .5, 0, "Ready", 0)
    for i in range(1, len(route)):
        (pr, pc), (r, c), ev = route[i - 1], route[i], steps[i]
        for k in range(1, sub + 1):
            t = k / sub
            x, y = pc + .5 + (c - pc) * t, pr + .5 + (r - pr) * t
            if k < sub:
                add(x, y, i - 1, "Following the shortest route", i - 1)
                continue
            if ev.kind == "key":
                held.add(ev.symbol)
                keys_fade[(r, c)] = 0.0
            elif ev.kind == "door":
                doors_open[(r, c)] = 0.0
            add(x, y, i, ev.note or "Following the shortest route", i)
            arrival[i] = len(frames) - 1
        if ev.kind in ("key", "door"):
            target = keys_fade if ev.kind == "key" else doors_open
            for amount in (.25, .5, .75, 1.0):
                target[(r, c)] = amount
                add(c + .5, r + .5, i, ev.note, i)
    last = len(route) - 1
    for _ in range(8):
        add(route[-1][1] + .5, route[-1][0] + .5, last, "Escaped!", last)
    return frames, arrival


class MazeView:
    def __init__(self, maze, route, stats=None, visited=None, controls=True):
        self.maze, self.stats, self.visited = maze, stats or [], visited or frozenset()
        self.solved = route is not None
        self.route = list(route) if route else [maze.start]
        self.steps = describe_route(maze, self.route)
        self.frames, self.arrival = build_frames(maze, self.route, self.steps)
        self.n = maze.size
        self.types = sorted(set(maze.keys) | set(maze.doors))
        self.pos, self.speed, self.playing, self._shown = 0.0, 1.0, self.solved, None
        self._build_figure(controls)
        self.render(0)

    # ------------------------------------------------------------------ figure
    def _build_figure(self, controls):
        n, maze = self.n, self.maze
        self.fig = plt.figure(figsize=(12.8, 8.0), facecolor=BG)
        try:
            self.fig.canvas.manager.set_window_title("Maze with Keys and Doors")
        except Exception:
            pass
        self.ax = self.fig.add_axes([.035, .165, .655, .73], facecolor=BG)
        self.panel = self.fig.add_axes([.715, .06, .265, .88])
        self.panel_aspect = (.265 * 12.8) / (.88 * 8.0)
        self.panel.set_xlim(0, 1)
        self.panel.set_ylim(0, 1)
        self.panel.axis("off")

        self.fig.text(.04, .965, "Maze with Keys and Doors", fontsize=20, fontweight="bold",
                      color=INK, va="center", ha="left")
        self.fig.text(.04, .93, f"{n} x {n} grid   |   {len(self.types)} key/door pair"
                      f"{'s' if len(self.types) != 1 else ''}   |   BFS over (cell, key set) states",
                      fontsize=10, color=MUTED, va="center", ha="left")

        ax = self.ax
        ax.set_xlim(0, n)
        ax.set_ylim(n, 0)
        ax.set_aspect("equal")
        every = 1 if n <= 20 else 2 if n <= 40 else 5
        ticks = [i for i in range(n) if i % every == 0 or i == n - 1]
        ax.set_xticks([i + .5 for i in ticks])
        ax.set_yticks([i + .5 for i in ticks])
        ax.set_xticklabels([str(i + 1) for i in ticks], fontsize=8, color=MUTED)
        ax.set_yticklabels([str(i + 1) for i in ticks], fontsize=8, color=MUTED)
        ax.tick_params(length=0, pad=4)
        for spine in ax.spines.values():
            spine.set_visible(False)

        route_cells = set(self.route) if self.solved else set()
        font = max(7, min(17, 230 / n))
        self.font = font
        static_patches, static_colors = [], []
        self.key_art, self.door_art = {}, {}

        def tile(r, c, color, zorder=1):
            return FancyBboxPatch((c + .04, r + .04), .92, .92, boxstyle="round,pad=0.0,rounding_size=0.1",
                                  linewidth=0.9, edgecolor=GRID_LINE, facecolor=color, zorder=zorder)

        for r, row in enumerate(maze.grid):
            for c, sym in enumerate(row):
                pos = (r, c)
                if sym in KEY_LETTERS or (sym in DOOR_LETTERS and pos != maze.exit):
                    color = PAIR_COLORS[sym.lower()]
                    patch = tile(r, c, color)
                    ax.add_patch(patch)
                    if sym in KEY_LETTERS:
                        dark = _mix(color, INK, .45)
                        badge = Circle((c + .5, r + .5), .31, facecolor="white", edgecolor=dark,
                                       linewidth=1.6, zorder=3)
                        ax.add_patch(badge)
                        text = ax.text(c + .5, r + .52, sym, ha="center", va="center", fontsize=font,
                                       fontweight="bold", color=dark, zorder=4)
                        self.key_art[pos] = dict(tile=patch, badge=badge, text=text, color=color)
                    else:
                        text = ax.text(c + .40, r + .60, sym, ha="center", va="center", fontsize=font,
                                       fontweight="bold", color=_text_on(color), zorder=4)
                        body = Rectangle((0, 0), 1, 1, zorder=9)
                        shackle = Line2D([], [], linewidth=2.0, solid_capstyle="round", zorder=9)
                        ax.add_patch(body)
                        ax.add_line(shackle)
                        self.door_art[pos] = dict(tile=patch, text=text, body=body, shackle=shackle,
                                                  color=color, lock_color=_text_on(color),
                                                  cx0=c + .76, cy0=r + .22, cx1=c + .5, cy1=r + .3)
                    continue
                if sym == "#":
                    color = WALL
                elif pos == maze.start:
                    color = START
                elif pos == maze.exit:
                    color = EXIT
                elif pos in route_cells:
                    color = PATH
                elif not self.solved and pos in self.visited:
                    color = UNREACHED
                else:
                    color = OPEN
                static_patches.append(tile(r, c, color))
                static_colors.append(color)
                if pos in (maze.start, maze.exit):
                    ax.text(c + .5, r + .52, sym, ha="center", va="center", fontsize=font * 1.05,
                            fontweight="bold", color="white", zorder=4)
        ax.add_collection(PatchCollection(static_patches, match_original=True, zorder=1))

        if self.solved and len(self.route) > 1:
            ax.plot([c + .5 for _, c in self.route], [r + .5 for r, _ in self.route], color=TRAIL,
                    linewidth=1.6, alpha=.22, linestyle=(0, (2, 3)), zorder=2)
        self.trail, = ax.plot([], [], color=TRAIL, linewidth=max(3.0, 11 / n * 3), alpha=.92,
                              solid_capstyle="round", solid_joinstyle="round", zorder=6)
        self.glow, = ax.plot([], [], marker="o", markersize=max(14, 30 - n / 2),
                             markerfacecolor=(.43, .31, .85, .22), markeredgecolor="none",
                             linestyle="None", zorder=7)
        self.player, = ax.plot([], [], marker="o", markersize=max(8, 15 - n / 6), markerfacecolor="white",
                               markeredgecolor=TRAIL, markeredgewidth=3, linestyle="None", zorder=8)

        self._build_panel()
        if controls:
            self._build_controls()

    def _build_panel(self):
        p = self.panel
        p.add_patch(FancyBboxPatch((0, 0), 1, 1, transform=p.transAxes, boxstyle="round,pad=0.0,rounding_size=0.03",
                                   facecolor="white", edgecolor="#d5dce8", linewidth=1.2, zorder=0))
        p.text(.07, .955, "Live solver", fontsize=14, fontweight="bold", color=INK, va="center")
        self.action = p.text(.07, .915, "", fontsize=11, fontweight="bold", color=TRAIL, va="center")
        self.step_text = p.text(.07, .878, "", fontsize=9, color=MUTED, va="center")
        p.add_patch(Rectangle((.07, .835), .86, .018, facecolor="#edf0f7", edgecolor="none"))
        self.progress = Rectangle((.07, .835), 0, .018, facecolor=TRAIL, edgecolor="none")
        p.add_patch(self.progress)

        total = len(self.types)
        self.stat_texts = {}
        for i, (name, init) in enumerate((("Shortest path", f"{len(self.route) - 1} moves" if self.solved else "none"),
                                          ("Keys collected", f"0 / {total}"),
                                          ("Doors opened", f"0 / {total}"))):
            y = .785 - i * .036
            p.text(.07, y, name, fontsize=9, color=MUTED, va="center")
            self.stat_texts[name] = p.text(.93, y, init, fontsize=10, fontweight="bold", color=INK,
                                           va="center", ha="right")

        p.text(.07, .655, "Key ring", fontsize=10, fontweight="bold", color=INK, va="center")
        self.chips = {}
        for i, letter in enumerate(self.types):
            y = .615 - i * .036
            color = PAIR_COLORS[letter]
            chip = Ellipse((.115, y), .05, .05 * self.panel_aspect, facecolor="white", edgecolor=color,
                           linewidth=2.2)
            p.add_patch(chip)
            label = p.text(.175, y, "", fontsize=9, va="center", color=INK)
            self.chips[letter] = (chip, label, color)

        guide_y = .615 - max(0, len(self.types) - 1) * .036 - .05
        p.text(.07, guide_y, "Cell guide", fontsize=10, fontweight="bold", color=INK, va="center")
        entries = [(OPEN, "Open"), (WALL, "Wall"), (START, "Start"), (EXIT, "Exit"), (PATH, "Route")]
        if not self.solved:
            entries.append((UNREACHED, "Reachable"))
        for i, (color, name) in enumerate(entries):
            x = .07 + (i % 2) * .45
            y = guide_y - .035 - (i // 2) * .033
            p.add_patch(FancyBboxPatch((x, y - .011), .045, .022, boxstyle="round,pad=0,rounding_size=0.006",
                                       facecolor=color, edgecolor=GRID_LINE, linewidth=.9))
            p.text(x + .06, y, name, fontsize=8.5, color=INK, va="center")

        if self.stats:
            base = guide_y - 3 * .033 - .075               # flows below the cell guide, whatever T is
            p.text(.07, base, "Algorithm comparison", fontsize=10, fontweight="bold", color=INK, va="center")
            p.text(.07, base - .03, f"{'':<9}{'states':>8}{'ms':>9}", fontsize=8, color=MUTED, va="center",
                   family="monospace")
            for i, st in enumerate(self.stats):
                y = base - .058 - i * .029
                mark = "+" if st.capped else ""
                p.text(.07, y, f"{st.algorithm:<9}{st.expanded:>7,}{mark:1}{st.time_ms:>9.2f}", fontsize=8.5,
                       color=INK, va="center", family="monospace")
            p.text(.07, base - .058 - len(self.stats) * .029 - .002, "states = frontier pops (fewer is better)",
                   fontsize=7.3, color=MUTED, va="center")
        p.text(.07, .035, "Matching key and door share a colour.", fontsize=8, color=MUTED, va="center")

    def _build_controls(self):
        fig = self.fig
        from matplotlib.widgets import Button, Slider
        style = dict(color="white", hovercolor="#e8e4fb")
        self.btn_back = Button(fig.add_axes([.04, .045, .085, .055]), "◀  Step", **style)
        self.btn_play = Button(fig.add_axes([.135, .045, .115, .055]), "Pause" if self.playing else "Play", **style)
        self.btn_fwd = Button(fig.add_axes([.26, .045, .085, .055]), "Step  ▶", **style)
        self.btn_reset = Button(fig.add_axes([.355, .045, .085, .055]), "Restart", **style)
        for b in (self.btn_back, self.btn_play, self.btn_fwd, self.btn_reset):
            b.label.set_fontsize(10)
            b.label.set_color(INK)
            for spine in b.ax.spines.values():
                spine.set_edgecolor("#c3ccdc")
        self.slider = Slider(fig.add_axes([.54, .062, .14, .022]), "Speed ", .25, 4.0, valinit=1.0,
                             color=TRAIL, valfmt="%.2gx")
        self.slider.label.set_fontsize(10)
        self.slider.label.set_color(INK)
        self.slider.valtext.set_fontsize(9)
        self.btn_back.on_clicked(lambda _: self.step(-1))
        self.btn_fwd.on_clicked(lambda _: self.step(+1))
        self.btn_play.on_clicked(lambda _: self.toggle())
        self.btn_reset.on_clicked(lambda _: self.restart())
        self.slider.on_changed(lambda v: setattr(self, "speed", v))
        self.fig.canvas.mpl_connect("key_press_event", self._on_key)

    # ------------------------------------------------------------------ playback
    def _on_key(self, event):
        key = (event.key or "").lower()
        if key == " ":
            self.toggle()
        elif key == "right":
            self.step(+1)
        elif key == "left":
            self.step(-1)
        elif key == "r":
            self.restart()

    def toggle(self):
        if not self.solved:
            return
        if not self.playing and self.pos >= len(self.frames) - 1:
            self.pos = 0.0
        self.playing = not self.playing
        self._sync_button()

    def restart(self):
        self.pos, self.playing = 0.0, self.solved
        self._sync_button()
        self.render(0)

    def step(self, direction):
        """Jump to the next / previous completed move."""
        self.playing = False
        order = sorted(self.arrival)
        if direction > 0:
            target = next((k for k in order if self.arrival[k] > self.pos), order[-1])
        else:
            target = next((k for k in reversed(order) if self.arrival[k] < self.pos), 0)
        self.pos = float(self.arrival[target])
        self._sync_button()
        self.render(int(self.pos))
        self.fig.canvas.draw_idle()

    def _sync_button(self):
        if hasattr(self, "btn_play"):
            self.btn_play.label.set_text("Pause" if self.playing else
                                         "Replay" if self.pos >= len(self.frames) - 1 else "Play")
            self.fig.canvas.draw_idle()

    def tick(self, _):
        if self.playing:
            self.pos = min(self.pos + self.speed, len(self.frames) - 1)
            if self.pos >= len(self.frames) - 1:
                self.playing = False
                self._sync_button()
        idx = int(self.pos)
        if idx != self._shown:
            self.render(idx)
        return []

    # ------------------------------------------------------------------ drawing
    @staticmethod
    def _place_lock(art, a):
        """a = 0: small closed padlock in the corner.  a = 1: big open padlock, centred."""
        cx = art["cx0"] + (art["cx1"] - art["cx0"]) * a
        cy = art["cy0"] + (art["cy1"] - art["cy0"]) * a
        (x, y, w, h), line = _lock_shape(cx, cy, .66 + .3 * a, a >= .5)
        color = _mix(art["lock_color"], GOOD, a)
        art["body"].set_bounds(x, y, w, h)
        art["body"].set_facecolor(color)
        art["body"].set_edgecolor("none")
        art["shackle"].set_data([q[0] for q in line], [q[1] for q in line])
        art["shackle"].set_color(color)

    def render(self, i):
        self._shown = i
        f = self.frames[i]
        self.player.set_data([f.x], [f.y])
        self.glow.set_data([f.x], [f.y])
        busy = any(0 < a < 1 for a in (*f.keys_fade.values(), *f.doors_open.values()))
        self.player.set_visible(not busy)          # let the pick-up / unlock beat be seen
        self.glow.set_visible(not busy)
        self.glow.set_markersize(max(14, 30 - self.n / 2) + 3 * (i % 4) / 3)
        pts = self.route[:f.trail + 1]
        xs, ys = [c + .5 for _, c in pts], [r + .5 for r, _ in pts]
        if not xs or (f.x, f.y) != (xs[-1], ys[-1]):
            xs.append(f.x)
            ys.append(f.y)
        self.trail.set_data(xs, ys)

        for pos, art in self.key_art.items():
            a = f.keys_fade.get(pos, 0.0)
            art["tile"].set_facecolor(_mix(art["color"], OPEN, a))
            art["badge"].set_radius(max(.31 * (1 - a), 1e-6))
            art["badge"].set_alpha(1 - a)
            art["text"].set_alpha(1 - a)
        for pos, art in self.door_art.items():
            a = f.doors_open.get(pos, 0.0)
            art["tile"].set_facecolor(_mix(art["color"], OPEN, a))
            art["text"].set_alpha(1 - a)
            self._place_lock(art, a)

        done = f.message == "Escaped!"
        if not self.solved:
            self.action.set_text("No route to the exit")
            self.action.set_color(EXIT)
            self.step_text.set_text("The red tint marks every cell that can be reached")
        else:
            self.action.set_text(f.message)
            self.action.set_color(GOOD if (done or f.message.startswith(("Picked", "Opened"))) else TRAIL)
            self.step_text.set_text(f"Move {f.step} of {len(self.route) - 1}")
        self.progress.set_width(.86 * f.step / max(1, len(self.route) - 1) if self.solved else 0)
        total = len(self.types)
        self.stat_texts["Keys collected"].set_text(f"{len(f.held)} / {total}")
        self.stat_texts["Doors opened"].set_text(f"{len({self.maze.grid[r][c].lower() for (r, c) in f.doors_open})} / {total}")
        for letter, (chip, label, color) in self.chips.items():
            got = letter in f.held
            chip.set_facecolor(color if got else "white")
            label.set_text(f"{letter} / {letter.upper()}   " + ("collected" if got else "waiting"))
            label.set_color(INK if got else MUTED)

    # ------------------------------------------------------------------ output
    def save_png(self, path, frame=None):
        self.render(len(self.frames) - 1 if frame is None else frame)
        self.fig.savefig(path, dpi=140, facecolor=self.fig.get_facecolor())

    def save_gif(self, path, fps=15, max_frames=140):
        """Export the animation; long routes are sub-sampled to keep the file small."""
        for name in ("btn_back", "btn_play", "btn_fwd", "btn_reset"):
            if hasattr(self, name):
                getattr(self, name).ax.set_visible(False)
        if hasattr(self, "slider"):
            self.slider.ax.set_visible(False)
        stride = max(1, math.ceil(len(self.frames) / max_frames))
        picks = list(range(0, len(self.frames), stride))
        if picks[-1] != len(self.frames) - 1:
            picks.append(len(self.frames) - 1)
        anim = FuncAnimation(self.fig, lambda k: self.render(picks[k]), frames=len(picks))
        anim.save(path, writer=PillowWriter(fps=fps), dpi=70)

    def run(self):
        self.anim = FuncAnimation(self.fig, self.tick, frames=itertools.count(), interval=40,
                                  blit=False, cache_frame_data=False, save_count=len(self.frames))
        plt.show()
        return self.anim


def show_animation(maze, route, stats=None, visited=None):
    """Open the interactive window (route=None shows the maze with no solution)."""
    for key in ("keymap.back", "keymap.forward", "keymap.home", "keymap.save", "keymap.fullscreen"):
        plt.rcParams[key] = [k for k in plt.rcParams.get(key, []) if k not in ("left", "right", "r", "s", "f", " ")]
    view = MazeView(maze, route, stats=stats, visited=visited)
    view.run()
    return view
