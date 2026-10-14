# Problem 1 - Analysis

## 1. Modelling

Reaching a cell is not enough: *what you hold* decides which doors you may pass later. The search state is

```
state = (row, col, mask)        mask = bit i set  <=>  key i has been picked up
```

with one bit per key type present (`T <= 6`, so at most 64 masks).

* **Start:** `(S, 0)`. **Goal:** any state whose cell is `E`.
* **Move** from `(r, c, m)` to a neighbour `(r', c')` that is inside the grid and not `#`, and, if it is a door `X`, requires `bit(x)` in `m`. The new mask is `m | bit(key at (r', c'))`, which is `m` unless the cell holds a key.
* Every move costs 1, so the length of a route is the number of edges in the state graph.

```
BFS((S, 0)):
    queue <- [(S, 0)];  parent[(S, 0)] <- root
    while queue not empty:
        (cell, m) <- pop front
        for each neighbour n of cell that is not a wall:
            if n is a door and its key bit not in m: skip
            m' <- m | keybit(n)
            if (n, m') not seen:  parent[(n, m')] <- (cell, m');  if n == E: stop;  push
    rebuild the route by following parent pointers back to the root
```

The code stops as soon as a state on `E` is *discovered* (not popped). This is still optimal because BFS discovers states in non-decreasing distance order.

## 2. Proof that the answer is optimal

**Lemma 1 (the state is sufficient).** Which moves are legal after some prefix of a route depends only on the current cell and the set of keys collected so far, because keys are never consumed and the grid never changes. Hence two prefixes that end in the same `(cell, mask)` have exactly the same possible futures, and the walk problem is equivalent to a path problem in the state graph.

**Lemma 2 (bijection).** Every legal walk from `S` in the maze maps to exactly one path from `(S, 0)` in the state graph (follow the mask updates), and every state-graph path maps back to a legal walk. Lengths are preserved.

**Theorem.** BFS returns the length of the shortest legal walk from `S` to `E`, or reports that none exists.

*Proof.* The state graph is unweighted, so BFS finds a shortest path from `(S, 0)` to the set of goal states (standard BFS invariant: states leave the queue in non-decreasing distance order, and the first discovery of a state happens along a shortest path). By Lemma 2 this is the shortest legal walk. If no goal state is reachable BFS exhausts the finite graph and returns `-1`. The route is rebuilt from `parent` pointers, each of which was set when the state was first discovered, so it is a valid path of that length. The program additionally replays the route under the game rules (`verify_route`) before printing. ∎

**Why a plain visited-cell array is wrong.** A cell visited with one key set may have to be visited again with a bigger one. In `samples/sample_revisit.csv`

```
S . A E
# a # #
```

the only route is `S -> . -> a -> . -> A -> E`: the cell next to `S` is used twice, first without and then with key `a`. A BFS that marks cells as visited returns `-1`; the correct answer is 5. The implementation `solve_naive` demonstrates this: on 120 random mazes it was wrong 43 % of the time (`python analysis.py`).

## 3. Complexity

* **States:** at most `N^2 * 2^T`. **Edges:** at most 4 per state.
* **Time:** `O(N^2 * 2^T)`. **Space:** `O(N^2 * 2^T)` for the parent table (an `array('i')` of `N^2 * 2^T` entries, 4 bytes each).
* With the problem's limit `T <= 6` this is at most `64 N^2`, i.e. linear in the number of cells.

**Empirical check (worst case).** Open grid, all keys reachable, exit sealed off so BFS must exhaust the state space:

| N | T | open cells | states expanded | cells x 2^T |
|---|---|---|---|---|
| 21 | 3 | 438 | 3,492 | 3,504 |
| 21 | 6 | 438 | 27,840 | 28,032 |
| 41 | 3 | 1,678 | 13,412 | 13,424 |
| 41 | 6 | 1,678 | 107,200 | 107,392 |

The measured count equals `cells * 2^T` (minus the few states that are unreachable), so the bound is tight.

**Can the `2^T` be avoided?** Choosing which keys to fetch, and in what order, generalises the travelling-salesman problem on grid graphs, so for unbounded `T` an exponential dependence on `T` is expected to be unavoidable. For `T <= 6` it is a constant factor of at most 64. The `N^2` factor is also necessary: in the worst case every cell must be inspected.

**Why BFS and not Dijkstra.** All edges have weight 1. Dijkstra gives the same answer with an extra `log` factor and heap overhead.

## 4. Corner cases

| Case | Expected | Handled by / test |
|---|---|---|
| Key hidden behind its own door | `-1` | state graph never reaches it - `sample_locked_key.csv` |
| Optimal route revisits a cell with a bigger key set | found | state includes the mask - `sample_revisit.csv` |
| Key present but not needed | key ignored | `sample_no_key_needed.csv` |
| Several doors / several keys of the same type | each door opens with the one key; extra key cells are harmless | `test_duplicate_keys_and_doors` |
| Chain of doors needing keys in order | found | `test_chain_of_doors` |
| Door whose key does not exist | behaves as a wall, note printed | `test_door_without_any_key_is_a_wall` |
| Key without a door | harmless, note printed | parser warnings |
| Exit walled off or no open neighbour | `-1`, output CSV has no `x`, window shows reachable region | `test_unreachable_exit_walled_off` |
| `S` adjacent to `E` | 1 | `test_start_next_to_exit` |
| `E` is also the door of key `e` | last `E` in row-major order is the exit | `SymbolCollision` tests |
| All six types (`T = 6`) | works, 64 masks | `test_six_types` |
| T given on stdin differs from the grid | note, not an error | `test_t_mismatch_is_a_warning` |
| Not square, bad symbol, empty cell, missing / duplicate `S` or `E`, empty file | clear error, exit code 1 | `Parsing` tests |
| BOM, CRLF line endings, compact rows (`S.aA`) | accepted | `test_compact_rows_and_bom_file` |
| Random generation for every T, many seeds, any size >= T+7 | exactly T keys and T doors, solvable, all keys used | `Generator` tests |

## 5. Comparative analysis

| Algorithm | Optimal? | Time | Notes |
|---|---|---|---|
| **BFS on `(cell, mask)`** (used) | yes | `O(N^2 2^T)` | simplest, no heuristic, stops at first discovery of `E` |
| **A\*** with Manhattan distance to `E` | yes (the heuristic is admissible and consistent: every move changes the distance by at most 1) | same worst case, far fewer states in practice | heap overhead; pays off on open mazes |
| **DFS with re-expansion** | yes, but only after exploring many longer routes | exponential in the worst case, capped in the benchmark | shows why depth-first is the wrong tool for shortest paths |
| **Naive BFS (visited = cells)** | **no** | `O(N^2)` | gives wrong answers (43 % of random mazes) |
| **Key-graph Dijkstra** | yes | `O(2^T * K * N^2)` for K keys | independent method (BFS between keys with a fixed mask); used as the correctness oracle |

Measured on random mazes (`python analysis.py`, mean of several seeds, T = 3, "open" = 30 % of interior walls removed):

| N | BFS ms / states | A\* ms / states | DFS ms / states |
|---|---|---|---|
| 17 | 0.24 / 319 | 0.18 / 70 | 0.71 / 1,429 |
| 33 | 1.04 / 1,492 | 0.65 / 158 | 19.5 / 43,761 |
| 51 | 3.06 / 4,090 | 1.68 / 294 | 47.5 / 94,064 (some runs hit the cap) |

* A\* expands roughly 5-15x fewer states than BFS on open mazes because the Manhattan heuristic pulls the search toward `E`.
* On perfect (tree) mazes there is a single corridor, so BFS, A\* and DFS expand nearly the same number of states and BFS is slightly faster (no heap).
* DFS is dramatically slower on open mazes because it re-expands states whenever it finds a shorter way to them.
* Running time grows roughly linearly with N^2 and mildly with T for mazes that can be solved early; the worst-case table above shows the `2^T` factor when the whole state space must be explored.

All four optimal methods returned identical lengths on 120 generated mazes and on 400 fuzz-generated small grids (the independent key-graph oracle included).

## 6. Random maze generator

1. Carve a random spanning-tree maze (randomised DFS), put `S` top-left and `E` at the last lattice cell, then remove a few interior walls (5 %) to create loops.
2. Take the shortest `S -> E` corridor and place the `T` doors on it, spread evenly, in random key order.
3. For door `i`, put its key in the region reachable from `S` while doors `i..T` are still closed (mostly in dead ends, so the runner has to detour and come back).
4. Validate with BFS and require that the shortest route collects **all** T keys; otherwise retry (finally falling back to a loop-free maze, where every door is mandatory).

Step 3 guarantees solvability by induction: key 1 is reachable with every door closed, key `i` is reachable once keys `1..i-1` have opened doors `1..i-1`. Step 4 re-verifies it.

## 7. Visualisation design

Everything required by the sheet is drawn from one list of events produced by `describe_route`: green start, red exit, black walls, white open cells; each pair has a colour that cannot be confused with those four; the route is tinted and a trail follows the runner; picked-up keys fade out and tick the key ring; doors fade to white and their padlock opens. The runner is hidden during a pick-up/unlock beat so the animation itself is visible. Playback state is a single frame index, so pausing, stepping backwards and restarting are exact.
