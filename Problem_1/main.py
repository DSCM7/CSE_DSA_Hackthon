"""Problem 1 - Maze with Keys and Doors.

Standard input  : T, then 1 (CSV file) or 2 (random maze) and the file path / grid size.
Standard output : a single integer, the shortest path length (or -1).
Files           : output/solution_path.csv   maze with the route marked 'x'
                  output/solution_steps.csv  step-by-step log of keys and doors
Everything else (prompts, tables, warnings) goes to standard error.

Examples
    python main.py
    python main.py --csv samples/sample_t3_generated.csv
    python main.py --random --size 25 --seed 4 --no-gui --gif output/run.gif
    echo 3 | python main.py --random --no-gui          (scripted use)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from maze_solver import (default_size, describe_route, generate_maze, load_maze, solve_astar,
                         solve_bfs, solve_dfs, verify_route, write_marked_path_csv, write_maze_csv,
                         write_steps_csv)


def say(text=""):
    print(text, file=sys.stderr)


def ask(prompt, default=None):
    """Prompt on stderr (so stdout stays clean).  EOF falls back to the default."""
    print(prompt, end="", file=sys.stderr, flush=True)
    try:
        answer = input().strip()
    except EOFError:
        if default is None:
            raise ValueError("Unexpected end of input.")
        say()
        return default
    return answer or default


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Maze with Keys and Doors: shortest path + live visualisation.")
    p.add_argument("--types", type=int, help="T (otherwise read from standard input)")
    src = p.add_mutually_exclusive_group()
    src.add_argument("--csv", metavar="FILE", help="read the maze from this CSV file")
    src.add_argument("--random", action="store_true", help="generate a random solvable maze")
    p.add_argument("--size", type=int, help="grid size N for a random maze (default depends on T)")
    p.add_argument("--seed", type=int, help="random seed, for reproducible mazes")
    p.add_argument("--solver", choices=("bfs", "astar", "dfs"), default="bfs", help="algorithm that produces the route")
    p.add_argument("--no-compare", action="store_true", help="skip the BFS / A* / DFS comparison")
    p.add_argument("--no-gui", action="store_true", help="do not open the animation window")
    p.add_argument("--gif", metavar="FILE", help="also save the animation as a GIF")
    p.add_argument("--png", metavar="FILE", help="also save a PNG of the finished route")
    p.add_argument("--out", default="output", help="output folder (default: output)")
    return p.parse_args(argv)


def get_types(args):
    value = args.types
    if value is None:
        value = ask("Enter T (number of key/door types, 1-6): ")
    try:
        value = int(value)
    except ValueError:
        raise ValueError("T must be an integer between 1 and 6.")
    if not 1 <= value <= 6:
        raise ValueError("T must be between 1 and 6.")
    return value


def get_maze(args, t, out_dir):
    choice = "1" if args.csv else "2" if args.random else None
    if choice is None:
        say("Choose maze input:  1 = read a CSV file   2 = generate a random solvable maze")
        choice = ask("Enter 1 or 2: ")
    if choice == "1":
        path = args.csv or ask("CSV file path (Enter = sample_maze.csv): ", "sample_maze.csv")
        return load_maze(path, expected_types=t)
    if choice == "2":
        size = args.size
        if size is None:
            raw = ask(f"Grid size N (Enter = {default_size(t)}): ", "")
            size = int(raw) if raw else None
        maze = generate_maze(t, size=size, seed=args.seed)
        saved = write_maze_csv(maze, out_dir / "generated_maze.csv")
        say(f"Generated a solvable {maze.size} x {maze.size} maze (saved to {saved}).")
        return maze
    raise ValueError("Choose 1 for a CSV file or 2 for random generation.")


def comparison(maze):
    results = [solve_bfs(maze), solve_astar(maze), solve_dfs(maze)]
    say("")
    say(f"{'algorithm':<10}{'length':>8}{'states':>10}{'ms':>9}")
    for r in results:
        say(f"{r.algorithm:<10}{r.length:>8}{r.expanded:>10,}{'+' if r.capped else ' '}{r.time_ms:>8.2f}")
    finished = {r.length for r in results if not r.capped}
    if len(finished) > 1:
        say("WARNING: the algorithms disagree - please report this as a bug.")
    say("")
    return results


def main(argv=None):
    args = parse_args(argv)
    out_dir = Path(args.out)
    try:
        t = get_types(args)
        maze = get_maze(args, t, out_dir)
        for warning in maze.warnings:
            say(f"Note: {warning}")

        primary = {"bfs": solve_bfs, "astar": solve_astar, "dfs": solve_dfs}[args.solver](maze)
        route = primary.route
        if route:
            verify_route(maze, route)                  # replay the route under the game rules
        print(primary.length)                          # <- the one line on stdout

        marked = write_marked_path_csv(maze, route or [], out_dir / "solution_path.csv")
        say(f"Marked path CSV : {marked}")
        if route:
            say(f"Steps log CSV   : {write_steps_csv(maze, route, out_dir / 'solution_steps.csv')}")
            events = [s.note for s in describe_route(maze, route) if s.kind in ("key", "door")]
            say("Key / door events: " + "; ".join(events))
        else:
            say("No route exists from S to E.")

        stats = comparison(maze) if not args.no_compare else [primary]

        if args.gif or args.png or not args.no_gui:
            import matplotlib
            if args.no_gui:
                matplotlib.use("Agg")                  # headless export only
            from visualizer import MazeView, show_animation
        if args.png or args.gif:
            view = MazeView(maze, route, stats=stats, visited=primary.visited)
            if args.png:
                Path(args.png).parent.mkdir(parents=True, exist_ok=True)
                view.save_png(args.png)
                say(f"PNG saved       : {args.png}")
            if args.gif:
                Path(args.gif).parent.mkdir(parents=True, exist_ok=True)
                say("Rendering GIF (a few seconds)...")
                view.save_gif(args.gif)
                say(f"GIF saved       : {args.gif}")
            import matplotlib.pyplot as plt
            plt.close(view.fig)
        if not args.no_gui:
            say("Opening the animation. Close the window to return to the terminal.")
            show_animation(maze, route, stats=stats, visited=primary.visited)
        return 0
    except (ValueError, OSError, RuntimeError) as error:
        say(f"Input error: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
