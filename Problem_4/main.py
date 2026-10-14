"""Exam timetable scheduler: interactive menu, file/stdin input, random input, benchmark."""
import argparse
import csv
import sys
from pathlib import Path

from graph_input import load_edge_list, parse_edge_list, generate_random_graph, write_timetable_csv
from scheduler import dsatur, welsh_powell, exact_branch_and_bound, lower_bound_parts, validate
from visualization import show_schedule_comparison, show_benchmark_chart

SLUG = {"DSatur": "dsatur", "Welsh-Powell": "welsh_powell", "Exact B&B": "exact"}


def ask(prompt):
    print(prompt, end="", file=sys.stderr, flush=True)
    return input().strip()


# ------------------------------------------------------------------- inputs
def read_random_input(show_prompts=True, seed=None):
    """Option 2: first line 'N R', second line = edge density."""
    header = ask("Enter N R on one line: ") if show_prompts else input().strip()
    fields = header.split()
    if len(fields) != 2:
        raise ValueError("Random input's first line must be: N R")
    try:
        n, capacity = map(int, fields)
    except ValueError as exc:
        raise ValueError("N and R must be integers.") from exc
    text = ask("Enter edge density (0.0 to 1.0): ") if show_prompts else input().strip()
    try:
        density = float(text)
    except ValueError as exc:
        raise ValueError("Edge density must be a number from 0.0 to 1.0.") from exc
    return generate_random_graph(n, capacity, density, seed=seed)


# ------------------------------------------------------------ solve + report
def solve_all(graph, time_limit):
    """Run both greedy heuristics, then the exact solver seeded with the better heuristic."""
    lb = max(lower_bound_parts(graph))
    ds, wp = dsatur(graph), welsh_powell(graph)
    for r in (ds, wp):
        r["proven_optimal"], r["lower_bound"], r["timed_out"] = r["slots"] == lb, lb, False
    exact = exact_branch_and_bound(graph, time_limit, initial=min((ds, wp), key=lambda r: r["slots"]))
    return [ds, wp, exact]


def _optimal_text(r):
    if r["proven_optimal"]:
        return "yes (lower bound matched)" if r["slots"] == r["lower_bound"] else "yes (search exhausted)"
    if r.get("timed_out"):
        return "no (time limit reached, best found)"
    return f"no (heuristic, gap to lower bound = {r['slots'] - r['lower_bound']})"


def report(graph, results, out_dir):
    cap_b, clq_b = lower_bound_parts(graph)
    print(f"Instance: N={graph.n}  M={len(graph.edges)}  R={graph.capacity}  density={graph.density:.3f}")
    print(f"Lower bound = max(ceil(N/R)={cap_b}, clique={clq_b}) = {max(cap_b, clq_b)}\n")
    print(f"{'Algorithm':<14}{'Slots':>6}{'Time (ms)':>12}   Proven optimal?")
    print("-" * 70)
    for r in results:
        problems = validate(graph, r["assignment"])
        if problems:
            raise RuntimeError(f"{r['name']} produced an invalid timetable: {problems[0]}")
        print(f"{r['name']:<14}{r['slots']:>6}{r['seconds'] * 1000:>12.3f}   {_optimal_text(r)}")
    exact, best_greedy = results[-1], min(results[:-1], key=lambda r: r["slots"])
    saved = best_greedy["slots"] - exact["slots"]
    print(f"\nAll timetables verified: no conflicts, <= R exams per slot.")
    print(f"Exact solver explored {exact['nodes']} search nodes and saved {saved} slot(s) over the best heuristic.")
    for r in results:
        print(f"\n{r['name']} timetable:")
        slots = [[] for _ in range(r["slots"])]
        for course, slot in enumerate(r["assignment"]):
            slots[slot].append(course + 1)
        for index, courses in enumerate(slots, 1):
            print(f"Slot {index}: {', '.join(map(str, courses))}")
    files = [write_timetable_csv(graph, r["assignment"], out_dir / f"timetable_{SLUG[r['name']]}.csv") for r in results]
    print("\nCSV files saved:\n  " + "\n  ".join(map(str, files)))


def run_comparison(graph, opts):
    out = Path(opts.out)
    results = solve_all(graph, opts.time_limit)
    report(graph, results, out)
    png = out / "schedule_comparison.png"
    gif = out / "schedule_animation.gif" if opts.gif else None
    show_schedule_comparison(graph, results, animate=not opts.no_animate, show=not opts.no_show,
                             save_png=png, save_gif=gif)
    print(f"Image saved: {png}" + (f"\nAnimation saved: {gif}" if gif else ""))


# ---------------------------------------------------------------- benchmark
def run_benchmark(opts, params=None):
    if params is None:
        sizes_text = ask("Course counts to benchmark (comma-separated, e.g. 8,12,16,20,30): ")
        sizes = sorted({int(v.strip()) for v in sizes_text.split(",") if v.strip()})
        capacity = int(ask("Hall capacity R: "))
        density = float(ask("Random edge density (0.0 to 1.0): "))
        repeats = int(ask("Random graphs per size (default 3): ") or "3")
        limit = float(ask("Exact solver time limit per graph in seconds (default 3): ") or "3")
    else:
        sizes, capacity, density, repeats, limit = params
    if not sizes or sizes[0] < 1 or capacity < 1 or not 0 <= density <= 1 or repeats < 1 or limit <= 0:
        raise ValueError("Course counts, R, density, repeats or time limit is outside its valid range.")
    rows = []
    print(f"\n{'N':>4} | " + " | ".join(f"{n:<22}" for n in ("DSatur slots/ms", "Welsh-P slots/ms", "Exact slots/ms")) + " | LB  | timeouts")
    for n in sizes:
        runs = [solve_all(generate_random_graph(n, capacity, density, seed=1000 + n * 31 + rep), limit)
                for rep in range(repeats)]
        graphs = [generate_random_graph(n, capacity, density, seed=1000 + n * 31 + rep) for rep in range(repeats)]
        row = {"n": n, "slots": {}, "time": {}, "timeouts": sum(r[2]["timed_out"] for r in runs),
               "lower": sum(max(lower_bound_parts(g)) for g in graphs) / repeats}
        for i, name in enumerate(("DSatur", "Welsh-Powell", "Exact B&B")):
            row["slots"][name] = sum(r[i]["slots"] for r in runs) / repeats
            row["time"][name] = sum(r[i]["seconds"] for r in runs) / repeats
        rows.append(row)
        cells = [f"{row['slots'][k]:5.2f} / {row['time'][k] * 1000:10.2f}" for k in row["slots"]]
        print(f"{n:>4} | " + " | ".join(f"{c:<22}" for c in cells) + f" | {row['lower']:.1f} | {row['timeouts']}/{repeats}")
    out = Path(opts.out)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "benchmark.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["N", "lower_bound", "dsatur_slots", "welsh_powell_slots", "exact_slots",
                    "dsatur_ms", "welsh_powell_ms", "exact_ms", "exact_timeouts"])
        for r in rows:
            w.writerow([r["n"], f"{r['lower']:.2f}", *(f"{r['slots'][k]:.2f}" for k in r["slots"]),
                        *(f"{r['time'][k] * 1000:.3f}" for k in r["time"]), r["timeouts"]])
    show_benchmark_chart(rows, density, capacity, save_path=out / "benchmark.png", show=not opts.no_show)
    print(f"\nSaved: {out / 'benchmark.csv'} and {out / 'benchmark.png'}")


# ---------------------------------------------------------------- front-ends
def interactive_mode(opts):
    print("EXAM TIMETABLE SCHEDULER", file=sys.stderr)
    print("1. Load a conflict graph from a file (N M R + edges)\n2. Generate a random graph (N R + density)\n"
          "3. Benchmark all algorithms as N grows", file=sys.stderr)
    choice = ask("Choose 1, 2, or 3: ")
    if choice == "3":
        return run_benchmark(opts)
    limit = float(ask("Exact solver time limit in seconds (default 10): ") or "10")
    if limit <= 0:
        raise ValueError("Exact solver time limit must be positive.")
    opts.time_limit = limit
    if choice == "1":
        graph = load_edge_list(ask("Input file path (default sample_graph.txt): ") or "sample_graph.txt")
    elif choice == "2":
        graph = read_random_input(seed=opts.seed)
    else:
        raise ValueError("Choose 1, 2, or 3.")
    run_comparison(graph, opts)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Exam timetabling: Welsh-Powell, DSatur and exact branch-and-bound.")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--file", metavar="PATH", help="Option 1 from a file whose first line is N M R")
    modes.add_argument("--stdin-graph", action="store_true", help="Option 1 from stdin: N M R, then M edges")
    modes.add_argument("--random", action="store_true", help="Option 2 from stdin: line 'N R', then density")
    modes.add_argument("--benchmark", action="store_true", help="Increasing-N comparison benchmark")
    parser.add_argument("--time-limit", type=float, default=10.0, help="Exact search limit in seconds (default 10)")
    parser.add_argument("--seed", type=int, default=None, help="Seed for random graphs (reproducible runs)")
    parser.add_argument("--out", default="output", help="Output folder (default: output)")
    parser.add_argument("--gif", action="store_true", help="Also save the animation as output/schedule_animation.gif")
    parser.add_argument("--no-animate", action="store_true", help="Show the final schedule without animating")
    parser.add_argument("--no-show", action="store_true", help="Do not open windows (save files only)")
    opts = parser.parse_args(argv)
    if opts.time_limit <= 0:
        raise ValueError("Exact solver time limit must be positive.")
    if opts.benchmark:
        run_benchmark(opts)
        return 0
    if opts.file:
        graph = load_edge_list(opts.file)
    elif opts.stdin_graph:
        graph = parse_edge_list(sys.stdin.read())
    elif opts.random:
        graph = read_random_input(show_prompts=False, seed=opts.seed)
    else:
        interactive_mode(opts)
        return 0
    run_comparison(graph, opts)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as error:
        print(f"Input error: {error}", file=sys.stderr)
        raise SystemExit(1)
