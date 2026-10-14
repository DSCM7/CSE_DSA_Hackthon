"""Run with:  python tests.py     (corner cases + exact solver vs. exhaustive brute force)"""
import random
import unittest

from graph_input import parse_edge_list, generate_random_graph, _make_graph
from scheduler import dsatur, welsh_powell, exact_branch_and_bound, lower_bound, validate


def brute_force_min_slots(graph):
    """Exhaustive search over all set partitions (restricted-growth strings). Tiny N only."""
    best = [graph.n]
    assign = [0] * graph.n

    def rec(i, used, sizes):
        if used >= best[0]:
            return
        if i == graph.n:
            best[0] = used
            return
        for s in range(used + 1):
            if s < used and (sizes[s] >= graph.capacity or any(assign[u] == s for u in graph.adjacency[i] if u < i)):
                continue
            assign[i] = s
            if s == used:
                rec(i + 1, used + 1, sizes + [1])
            else:
                sizes[s] += 1
                rec(i + 1, used, sizes)
                sizes[s] -= 1
    rec(0, 0, [])
    return best[0]


def all_results(graph):
    return [dsatur(graph), welsh_powell(graph), exact_branch_and_bound(graph, 5)]


class CornerCases(unittest.TestCase):
    def check(self, graph, expected):
        for r in all_results(graph):
            self.assertEqual(validate(graph, r["assignment"]), [], r["name"])
        self.assertEqual(all_results(graph)[-1]["slots"], expected)

    def test_single_course(self):
        self.check(_make_graph(1, 1, []), 1)

    def test_no_conflicts_capacity_one(self):          # R=1 -> N slots
        self.check(_make_graph(5, 1, []), 5)

    def test_no_conflicts_big_capacity(self):          # R>=N -> 1 slot
        self.check(_make_graph(5, 10, []), 1)

    def test_complete_graph(self):                     # K5 -> 5 slots
        edges = [(u, v) for u in range(5) for v in range(u + 1, 5)]
        self.check(_make_graph(5, 3, edges), 5)

    def test_even_cycle_capacity_binds(self):          # C6, R=2 -> ceil(6/2)=3 slots
        self.check(_make_graph(6, 2, [(i, (i + 1) % 6) for i in range(6)]), 3)

    def test_even_cycle_two_colours(self):             # C6, R=3 -> 2 slots
        self.check(_make_graph(6, 3, [(i, (i + 1) % 6) for i in range(6)]), 2)

    def test_odd_cycle(self):                          # C5 -> chi=3
        self.check(_make_graph(5, 5, [(i, (i + 1) % 5) for i in range(5)]), 3)

    def test_star(self):
        self.check(_make_graph(6, 6, [(0, i) for i in range(1, 6)]), 2)

    def test_disconnected(self):
        self.check(_make_graph(6, 6, [(0, 1), (2, 3)]), 2)

    def test_sample_file(self):
        g = parse_edge_list("8 9 3\n1 2\n1 3\n2 3\n2 4\n3 5\n4 5\n4 6\n5 7\n7 8\n")
        self.check(g, 3)


class InputValidation(unittest.TestCase):
    def test_bad_inputs(self):
        for text in ["", "3 1\n1 2", "3 1 2\n1 1", "3 1 2\n1 9", "3 2 2\n1 2", "0 0 1", "3 0 0", "3 1 2\na b"]:
            with self.assertRaises(ValueError, msg=text):
                parse_edge_list(text)

    def test_duplicate_edges_merge(self):
        g = parse_edge_list("3 2 2\n1 2\n2 1")
        self.assertEqual(len(g.edges), 1)

    def test_density_bounds(self):
        with self.assertRaises(ValueError):
            generate_random_graph(5, 2, 1.5)
        self.assertEqual(len(generate_random_graph(6, 2, 1.0).edges), 15)
        self.assertEqual(len(generate_random_graph(6, 2, 0.0).edges), 0)


class AgainstBruteForce(unittest.TestCase):
    def test_exact_equals_brute_force_and_bounds(self):
        rng = random.Random(42)
        for _ in range(150):
            n, r = rng.randint(1, 8), rng.randint(1, 4)
            g = generate_random_graph(n, r, rng.random(), seed=rng.randint(0, 10 ** 6))
            truth = brute_force_min_slots(g)
            ds, wp, ex = all_results(g)
            self.assertEqual(ex["slots"], truth)
            self.assertTrue(ex["proven_optimal"])
            self.assertLessEqual(lower_bound(g), truth)
            self.assertGreaterEqual(ds["slots"], truth)
            self.assertGreaterEqual(wp["slots"], truth)
            for res in (ds, wp, ex):
                self.assertEqual(validate(g, res["assignment"]), [])


if __name__ == "__main__":
    unittest.main(verbosity=1)
