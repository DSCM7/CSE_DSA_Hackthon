# CSE Hackathon on Data Structures and Algorithms - Solutions

**Department of Computer Science and Engineering, CMRIT, Bangalore**
**Date:** 14 October 2026 | **Duration:** 9 am - 3 pm (6 hours)

This repository contains our solutions to **all four problem statements** of the hackathon. Every problem comes with a working solution, a corner-case analysis, a justification of optimality, a comparative analysis where applicable, and a visualisation.

---

## Problems at a glance

| # | Problem | Core idea | Language | Folder |
|---|---|---|---|---|
| 1 | Maze with Keys and Doors | BFS over `(row, col, key-set)` states, compared with A\*, DFS and a deliberately wrong naive BFS | Python | [`problem1_maze_keys_doors/`](problem1_maze_keys_doors/) |
| 2 | Closest Pair of Points | Brute-Force vs Divide-and-Conquer, with running-time comparison | [Java / Python] | [`problem2_closest_pair/`](problem2_closest_pair/) |
| 3 | Budget Traveller with Coupons | Cheapest route with at most K stops and C halving coupons | [Java / Python] | [`problem3_budget_traveller/`](problem3_budget_traveller/) |
| 4 | Exam Timetable Scheduling | Capacity-constrained graph colouring: Welsh-Powell, DSatur and exact Branch-and-Bound | Python | [`problem4_exam_timetable/`](problem4_exam_timetable/) |

Each folder has its own `README.md` with setup, input/output formats, algorithms and tests.

---

## Problem summaries

### Problem 1 - Maze with Keys and Doors
Find the shortest path from `S` to `E` in an N x N grid with walls, keys `a`-`f` and doors `A`-`F`.
* Search state includes the set of keys held, so the solver runs in `O(N^2 * 2^T)`.
* Random solvable maze generator with exactly `T` keys and `T` doors.
* Animated visualisation: key pick-ups, unlocking doors, key-inventory panel.
* Output: shortest length (or `-1`) and a CSV with the path marked by `x`.

### Problem 2 - Closest Pair of Points
Find the closest pair among N points in the plane with two algorithms and check that they agree.
* Brute-Force `O(N^2)` and Divide-and-Conquer `O(N log N)`. [Confirm against your code]
* Corner cases: duplicate points, collinear points, shared x or y, `N = 2`, `N < 2`.
* Visualisation: points, closest pair per algorithm, dividing line, strip of width `2d`, running time vs N.

### Problem 3 - Budget Traveller with Coupons
Travel from city 1 to city N on one-way flights with at most K stops and C coupons, each halving one flight's price (rounded down).
* Approach: [fill in, e.g. shortest path over states `(city, stops, coupons)`]
* Output: minimum cost (or `-1`) and a CSV of the graph with the chosen path and coupon flights marked.
* Visualisation: directed weighted graph, animated journey, coupon flights highlighted with original price to discounted price.

### Problem 4 - Exam Timetable Scheduling
Assign N courses to the fewest time slots with no conflicting courses together and at most R exams per slot.
* Welsh-Powell and DSatur heuristics against an exact Branch-and-Bound solver with lower-bound optimality proofs.
* Output: slots per algorithm, whether each is proven optimal, slot-wise timetable and a CSV timetable.
* Visualisation: coloured conflict graph, timetable grid, and a benchmark of slots and running time as N grows.

---

## Repository structure

```
.
├── README.md                      <- this file
├── problem1_maze_keys_doors/
│   ├── main.py  maze_solver.py  visualizer.py  analysis.py
│   ├── ANALYSIS.md  README.md  requirements.txt
│   ├── samples/  tests/
├── problem2_closest_pair/
│   └── ...
├── problem3_budget_traveller/
│   └── ...
└── problem4_exam_timetable/
    ├── main.py  graph_input.py  scheduler.py  visualization.py  tests.py
    ├── sample_graph.txt  README.md  requirements.txt
    └── docs/
```

---

## Getting started

Clone the repository and open the folder of the problem you want to run:

```bash
git clone <your-repo-url>
cd <repo-name>/problem4_exam_timetable      # or any other problem folder
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Python 3.10 or newer is recommended. For Java solutions, use JDK [version] and follow the instructions in that problem's README.

### Quick run commands

| Problem | Command |
|---|---|
| 1 | `python main.py --types 3 --random --seed 4` |
| 2 | [add command] |
| 3 | [add command] |
| 4 | `python main.py --file sample_graph.txt` |

### Running the tests

| Problem | Command |
|---|---|
| 1 | `python -m unittest discover -s tests -v` |
| 2 | [add command] |
| 3 | [add command] |
| 4 | `python tests.py` |

---

## What every solution includes

| Hackathon expectation | Where to find it |
|---|---|
| Working solution | the source files in each problem folder |
| Deep-dive analysis with corner cases | each problem's README (Problem 1 also has `ANALYSIS.md`) |
| Comparative analysis | Problem 1: BFS vs A\* vs DFS; Problem 2: Brute-Force vs Divide-and-Conquer; Problem 4: heuristics vs exact solver |
| Proof or justification of optimality | analysis sections and test suites that cross-check against independent solvers |
| Visualisation | Matplotlib / NetworkX animations and charts in each problem |

---

## Tech stack

* **Python** with `matplotlib`, `networkx` and `numpy` for visualisation and benchmarks
* **Java** [for the problem(s) solved in Java]
* Visual references used: [VisuAlgo](https://visualgo.net/en) and [Python Tutor](https://pythontutor.com/)

---

## Team

| Name | USN |
|---|---|
| Dhriti Setty C M | 1CR24CS058 |
| Divya Teja B | 1CR24CS062 |
| Bhavana | 1CR24CS044 |
| Bhagyashree | 1CR24CS042 |

---

## Acknowledgements

Thanks to the Department of Computer Science and Engineering, CMRIT, Bangalore, for organising the hackathon.
