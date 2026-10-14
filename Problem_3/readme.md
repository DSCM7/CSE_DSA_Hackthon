# Budget Traveller with Coupons (Problem 3)

Travel from city 1 to city N on one-way flights with at most **K stops** (so at most K + 1 flights). You hold **C coupons**; each halves one flight's price (rounded down), at most one coupon per flight. Output the minimum cost, or -1.

## Run it

```
python Budget_Traveller_with_Coupons.py              # opens route.html when done
python Budget_Traveller_with_Coupons.py --no-browser # don't open the browser
python Budget_Traveller_with_Coupons.py --quick      # smaller stress test / benchmarks
```

| Option | What you type |
|---|---|
| 1 | `N M`, then `K C`, then M lines `u v p` |
| 2 | `K C`, a CSV filename (`from,to,price` rows), and optionally N (default: largest city id in the file) |
| 3 | N, then `K C`, edge density, optional seed (the graph is saved to `flights.csv`) |

## Outputs

| File | Contents |
|---|---|
| console | **Output 1**: minimum cost (or -1), route, coupon flights, timings |
| `result.csv` | **Output 2**: the whole graph; chosen path marked `x`, `leg_no` gives the order, `coupon_used` flags coupon flights, `price_paid` shows the discounted fare |
| `route.html` | Visualization dashboard (below) |
| `flights.csv` | Generated graph (option 3) |
| `benchmark.csv`, `benchmark_k.csv` | Runtime vs N, and runtime vs K |

## Visualization (`route.html`, self-contained, light/dark aware)

* **Journey**: directed weighted graph, start green, destination red, intermediate stops orange. A plane flies the route; the edge turns **gold** when a coupon is applied and the price label changes to `original → discounted`. Live running cost, stops-used pips (out of K), coupon tickets (out of C), itinerary ledger with total savings. Play/pause/step, speed, left-to-right or circle layout, hover a city to see its flights.
* **What-if explorer**: K and C sliders re-solve in the browser; heat-map of cost by flights x coupons from the DP table; cost-vs-K and cost-vs-C charts.
* **Algorithm analysis**: comparison table, runtime charts, correctness argument.
* **Corner cases**: 21 named cases with expected value, DP, Dijkstra and brute-force results.

## Algorithms (comparative analysis)

1. **Layered DP (primary)**: state = (city, flights used, coupons used). `O((K+1)(C+1)(N+M))` time.
2. **Dijkstra on expanded states**: same states, heap-ordered, stops when N is popped. Adds a log factor in the worst case.
3. **Brute-force DFS**: every walk of <= K+1 flights, every coupon choice. `O((2M)^(K+1))`. Ground truth for small inputs only.
4. **Greedy baseline (deliberately wrong)**: cheapest-fare path, then coupons on its biggest fares. Example: 1->2 (30), 2->3 (30), 1->3 (80), K=1, C=1: greedy gives 45, optimum is 40.

**Measured honestly:** on the random benchmark graphs Dijkstra is usually *faster* than the layered DP, because it exits as soon as city N is reached while the DP scans every layer. The DP is kept as the primary method for its predictable worst case, simple proof, and because its table powers the what-if heat-map. Brute force falls behind quickly as K grows.

## Correctness argument

* A trip's remaining cost depends only on (current city, flights used, coupons used), so the DP state loses no information.
* Induction on layers: if layer t holds the true minimum for every (city, coupons) reachable in t flights, relaxing every outgoing flight with both payment choices gives the true minimum for layer t+1 (a cheapest walk has a cheapest prefix).
* Answer = minimum over layers 1..K+1 at city N; no state at N means -1.

## Verification built into the program

* 21 corner cases run at every start-up (direct flight, odd fare 9 -> 4, K = 0 blocking a 2-flight route, no flights, one-way only, unreachable N, one coupon per flight, more coupons than flights, zero-price flights, parallel flights, cycles, stop limit forcing a pricier direct flight, a coupon changing the winning route, greedy trap, K larger than needed, very large prices).
* Randomised stress test (2000 tiny graphs, zero and odd prices): DP = Dijkstra = brute force on every instance, and every returned route is re-validated (connected walk from 1 to N, <= K+1 flights, <= C coupons, recomputed cost).
* The browser solver in `route.html` is checked against the Python answer (badge in the header).
