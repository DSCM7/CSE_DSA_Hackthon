"""Capacity-constrained graph colouring: Welsh-Powell, DSatur, exact branch-and-bound.

Model: courses = vertices, conflicts = edges, slots = colours, and every colour
class (slot) holds at most R vertices.
"""
import sys
from math import ceil
from time import perf_counter


# ----------------------------------------------------------------- utilities
def validate(graph, assignment):
    """Independent checker. Returns a list of problems (empty list = valid timetable)."""
    if len(assignment) != graph.n:
        return ["assignment length differs from N"]
    problems = []
    if any(slot < 0 for slot in assignment):
        problems.append("some course is unassigned")
    for u, v in graph.edges:
        if assignment[u] == assignment[v]:
            problems.append(f"courses {u + 1} and {v + 1} conflict but share slot {assignment[u] + 1}")
    counts = {}
    for slot in assignment:
        counts[slot] = counts.get(slot, 0) + 1
    for slot, count in counts.items():
        if count > graph.capacity:
            problems.append(f"slot {slot + 1} holds {count} exams, more than R={graph.capacity}")
    if sorted(counts) != list(range(len(counts))):
        problems.append("slot numbers are not contiguous")
    return problems


def _pack(name, assignment, order, started, **extra):
    return {"name": name, "assignment": tuple(assignment), "order": tuple(order),
            "slots": max(assignment, default=-1) + 1, "seconds": perf_counter() - started, **extra}


# ------------------------------------------------------------- lower bounds
def lower_bound_parts(graph):
    """(capacity bound, clique bound). Both are valid lower bounds on the slot count.

    * ceil(N/R): every slot holds at most R exams.
    * clique size: the courses of a clique pairwise conflict, so each needs its own slot.
    """
    capacity_bound = ceil(graph.n / graph.capacity)
    order = sorted(range(graph.n), key=lambda v: (-len(graph.adjacency[v]), v))
    starts = order if graph.n <= 200 else order[:100]
    clique_bound = 1
    for start in starts:
        clique = [start]
        for candidate in order:
            if candidate != start and all(candidate in graph.adjacency[v] for v in clique):
                clique.append(candidate)
        clique_bound = max(clique_bound, len(clique))
    return capacity_bound, clique_bound


def lower_bound(graph):
    return max(lower_bound_parts(graph))


# ------------------------------------------------------------------ greedy 1
def welsh_powell(graph):
    """Welsh-Powell: sort by degree, then fill one slot at a time with non-conflicting courses."""
    started = perf_counter()
    adj = graph.adjacency
    left = sorted(range(graph.n), key=lambda v: (-len(adj[v]), v))
    assignment = [-1] * graph.n
    order, slot = [], 0
    while left:
        members, rest = [], []
        for v in left:
            if len(members) < graph.capacity and not any(u in adj[v] for u in members):
                members.append(v)
            else:
                rest.append(v)
        for v in members:
            assignment[v] = slot
            order.append(v)
        left, slot = rest, slot + 1
    return _pack("Welsh-Powell", assignment, order, started)


# ------------------------------------------------------------------ greedy 2
def dsatur(graph):
    """DSatur: next course = most distinct neighbour slots (saturation), ties by degree."""
    started = perf_counter()
    adj, n = graph.adjacency, graph.n
    assignment = [-1] * n
    saturation = [set() for _ in range(n)]
    sizes, order = [], []
    remaining = set(range(n))
    while remaining:
        v = max(remaining, key=lambda c: (len(saturation[c]), len(adj[c]), -c))
        slot = next((s for s in range(len(sizes))
                     if sizes[s] < graph.capacity and s not in saturation[v]), len(sizes))
        if slot == len(sizes):
            sizes.append(0)
        assignment[v] = slot
        sizes[slot] += 1
        order.append(v)
        remaining.discard(v)
        for u in adj[v]:
            saturation[u].add(slot)
    return _pack("DSatur", assignment, order, started)


# --------------------------------------------------------------------- exact
def exact_branch_and_bound(graph, time_limit=10.0, initial=None):
    """Exact minimum number of slots (anytime: returns best found if time runs out).

    Search = DSatur-ordered backtracking. A course goes into an existing legal slot or
    into exactly one new slot (slot-label symmetry removed). Pruning:
      1. used >= best                       (cannot improve),
      2. used + ceil(max(0, left - free)/R) >= best   (hall-capacity bound),
      3. stop as soon as best == global lower bound (proof of optimality).
    """
    if time_limit <= 0:
        raise ValueError("Exact solver time limit must be greater than zero.")
    started = perf_counter()
    n, R, adj = graph.n, graph.capacity, graph.adjacency
    if initial is None:
        initial = min((dsatur(graph), welsh_powell(graph)), key=lambda r: r["slots"])
    best, best_order, best_count = list(initial["assignment"]), list(initial["order"]), initial["slots"]
    cap_bound, clique_bound = lower_bound_parts(graph)
    bound = max(cap_bound, clique_bound)
    if best_count == bound:
        return _pack("Exact B&B", best, best_order, started, proven_optimal=True,
                     lower_bound=bound, nodes=0, timed_out=False)

    assign = [-1] * n
    sat = [dict() for _ in range(n)]      # sat[v][slot] = neighbours of v already in slot
    sizes, order = [], []
    state = {"nodes": 0, "stopped": False, "done": False}
    sys.setrecursionlimit(max(sys.getrecursionlimit(), n + 500))

    def search(used):
        nonlocal best, best_order, best_count
        state["nodes"] += 1
        if state["nodes"] & 255 == 0 and perf_counter() - started >= time_limit:
            state["stopped"] = True
        if state["stopped"] or state["done"]:
            return
        colored = len(order)
        if colored == n:
            if used < best_count:
                best, best_order, best_count = assign.copy(), order.copy(), used
                if best_count == bound:
                    state["done"] = True
            return
        if used >= best_count:
            return
        free = used * R - colored
        if used + ceil(max(0, n - colored - free) / R) >= best_count:
            return
        v = max((c for c in range(n) if assign[c] < 0),
                key=lambda c: (len(sat[c]), len(adj[c]), -c))
        options = [s for s in range(used) if s not in sat[v] and sizes[s] < R]
        options.sort(key=lambda s: (-sizes[s], s))          # fill fuller slots first
        if used + 1 < best_count:
            options.append(used)                             # the single "new slot" branch
        for s in options:
            new = s == used
            assign[v] = s
            order.append(v)
            if new:
                sizes.append(1)
            else:
                sizes[s] += 1
            for u in adj[v]:
                sat[u][s] = sat[u].get(s, 0) + 1
            search(used + 1 if new else used)
            for u in adj[v]:
                sat[u][s] -= 1
                if not sat[u][s]:
                    del sat[u][s]
            if new:
                sizes.pop()
            else:
                sizes[s] -= 1
            order.pop()
            assign[v] = -1
            if state["stopped"] or state["done"]:
                return

    search(0)
    return _pack("Exact B&B", best, best_order, started,
                 proven_optimal=(not state["stopped"]) or state["done"],
                 lower_bound=bound, nodes=state["nodes"], timed_out=state["stopped"])
