# Problem 2: Closest Pair of Points - Comparative Analysis

Finds the closest pair among N random points on a 2D plane using two algorithms,
compares their running time, verifies that they always agree, and visualises everything.

| Algorithm | Idea | Complexity |
|---|---|---|
| Brute-Force | Check every one of the N(N-1)/2 pairs | O(N^2) |
| Divide-and-Conquer | Sort by x, split at the median, solve both halves, then check only the strip of width 2d around the split line (each strip point against a few neighbours in y order) | O(N log N) |

## Requirements

- Java 8 or newer (tested on Java 21)
- A desktop environment for the GUI (without one, the program prints the results and exits)

## How to run

```bash
javac Main.java
java Main            # then type N and press Enter
java Main 12345      # optional: a numeric seed to reproduce the same points
```

The prompt "Enter number of points N" is written to stderr so that stdout contains only the results.

## Input

- **Standard input:** one integer `N`.
- The N points are generated randomly with integer coordinates in `[0, max(1000, 10N)]`.
- `N` must be at least 2 and at most 200,000 (brute force is O(N^2)).

## Output (stdout)

Exactly three lines:

```
6.082763 (808, 1496) (814, 1495)      <- Brute-Force: distance (6 decimals), then the two points
6.082763 (808, 1496) (814, 1495)      <- Divide-and-Conquer: same format
1.234 ms 0.456 ms                     <- execution time: Brute-Force, Divide-and-Conquer
```

- Each pair is printed in a fixed order (by x, then y), so identical pairs print identically.
- If several pairs tie for the minimum, the two algorithms may report different pairs with the same distance.
- Invalid input prints one message and exits: `Invalid input: N must be an integer.` or `N must be at least 2: ...`.

## Corner cases handled

N < 2, N = 2, N = 3, duplicate points, all points identical, collinear points
(horizontal, vertical, diagonal), points sharing the same x or y, lattice grids with
many equal distances, and floating-point coordinates (in the tests).

## Visualization (GUI)

A dark-themed window opens after the results are printed. Header cards show both distances,
pairs and times, the speed-up, and a MATCH/MISMATCH badge for the two distances.

| Tab | Contents |
|---|---|
| Overview | All points; Brute-Force pair in red, Divide-and-Conquer pair in blue, each joined by a line |
| Brute Force | Its closest pair and the number of pairs checked |
| Divide & Conquer | Dividing line (green dashed), strip region of width 2d (yellow), points inside the strip, closest pair |
| Animation | Step-by-step recursion: divide, base case, combine (with strip). Play/Pause, Prev, Next, Restart, slider, speed 0.5x-4x |
| Performance | Running time vs N for both algorithms (linear or log scale, hover tooltip) plus a table with speed-ups |
| Verification | Randomized test suite comparing both algorithms across 12 scenarios |

Plot controls: **scroll** to zoom, **drag** to pan, **double-click** to reset, **hover** a point to see its coordinates.

## Performance analysis

The Performance tab times both algorithms on random inputs of N = 100, 250, 500, 1000, 2000,
4000, 8000, 12000, 16000 (best of several runs, after a JIT warm-up).

- For small N (up to roughly 1000) brute force is as fast or faster, because it has no sorting or recursion overhead.
- Beyond that, Divide-and-Conquer wins and the gap keeps widening, matching O(N^2) vs O(N log N).
- Example single run with N = 100,000: Brute-Force about 6.3 s, Divide-and-Conquer about 160 ms.

Exact timings depend on your machine.

## Verification

Both algorithms are cross-checked on 3,060 randomized trials. A trial passes when:

1. the two minimum distances agree (tolerance 1e-9), and
2. each reported pair consists of two different points that really are that far apart.

For N < 2 the check requires both algorithms to return "no pair".

## Code layout (`Main.java`)

- `brute`, `divideConquer`, `rec`: the two algorithms (squared distances internally, square root only for output)
- `Anim`: replays the recursion as a list of steps for the animation tab
- `benchmark`, `timeMs`, `warmUp`: timing
- `Plot` and its subclasses, `PerfChart`, `AnimPage`, `VerifyPage`: the GUI
- `main`: reads N, runs both algorithms, prints the three lines, opens the window