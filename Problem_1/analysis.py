"""Comparative analysis for Problem 1.

    python analysis.py            full run (about a minute)
    python analysis.py --quick    smaller sizes, a few seconds
    python analysis.py --show     also open the chart window

It (1) cross-checks every algorithm on many random mazes, (2) measures how the
naive cell-only BFS fails, (3) benchmarks running time and expanded states against
the grid size N and the number of key types T, and (4) writes
output/benchmark.csv and output/analysis_benchmark.png.
"""
from __future__ import annotations

import argparse
import csv
import statistics
import sys
from pathlib import Path

from maze_solver import generate_maze, solve_astar, solve_bfs, solve_dfs, solve_key_graph, solve_naive

SOLVERS = {"BFS": solve_bfs, "A*": solve_astar, "DFS": lambda m: solve_dfs(m, cap=150_000)}
COLORS = {"BFS": "#6d4fd8", "A*": "#2ea66a", "DFS": "#ff7a2f"}


def say(text=""):
    print(text, file=sys.stderr)


def cross_check(count):
    """All optimal algorithms and the independent key-graph oracle must agree."""
    say(f"[1] Cross-check on {count} random mazes (BFS, A*, DFS, key-graph Dijkstra)")
    agree = naive_wrong = 0
    for i in range(count):
        t = 1 + i % 6
        n = t + 8 + (i % 5) * 2
        loops = 0.0 if i % 3 == 0 else 0.25
        maze = generate_maze(t, size=n, seed=1000 + i, loops=loops, strict=loops == 0.0)
        answers = {name: fn(maze).length for name, fn in SOLVERS.items()}
        answers["oracle"] = solve_key_graph(maze).length
        if len(set(answers.values())) != 1:
            say(f"    MISMATCH on seed {1000 + i}: {answers}")
            raise SystemExit(1)
        agree += 1
        if solve_naive(maze).length != answers["BFS"]:
            naive_wrong += 1
    say(f"    all {agree} mazes agree.  Naive cell-only BFS was wrong on {naive_wrong} of them "
        f"({100 * naive_wrong / count:.0f}%).")
    return agree, naive_wrong


def time_family(sizes, types, seeds, loops):
    rows = []
    for n in sizes:
        for t in types:
            samples = {name: [] for name in SOLVERS}
            for seed in range(seeds):
                maze = generate_maze(t, size=n, seed=seed, loops=loops, strict=False)
                lengths = set()
                for name, fn in SOLVERS.items():
                    r = fn(maze)
                    samples[name].append((r.time_ms, r.expanded, r.capped))
                    if not r.capped:
                        lengths.add(r.length)
                assert len(lengths) == 1, "algorithms disagree"
            for name, vals in samples.items():
                rows.append(dict(family="open" if loops else "tree", N=n, T=t, algorithm=name,
                                 time_ms=statistics.mean(v[0] for v in vals),
                                 states=statistics.mean(v[1] for v in vals),
                                 capped=sum(v[2] for v in vals)))
    return rows


def plot(rows, path, show):
    import matplotlib
    if not show:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(12.5, 8), facecolor="#eaf0f8")
    fig.suptitle("Maze with Keys and Doors: BFS vs A* vs DFS (open mazes, mean of several seeds)",
                 fontsize=14, fontweight="bold", color="#1f2a3c", x=.06, ha="left")
    spec = [("N", "time_ms", "Running time (ms)", "vs grid size N  (T = 3)", lambda r: r["T"] == 3),
            ("N", "states", "States expanded", "vs grid size N  (T = 3)", lambda r: r["T"] == 3),
            ("T", "time_ms", "Running time (ms)", "vs key types T  (N = largest)", None),
            ("T", "states", "States expanded", "vs key types T  (N = largest)", None)]
    big_n = max(r["N"] for r in rows if r["family"] == "open")
    for ax, (xkey, ykey, ylabel, title, keep) in zip(axes.flat, spec):
        ax.set_facecolor("white")
        for name in SOLVERS:
            pts = sorted((r[xkey], r[ykey]) for r in rows if r["family"] == "open" and r["algorithm"] == name
                         and (keep(r) if keep else r["N"] == big_n))
            ax.plot([p[0] for p in pts], [p[1] for p in pts], marker="o", linewidth=2.2, label=name,
                    color=COLORS[name])
        ax.set_yscale("log")
        ax.set_xlabel("grid size N" if xkey == "N" else "key types T")
        ax.set_ylabel(ylabel)
        ax.set_title(title, fontsize=11, loc="left", color="#1f2a3c")
        ax.grid(True, alpha=.25)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.legend(frameon=False)
    fig.tight_layout(rect=(0, 0, 1, .95))
    fig.savefig(path, dpi=140, facecolor=fig.get_facecolor())
    if show:
        plt.show()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--quick", action="store_true")
    p.add_argument("--show", action="store_true")
    p.add_argument("--out", default="output")
    args = p.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    cross_check(36 if args.quick else 120)

    sizes = [11, 17, 25, 33] if args.quick else [11, 17, 25, 33, 41, 51]
    seeds = 2 if args.quick else 4
    say("[2] Timing on open mazes (30% of interior walls removed) ...")
    rows = time_family(sizes, [3], seeds, 0.3)
    rows += time_family([sizes[-1]], [1, 2, 4, 5, 6], seeds, 0.3)
    say("[3] Timing on perfect (tree) mazes ...")
    rows += time_family(sizes, [3], seeds, 0.0)

    with (out / "benchmark.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows({**r, "time_ms": round(r["time_ms"], 3), "states": round(r["states"])} for r in rows)
    say(f"    wrote {out / 'benchmark.csv'}")

    say("")
    say(f"{'family':<7}{'N':>4}{'T':>3}  {'algorithm':<6}{'time ms':>10}{'states':>10}{'capped':>8}")
    for r in rows:
        say(f"{r['family']:<7}{r['N']:>4}{r['T']:>3}  {r['algorithm']:<6}{r['time_ms']:>10.2f}"
            f"{r['states']:>10,.0f}{r['capped']:>8}")
    plot(rows, out / "analysis_benchmark.png", args.show)
    say(f"\nChart saved to {out / 'analysis_benchmark.png'}")


if __name__ == "__main__":
    main()
