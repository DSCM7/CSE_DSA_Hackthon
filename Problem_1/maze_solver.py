"""Maze with Keys and Doors: parsing, generation, solvers and CSV output.

State space
-----------
A position alone is not enough to describe progress through the maze, because
the doors you may enter depend on the keys you hold.  The search state is
therefore ``(row, col, key_mask)`` where ``key_mask`` is a bitmask with one bit
per key type present in the grid (at most 6 bits -> at most 64 masks).

Every move costs exactly 1, so Breadth-First Search over this state graph finds
the shortest path.  Total work is O(N^2 * 2^T).  See ANALYSIS.md for the proof.
"""
from __future__ import annotations

import csv
import heapq
import random
import time
from array import array
from collections import deque
from dataclasses import dataclass
from pathlib import Path

KEY_LETTERS = "abcdef"
DOOR_LETTERS = "ABCDEF"
ALLOWED = set(".#SE" + KEY_LETTERS + DOOR_LETTERS)
MOVES = ((-1, 0), (1, 0), (0, -1), (0, 1))
UNSEEN = -2          # parent[] sentinel: state never discovered
ROOT = -1            # parent[] sentinel: the start state
INF = 1 << 30


# --------------------------------------------------------------------------- #
#  Data model
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Maze:
    grid: tuple                  # tuple of tuples of single-character strings
    start: tuple                 # (row, col)
    exit: tuple                  # (row, col)
    keys: tuple                  # sorted key letters present, e.g. ('a', 'b')
    doors: tuple = ()            # sorted door types present (lower-case)
    warnings: tuple = ()         # non-fatal input remarks

    @property
    def size(self):
        return len(self.grid)

    def is_door(self, r, c):
        return self.grid[r][c] in DOOR_LETTERS and (r, c) != self.exit


@dataclass
class SolveResult:
    algorithm: str
    route: list | None           # [(r, c), ...] from S to E, or None
    length: int                  # number of moves, -1 when unreachable
    expanded: int                # states taken off the frontier
    time_ms: float
    visited: frozenset = frozenset()   # cells ever reached (used for "no path" view)
    capped: bool = False         # True when a safety cap stopped the search early


@dataclass(frozen=True)
class Step:
    index: int
    pos: tuple
    symbol: str
    kind: str                    # start | move | key | door | exit
    held: str                    # keys held after this step, e.g. "ac"
    note: str


# --------------------------------------------------------------------------- #
#  Parsing and validation
# --------------------------------------------------------------------------- #
def _validate(rows, expected_types=None):
    if not rows or not rows[0]:
        raise ValueError("The grid cannot be empty.")
    n = len(rows)
    for i, row in enumerate(rows):
        if len(row) != n:
            raise ValueError(
                f"The maze must be an N x N square grid: there are {n} rows but row {i + 1} has {len(row)} cells.")
    for r, row in enumerate(rows):
        for c, cell in enumerate(row):
            if cell not in ALLOWED:
                shown = repr(cell) if cell else "an empty cell"
                raise ValueError(f"Invalid cell {shown} at row {r + 1}, column {c + 1}.")

    starts = [(r, c) for r, row in enumerate(rows) for c, v in enumerate(row) if v == "S"]
    exits = [(r, c) for r, row in enumerate(rows) for c, v in enumerate(row) if v == "E"]
    if len(starts) != 1:
        raise ValueError(f"The grid must contain exactly one S start (found {len(starts)}).")

    warnings = []
    keys = tuple(sorted({v for row in rows for v in row if v in KEY_LETTERS}))
    # 'E' is both the exit symbol and the door symbol for key 'e'.  When key e is
    # present, the LAST 'E' in row-major order is the exit and earlier ones are doors.
    if "e" in keys:
        if not exits:
            raise ValueError("The grid needs an E exit (key e is present, so the last E is the exit).")
        exit_position = exits[-1]
        if len(exits) > 1:
            warnings.append("Key e is present: the last E in row-major order is the exit; other E cells are doors.")
    else:
        if len(exits) != 1:
            raise ValueError(f"The grid must contain exactly one E exit (found {len(exits)}).")
        exit_position = exits[0]

    doors = tuple(sorted({v.lower() for r, row in enumerate(rows) for c, v in enumerate(row)
                          if v in DOOR_LETTERS and (r, c) != exit_position}))
    for k in sorted(set(keys) - set(doors)):
        warnings.append(f"Key '{k}' has no matching door '{k.upper()}'.")
    for d in sorted(set(doors) - set(keys)):
        warnings.append(f"Door '{d.upper()}' has no matching key '{d}', so it can never be opened.")
    found_types = len(set(keys) | set(doors))
    if expected_types is not None and found_types != expected_types:
        warnings.append(f"T = {expected_types} was given but the grid has {found_types} key/door type(s).")
    return Maze(tuple(tuple(row) for row in rows), starts[0], exit_position, keys, doors, tuple(warnings))


def parse_rows(text):
    """Parse CSV text (or compact rows such as 'S..#E') into a list of rows."""
    rows = []
    for line in text.splitlines():
        if not line.strip():
            continue
        cells = [cell.strip() for cell in next(csv.reader([line]))]
        rows.append(cells if len(cells) > 1 else list(cells[0]))
    return rows


def load_maze(csv_path, expected_types=None):
    """Load an N x N maze from a CSV file."""
    with Path(csv_path).open("r", newline="", encoding="utf-8-sig") as f:
        return _validate(parse_rows(f.read()), expected_types)


def maze_from_text(text, expected_types=None):
    return _validate(parse_rows(text), expected_types)


def write_maze_csv(maze, output_csv):
    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f, lineterminator="\n").writerows(maze.grid)
    return output_path


# --------------------------------------------------------------------------- #
#  Random generation
# --------------------------------------------------------------------------- #
def _carve(n, rng):
    """Recursive-backtracker maze on the even/even lattice (a spanning tree)."""
    grid = [["#"] * n for _ in range(n)]
    grid[0][0] = "."
    stack = [(0, 0)]
    while stack:
        r, c = stack[-1]
        options = [(r + dr, c + dc, dr, dc) for dr, dc in ((-2, 0), (2, 0), (0, -2), (0, 2))
                   if 0 <= r + dr < n and 0 <= c + dc < n and grid[r + dr][c + dc] == "#"]
        if not options:
            stack.pop()
            continue
        nr, nc, dr, dc = rng.choice(options)
        grid[r + dr // 2][c + dc // 2] = "."
        grid[nr][nc] = "."
        stack.append((nr, nc))
    return grid


def _braid(grid, rng, probability):
    """Knock out some interior walls to create loops (alternative routes)."""
    n = len(grid)
    for r in range(1, n - 1):
        for c in range(1, n - 1):
            if grid[r][c] != "#" or rng.random() >= probability:
                continue
            vertical = r % 2 == 1 and c % 2 == 0 and grid[r - 1][c] != "#" and grid[r + 1][c] != "#"
            horizontal = r % 2 == 0 and c % 2 == 1 and grid[r][c - 1] != "#" and grid[r][c + 1] != "#"
            if vertical or horizontal:
                grid[r][c] = "."


def _neighbours(grid, r, c):
    n = len(grid)
    for dr, dc in MOVES:
        nr, nc = r + dr, c + dc
        if 0 <= nr < n and 0 <= nc < n and grid[nr][nc] != "#":
            yield nr, nc


def _shortest_cell_path(grid, src, dst):
    parent = {src: None}
    queue = deque([src])
    while queue:
        cur = queue.popleft()
        if cur == dst:
            break
        for nxt in _neighbours(grid, *cur):
            if nxt not in parent:
                parent[nxt] = cur
                queue.append(nxt)
    path, cur = [], dst
    while cur is not None:
        path.append(cur)
        cur = parent[cur]
    return path[::-1]


def _region(grid, src, blocked):
    seen = {src}
    queue = deque([src])
    while queue:
        cur = queue.popleft()
        for nxt in _neighbours(grid, *cur):
            if nxt not in seen and nxt not in blocked:
                seen.add(nxt)
                queue.append(nxt)
    return seen


def default_size(types_count):
    return max(11, 4 * types_count + 9)


def generate_maze(types_count, size=None, seed=None, loops=0.05, strict=True):
    """Generate a random N x N maze with exactly T keys and T doors.

    Construction (solvable *by construction*, then re-verified with BFS):
      1. carve a random maze, S at the top-left, E at the last lattice cell
         (so E is also the last 'E' in row-major order -> no e/E ambiguity);
      2. take the S->E corridor and put the T doors on it, spread out evenly;
      3. put the key for door i in the region reachable from S while doors
         i..T are still closed (preferring dead ends, so detours are needed).
    With ``strict`` the shortest route must really collect all T keys.
    """
    if not 1 <= types_count <= 6:
        raise ValueError("T must be between 1 and 6.")
    n = size if size else default_size(types_count)
    if n < types_count + 7:
        raise ValueError(f"For T = {types_count} the grid must be at least {types_count + 7} x {types_count + 7}.")
    rng = random.Random(seed)
    last = (n - 1) - ((n - 1) % 2)
    exit_cell = (last, last)

    for attempt in range(600):
        p = loops if attempt < 40 else 0.0     # fall back to a pure tree maze
        grid = _carve(n, rng)
        if p:
            _braid(grid, rng, p)
        path = _shortest_cell_path(grid, (0, 0), exit_cell)
        length = len(path)
        if length - 2 < types_count:
            continue
        letters = list(KEY_LETTERS[:types_count])
        rng.shuffle(letters)
        indices = []
        for i in range(types_count):                       # stratified door positions
            lo = 1 + (length - 2) * i // types_count
            hi = 1 + (length - 2) * (i + 1) // types_count - 1
            indices.append(rng.randint(lo, max(lo, hi)))
        door_cells = [path[i] for i in indices]

        used = set(door_cells) | {(0, 0), exit_cell}
        key_cells, ok = [], True
        for i in range(types_count):
            blocked = set(door_cells[i:])
            region = [cell for cell in _region(grid, (0, 0), blocked) if cell not in used]
            if not region:
                ok = False
                break
            dead_ends = [cell for cell in region if sum(1 for _ in _neighbours(grid, *cell)) == 1]
            pool = dead_ends if dead_ends and rng.random() < 0.85 else region
            cell = rng.choice(sorted(pool))
            key_cells.append(cell)
            used.add(cell)
        if not ok:
            continue

        rows = [row[:] for row in grid]
        rows[0][0] = "S"
        rows[exit_cell[0]][exit_cell[1]] = "E"
        for letter, (dr, dc), (kr, kc) in zip(letters, door_cells, key_cells):
            rows[dr][dc] = letter.upper()
            rows[kr][kc] = letter
        maze = _validate(rows, types_count)
        result = solve_bfs(maze)
        if result.route is None:
            continue
        if strict:
            collected = {maze.grid[r][c] for r, c in result.route} & set(KEY_LETTERS)
            if len(collected) != types_count:
                continue
        return maze
    raise RuntimeError("Could not generate a maze; try a larger size or another seed.")


# --------------------------------------------------------------------------- #
#  Compiled grid shared by all solvers
# --------------------------------------------------------------------------- #
class _Compiled:
    """Flat-array view of a maze for fast searches."""

    def __init__(self, maze):
        n = maze.size
        self.n = n
        self.maze = maze
        self.bits = len(maze.keys)
        self.masks = 1 << self.bits
        bit = {k: 1 << i for i, k in enumerate(maze.keys)}
        self.need = [0] * (n * n)       # key bit required to ENTER the cell
        self.give = [0] * (n * n)       # key bit obtained by ENTERING the cell
        passable = [True] * (n * n)
        for r in range(n):
            for c in range(n):
                ch, i = maze.grid[r][c], r * n + c
                if ch == "#":
                    passable[i] = False
                elif ch in KEY_LETTERS:
                    self.give[i] = bit[ch]
                elif ch in DOOR_LETTERS and (r, c) != maze.exit:
                    b = bit.get(ch.lower())
                    if b is None:
                        passable[i] = False      # door whose key does not exist
                    else:
                        self.need[i] = b
        self.nbrs = [[] for _ in range(n * n)]
        for r in range(n):
            for c in range(n):
                if not passable[r * n + c]:
                    continue
                for dr, dc in MOVES:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < n and 0 <= nc < n and passable[nr * n + nc]:
                        self.nbrs[r * n + c].append(nr * n + nc)
        self.start = maze.start[0] * n + maze.start[1]
        self.exit = maze.exit[0] * n + maze.exit[1]
        self.heur = [abs(i // n - maze.exit[0]) + abs(i % n - maze.exit[1]) for i in range(n * n)]

    def route(self, parent, state):
        cells = []
        while state != ROOT:
            cells.append(divmod(state >> self.bits, self.n))
            state = parent[state]
        return cells[::-1]

    def cells_of(self, parent):
        seen = set()
        for state, p in enumerate(parent):
            if p != UNSEEN:
                seen.add(divmod(state >> self.bits, self.n))
        return frozenset(seen)


def _finish(name, cp, parent, goal, expanded, t0, capped=False):
    route = cp.route(parent, goal) if goal >= 0 else None
    return SolveResult(name, route, len(route) - 1 if route else -1, expanded,
                       (time.perf_counter() - t0) * 1000, cp.cells_of(parent), capped)


# --------------------------------------------------------------------------- #
#  Solvers
# --------------------------------------------------------------------------- #
def solve_bfs(maze):
    """Optimal: BFS over (cell, key-mask) states.  O(N^2 * 2^T) time and space."""
    t0 = time.perf_counter()
    cp = _Compiled(maze)
    bits, M = cp.bits, cp.masks
    parent = array("i", [UNSEEN]) * (cp.n * cp.n * M)
    root = cp.start << bits
    parent[root] = ROOT
    queue = deque([root])
    need, give, nbrs, goal_cell = cp.need, cp.give, cp.nbrs, cp.exit
    expanded, goal = 0, -1
    while queue and goal < 0:
        state = queue.popleft()
        expanded += 1
        cell, mask = state >> bits, state & (M - 1)
        for nb in nbrs[cell]:
            if need[nb] & ~mask:
                continue                               # door without its key
            nxt = (nb << bits) | (mask | give[nb])
            if parent[nxt] == UNSEEN:
                parent[nxt] = state
                if nb == goal_cell:                    # first discovery == shortest
                    goal = nxt
                    break
                queue.append(nxt)
    return _finish("BFS", cp, parent, goal, expanded, t0)


def solve_astar(maze):
    """Optimal: A* with the Manhattan distance to E (admissible and consistent)."""
    t0 = time.perf_counter()
    cp = _Compiled(maze)
    bits, M = cp.bits, cp.masks
    size = cp.n * cp.n * M
    parent = array("i", [UNSEEN]) * size
    g = array("i", [INF]) * size
    root = cp.start << bits
    parent[root], g[root] = ROOT, 0
    heap = [(cp.heur[cp.start], 0, root)]
    need, give, nbrs, heur = cp.need, cp.give, cp.nbrs, cp.heur
    expanded, goal = 0, -1
    while heap:
        f, _, state = heapq.heappop(heap)
        cell, mask = state >> bits, state & (M - 1)
        if f > g[state] + heur[cell]:
            continue                                   # stale heap entry
        expanded += 1
        if cell == cp.exit:
            goal = state
            break
        ng = g[state] + 1
        for nb in nbrs[cell]:
            if need[nb] & ~mask:
                continue
            nxt = (nb << bits) | (mask | give[nb])
            if ng < g[nxt]:
                g[nxt], parent[nxt] = ng, state
                heapq.heappush(heap, (ng + heur[nb], -ng, nxt))
    return _finish("A*", cp, parent, goal, expanded, t0)


def solve_dfs(maze, cap=400_000):
    """Optimal but wasteful: depth-first search that re-expands a state whenever a
    shorter way to it is found.  Included to show why BFS is the right tool."""
    t0 = time.perf_counter()
    cp = _Compiled(maze)
    bits, M = cp.bits, cp.masks
    size = cp.n * cp.n * M
    parent = array("i", [UNSEEN]) * size
    depth = array("i", [INF]) * size
    root = cp.start << bits
    parent[root], depth[root] = ROOT, 0
    stack = [root]
    need, give, nbrs = cp.need, cp.give, cp.nbrs
    expanded, best, goal, capped = 0, INF, -1, False
    while stack:
        if expanded >= cap:
            capped = True
            break
        state = stack.pop()
        expanded += 1
        cell, mask, d = state >> bits, state & (M - 1), depth[state]
        if cell == cp.exit:
            if d < best:
                best, goal = d, state
            continue
        if d + 1 >= best:
            continue
        for nb in nbrs[cell]:
            if need[nb] & ~mask:
                continue
            nxt = (nb << bits) | (mask | give[nb])
            if d + 1 < depth[nxt]:
                depth[nxt], parent[nxt] = d + 1, state
                stack.append(nxt)
    return _finish("DFS", cp, parent, goal, expanded, t0, capped)


def solve_naive(maze):
    """INCORRECT baseline for demonstration: BFS that remembers visited *cells*
    only.  It cannot come back through a cell it has already used, even though
    the new key mask would make that worthwhile (see samples/sample_revisit.csv)."""
    t0 = time.perf_counter()
    cp = _Compiled(maze)
    bits, M = cp.bits, cp.masks
    parent = array("i", [UNSEEN]) * (cp.n * cp.n * M)
    seen = bytearray(cp.n * cp.n)
    root = cp.start << bits
    parent[root], seen[cp.start] = ROOT, 1
    queue = deque([root])
    expanded, goal = 0, -1
    while queue and goal < 0:
        state = queue.popleft()
        expanded += 1
        cell, mask = state >> bits, state & (M - 1)
        for nb in cp.nbrs[cell]:
            if cp.need[nb] & ~mask or seen[nb]:
                continue
            seen[nb] = 1
            nxt = (nb << bits) | (mask | cp.give[nb])
            parent[nxt] = state
            if nb == cp.exit:
                goal = nxt
                break
            queue.append(nxt)
    return _finish("Naive (cell-only visited)", cp, parent, goal, expanded, t0)


def solve_key_graph(maze):
    """Independent oracle: Dijkstra over 'key events'.

    Nodes are (key cell just collected, key mask).  Edge weights come from plain
    BFS runs on the grid with the mask frozen.  Only returns the length (route=None);
    used by the tests and the benchmark to cross-check the main algorithms.
    """
    t0 = time.perf_counter()
    cp = _Compiled(maze)
    n, bits = cp.n, cp.bits
    key_cells = [i for i in range(n * n) if cp.give[i]]
    index = {cell: k + 1 for k, cell in enumerate(key_cells)}      # 0 is the start

    def distances(src, mask):
        dist = {src: 0}
        queue = deque([src])
        while queue:
            cur = queue.popleft()
            for nb in cp.nbrs[cur]:
                if nb not in dist and not (cp.need[nb] & ~mask):
                    dist[nb] = dist[cur] + 1
                    queue.append(nb)
        return dist

    cells = [cp.start] + key_cells
    best = {(0, 0): 0}
    heap = [(0, 0, 0)]
    answer, expanded = INF, 0
    while heap:
        d, node, mask = heapq.heappop(heap)
        if d > best.get((node, mask), INF) or d >= answer:
            continue
        expanded += 1
        dist = distances(cells[node], mask)
        if cp.exit in dist:
            answer = min(answer, d + dist[cp.exit])
        for cell in key_cells:
            if cell in dist and not (cp.give[cell] & mask):
                state = (index[cell], mask | cp.give[cell])
                nd = d + dist[cell]
                if nd < best.get(state, INF):
                    best[state] = nd
                    heapq.heappush(heap, (nd, *state))
    length = -1 if answer == INF else answer
    return SolveResult("Key-graph Dijkstra", None, length, expanded, (time.perf_counter() - t0) * 1000)


ALGORITHMS = {"bfs": solve_bfs, "astar": solve_astar, "dfs": solve_dfs,
              "naive": solve_naive, "keygraph": solve_key_graph}


def solve(maze, algorithm="bfs"):
    return ALGORITHMS[algorithm](maze)


def solve_maze(maze):
    """Shortest route as a list of (row, col), or None when E is unreachable."""
    return solve_bfs(maze).route


# --------------------------------------------------------------------------- #
#  Route checking, description and output files
# --------------------------------------------------------------------------- #
def verify_route(maze, route):
    """Replay a route under the game rules.  Raises ValueError on any violation."""
    if not route or route[0] != maze.start or route[-1] != maze.exit:
        raise ValueError("A route must start at S and end at E.")
    held = set()
    for i, (r, c) in enumerate(route):
        if i:
            pr, pc = route[i - 1]
            if abs(pr - r) + abs(pc - c) != 1:
                raise ValueError(f"Step {i} is not a one-cell move.")
        ch = maze.grid[r][c]
        if ch == "#":
            raise ValueError(f"Step {i} walks into a wall.")
        if ch in DOOR_LETTERS and (r, c) != maze.exit and ch.lower() not in held:
            raise ValueError(f"Step {i} enters door {ch} without key {ch.lower()}.")
        if ch in KEY_LETTERS:
            held.add(ch)
    return True


def describe_route(maze, route):
    """Annotate each step of a route with the event it triggers."""
    steps, held, picked, opened = [], set(), set(), set()
    for i, (r, c) in enumerate(route or []):
        ch = maze.grid[r][c]
        kind, note = "move", ""
        if i == 0:
            kind, note = "start", "Start"
        elif (r, c) == maze.exit:
            kind, note = "exit", "Reached the exit"
        elif ch in KEY_LETTERS and (r, c) not in picked:
            picked.add((r, c))
            held.add(ch)
            kind, note = "key", f"Picked up key {ch}"
        elif ch in DOOR_LETTERS and (r, c) not in opened:
            opened.add((r, c))
            kind, note = "door", f"Opened door {ch} with key {ch.lower()}"
        steps.append(Step(i, (r, c), ch, kind, "".join(sorted(held)), note))
    return steps


def write_marked_path_csv(maze, path, output_csv):
    """Mark ordinary route cells with 'x'.  S, E, keys and doors keep their symbols
    so every pick-up and door opening along the route stays identifiable."""
    route = set(path or [])
    output = [[("x" if (r, c) in route and cell == "." else cell)
               for c, cell in enumerate(row)] for r, row in enumerate(maze.grid)]
    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f, lineterminator="\n").writerows(output)
    return output_path


def write_steps_csv(maze, route, output_csv):
    """Step-by-step log: step, row, col (1-based), cell, event, keys held."""
    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["step", "row", "col", "cell", "event", "keys_held"])
        for s in describe_route(maze, route):
            writer.writerow([s.index, s.pos[0] + 1, s.pos[1] + 1, s.symbol, s.note, s.held])
    return output_path
