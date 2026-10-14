"""Unit tests and fuzz tests for the maze solver.  Run:  python -m unittest discover -s tests -v"""
import csv
import random
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from maze_solver import (ALGORITHMS, describe_route, generate_maze, load_maze, maze_from_text,
                         solve, solve_astar, solve_bfs, solve_dfs, solve_key_graph, solve_naive,
                         verify_route, write_marked_path_csv, write_steps_csv)

SAMPLES = ROOT / "samples"


def read_csv(path):
    with Path(path).open(newline="") as fh:
        return list(csv.reader(fh))


def M(text, t=None):
    return maze_from_text(text.strip(), t)


class ShortestPath(unittest.TestCase):
    def test_provided_sample(self):
        self.assertEqual(solve_bfs(load_maze(ROOT / "sample_maze.csv", 1)).length, 14)

    def test_revisit_needs_state_not_cell(self):
        """The optimal route walks through one cell twice with different key masks."""
        maze = load_maze(SAMPLES / "sample_revisit.csv")
        self.assertEqual(solve_bfs(maze).length, 5)
        self.assertEqual(solve_naive(maze).length, -1)      # cell-only BFS is wrong here

    def test_door_blocks_its_own_key(self):
        self.assertEqual(solve_bfs(load_maze(SAMPLES / "sample_locked_key.csv")).length, -1)

    def test_key_not_needed(self):
        self.assertEqual(solve_bfs(load_maze(SAMPLES / "sample_no_key_needed.csv")).length, 3)

    def test_unreachable_exit_walled_off(self):
        self.assertEqual(solve_bfs(M("S,#,.\n#,#,.\n.,.,E")).length, -1)

    def test_start_next_to_exit(self):
        self.assertEqual(solve_bfs(M("S,E\n.,.")).length, 1)

    def test_door_without_any_key_is_a_wall(self):
        maze = M("S,B,E\n#,#,#\n#,#,#")
        self.assertEqual(solve_bfs(maze).length, -1)
        self.assertTrue(any("never be opened" in w for w in maze.warnings))

    def test_duplicate_keys_and_doors(self):
        maze = M("S,a,a,A\n#,#,#,A\n#,#,#,E\n#,#,#,#")
        self.assertEqual(solve_bfs(maze).length, 5)

    def test_chain_of_doors(self):
        maze = M("S,a,A,b,B,E\n#,#,#,#,#,.\n#,#,#,#,#,.\n#,#,#,#,#,.\n#,#,#,#,#,.\n#,#,#,#,#,.")
        self.assertEqual(solve_bfs(maze).length, 5)

    def test_shorter_route_through_door_beats_open_detour(self):
        maze = load_maze(SAMPLES / "sample_two_routes.csv")
        results = {name: solve(maze, name).length for name in ("bfs", "astar", "dfs", "keygraph")}
        self.assertEqual(set(results.values()), {10})


class SymbolCollision(unittest.TestCase):
    def test_e_door_and_exit(self):
        # key e + door E + exit E: last E in row-major order is the exit
        maze = M("S,e,E,E\n#,#,#,#\n#,#,#,#\n#,#,#,#", 1)
        self.assertEqual(maze.exit, (0, 3))
        self.assertEqual(solve_bfs(maze).length, 3)

    def test_e_key_without_e_door(self):
        maze = M("S,e,E\n#,#,#\n#,#,#")
        self.assertEqual(maze.exit, (0, 2))
        self.assertEqual(solve_bfs(maze).length, 2)

    def test_six_types(self):
        maze = M("S,a,A,b,B,c,C,d\n#,#,#,#,#,#,#,D\n#,#,#,#,#,#,#,e\n#,#,#,#,#,#,#,E\n"
                 "#,#,#,#,#,#,#,f\n#,#,#,#,#,#,#,F\n#,#,#,#,#,#,#,.\n#,#,#,#,#,#,#,E", 6)
        self.assertEqual(maze.exit, (7, 7))
        self.assertEqual(solve_bfs(maze).length, 14)


class Parsing(unittest.TestCase):
    def test_not_square(self):
        with self.assertRaises(ValueError):
            M("S,.,.\n.,.,E")

    def test_bad_symbol(self):
        with self.assertRaises(ValueError):
            M("S,z\n.,E")

    def test_empty_cell(self):
        with self.assertRaises(ValueError):
            M("S,\n.,E")

    def test_missing_or_double_start(self):
        with self.assertRaises(ValueError):
            M(".,E\n.,.")
        with self.assertRaises(ValueError):
            M("S,S\n.,E")

    def test_missing_or_double_exit(self):
        with self.assertRaises(ValueError):
            M("S,.\n.,.")
        with self.assertRaises(ValueError):
            M("S,E\nE,.")

    def test_empty_file(self):
        with self.assertRaises(ValueError):
            maze_from_text("")

    def test_t_mismatch_is_a_warning(self):
        maze = M("S,a,A\n#,#,E\n#,#,#", 3)
        self.assertTrue(any("T = 3" in w for w in maze.warnings))

    def test_compact_rows_and_bom_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "m.csv"
            p.write_text("\ufeffS.aA\n####\n####\n###E\n".replace("\n", "\r\n"), encoding="utf-8")
            self.assertEqual(load_maze(p).size, 4)


class RouteAndFiles(unittest.TestCase):
    def test_route_is_legal_and_described(self):
        maze = load_maze(SAMPLES / "sample_revisit.csv")
        route = solve_bfs(maze).route
        self.assertTrue(verify_route(maze, route))
        kinds = [s.kind for s in describe_route(maze, route)]
        self.assertEqual(kinds, ["start", "move", "key", "move", "door", "exit"])

    def test_verify_rejects_cheating(self):
        maze = load_maze(SAMPLES / "sample_revisit.csv")
        with self.assertRaises(ValueError):
            verify_route(maze, [(0, 0), (0, 1), (0, 2), (0, 3)])        # door without key

    def test_marked_csv_keeps_identifiers(self):
        maze = load_maze(SAMPLES / "sample_revisit.csv")
        route = solve_bfs(maze).route
        with tempfile.TemporaryDirectory() as d:
            out = write_marked_path_csv(maze, route, Path(d) / "o.csv")
            rows = read_csv(out)
            steps = write_steps_csv(maze, route, Path(d) / "s.csv")
            n_steps = len(read_csv(steps)) - 1
        self.assertEqual(rows[0], ["S", "x", "A", "E"])
        self.assertEqual(rows[1][1], "a")
        self.assertEqual(n_steps, len(route))

    def test_no_route_marks_nothing(self):
        maze = load_maze(SAMPLES / "sample_locked_key.csv")
        with tempfile.TemporaryDirectory() as d:
            out = write_marked_path_csv(maze, [], Path(d) / "o.csv")
            self.assertEqual(read_csv(out)[0], ["S", "A", "a", "E"])


class Generator(unittest.TestCase):
    def test_all_t_and_seeds(self):
        for t in range(1, 7):
            for seed in range(6):
                maze = generate_maze(t, seed=seed)
                flat = [v for row in maze.grid for v in row]
                for k in "abcdef"[:t]:
                    self.assertEqual(flat.count(k), 1)
                    self.assertEqual(flat.count(k.upper()) - (1 if k == "e" else 0), 1)
                result = solve_bfs(maze)
                self.assertGreater(result.length, 0)
                self.assertTrue(verify_route(maze, result.route))
                self.assertEqual({v for v in (maze.grid[r][c] for r, c in result.route) if v in "abcdef"},
                                 set("abcdef"[:t]))

    def test_reproducible(self):
        self.assertEqual(generate_maze(3, seed=5).grid, generate_maze(3, seed=5).grid)

    def test_custom_size_and_limits(self):
        self.assertEqual(generate_maze(2, size=12, seed=1).size, 12)
        with self.assertRaises(ValueError):
            generate_maze(0)
        with self.assertRaises(ValueError):
            generate_maze(7)
        with self.assertRaises(ValueError):
            generate_maze(6, size=8)


class CrossCheck(unittest.TestCase):
    """Every optimal algorithm and the independent oracle must agree."""

    def agree(self, maze):
        lengths = {n: solve(maze, n).length for n in ("bfs", "astar", "dfs", "keygraph")}
        self.assertEqual(len(set(lengths.values())), 1, lengths)
        return lengths["bfs"]

    def test_generated(self):
        for t in range(1, 7):
            self.agree(generate_maze(t, size=t + 9, seed=100 + t))
            self.agree(generate_maze(t, size=t + 11, seed=200 + t, loops=0.3, strict=False))

    def test_fuzz_small_random_grids(self):
        rng = random.Random(2026)
        solved = 0
        for _ in range(400):
            n = rng.randint(3, 6)
            cells = rng.choices(list(".#abcdABCD"), weights=[8, 4, 1, 1, 1, 1, 1, 1, 1, 1], k=n * n)
            s, e = rng.sample(range(n * n), 2)
            cells[s], cells[e] = "S", "E"
            maze = maze_from_text("\n".join(",".join(cells[r * n:(r + 1) * n]) for r in range(n)))
            if self.agree(maze) > 0:
                solved += 1
        self.assertGreater(solved, 100)       # the fuzz really exercised solvable cases


if __name__ == "__main__":
    unittest.main()
