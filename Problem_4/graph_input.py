"""Input helpers (Option 1 / Option 2) and timetable CSV export."""
from dataclasses import dataclass
from pathlib import Path
import csv
import random


@dataclass(frozen=True)
class ConflictGraph:
    n: int
    capacity: int
    adjacency: tuple  # tuple[frozenset[int], ...], zero-based course ids

    @property
    def edges(self):
        return [(u, v) for u in range(self.n) for v in sorted(self.adjacency[u]) if u < v]

    @property
    def density(self):
        pairs = self.n * (self.n - 1) / 2
        return len(self.edges) / pairs if pairs else 0.0


def _make_graph(n, capacity, edges):
    if n < 1:
        raise ValueError("N must be at least 1.")
    if capacity < 1:
        raise ValueError("R (hall capacity) must be at least 1.")
    adjacency = [set() for _ in range(n)]
    for u, v in edges:
        if not (0 <= u < n and 0 <= v < n):
            raise ValueError(f"Course IDs must be from 1 to {n}.")
        if u == v:
            raise ValueError("A course cannot conflict with itself.")
        adjacency[u].add(v)
        adjacency[v].add(u)
    return ConflictGraph(n, capacity, tuple(frozenset(row) for row in adjacency))


def parse_edge_list(text):
    """Option 1: 'N M R' followed by M lines 'u v' (1-based). '#' starts a comment.

    Duplicate conflicts (u v / v u) are harmless and merged; self-conflicts,
    out-of-range ids and a wrong number of lines are rejected.
    """
    lines = [line.split("#", 1)[0].strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        raise ValueError("The input is empty.")
    header = lines[0].split()
    if len(header) != 3:
        raise ValueError("First line must be: N M R")
    try:
        n, m, capacity = map(int, header)
    except ValueError as exc:
        raise ValueError("N, M, and R must be integers.") from exc
    if n < 1 or m < 0 or capacity < 1:
        raise ValueError("Use N >= 1, M >= 0, and R >= 1.")
    if len(lines) - 1 != m:
        raise ValueError(f"Header says M={m}, but found {len(lines) - 1} conflict lines.")
    edges = set()
    for number, line in enumerate(lines[1:], start=2):
        pair = line.split()
        if len(pair) != 2:
            raise ValueError(f"Line {number} must contain two course IDs.")
        try:
            u, v = map(int, pair)
        except ValueError as exc:
            raise ValueError(f"Line {number} must contain integer course IDs.") from exc
        if not (1 <= u <= n and 1 <= v <= n):
            raise ValueError(f"Line {number}: course IDs must be between 1 and {n}.")
        if u == v:
            raise ValueError(f"Line {number}: course {u} cannot conflict with itself.")
        edges.add((min(u, v) - 1, max(u, v) - 1))
    return _make_graph(n, capacity, sorted(edges))


def load_edge_list(path):
    return parse_edge_list(Path(path).read_text(encoding="utf-8-sig"))


def generate_random_graph(n, capacity, density, seed=None):
    """Option 2: each pair of courses conflicts independently with probability `density`."""
    if not 0.0 <= density <= 1.0:
        raise ValueError("Edge density must be between 0.0 and 1.0.")
    rng = random.Random(seed)
    edges = [(u, v) for u in range(n) for v in range(u + 1, n) if rng.random() < density]
    return _make_graph(n, capacity, edges)


def timetable_columns(graph):
    """Number of hall columns: R, but never more than N (a slot cannot hold more than N exams)."""
    return min(graph.capacity, graph.n)


def write_timetable_csv(graph, assignment, path):
    """Rows = slots, columns = hall positions. Unused hall cells are blank."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    slot_count = max(assignment, default=-1) + 1
    slots = [[] for _ in range(slot_count)]
    for course, slot in enumerate(assignment):
        slots[slot].append(course + 1)
    cols = timetable_columns(graph)
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["Slot"] + [f"Hall {i + 1}" for i in range(cols)])
        for index, courses in enumerate(slots):
            writer.writerow([f"Slot {index + 1}"] + courses + [""] * (cols - len(courses)))
    return output
