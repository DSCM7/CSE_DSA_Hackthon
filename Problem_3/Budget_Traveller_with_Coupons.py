import csv
import heapq
import json
import random
import sys
import time
import webbrowser
from pathlib import Path


def read_csv(filename):
    """Read flights from a CSV with from,to,price columns."""
    flights = []

    with open(filename, "r", newline="", encoding="utf-8-sig") as file:
        reader = csv.reader(file)

        for line_number, row in enumerate(reader, start=1):
            if not row or all(not value.strip() for value in row):
                continue

            if row[0].strip().lower() in {"from", "u", "origin"}:
                continue

            if len(row) < 3:
                raise ValueError(
                    f"Line {line_number}: expected from,to,price."
                )

            try:
                origin, destination, price = map(
                    lambda value: int(value.strip()),
                    row[:3]
                )
            except ValueError:
                raise ValueError(
                    f"Line {line_number}: city numbers and price "
                    "must be whole numbers."
                )

            flights.append((origin, destination, price))

    return flights


def validate_flights(city_count, flights):
    if city_count < 2:
        raise ValueError("The number of cities must be at least 2.")

    for index, (origin, destination, price) in enumerate(flights, start=1):
        if not 1 <= origin <= city_count:
            raise ValueError(
                f"Flight {index}: origin must be between 1 and {city_count}."
            )
        if not 1 <= destination <= city_count:
            raise ValueError(
                f"Flight {index}: destination must be between 1 and "
                f"{city_count}."
            )
        if origin == destination:
            raise ValueError(
                f"Flight {index}: a flight must connect different cities."
            )
        if price < 0:
            raise ValueError(f"Flight {index}: price cannot be negative.")


def dynamic_programming(city_count, max_stops, coupon_count, flights):
    """
    Main algorithm: layered dynamic programming.

    Time: O((K + 1) * (C + 1) * (N + M))
    Space: O(N * (C + 1) + (K + 1) * N * (C + 1))
    """

    max_flights = max_stops + 1
    infinity = float("inf")

    # Store only flights leaving each city.
    outgoing = [[] for _ in range(city_count + 1)]

    for flight_index, (origin, destination, price) in enumerate(flights):
        outgoing[origin].append((flight_index, destination, price))

    # Current costs indexed by city and coupons already used.
    current_costs = [
        [infinity] * (coupon_count + 1)
        for _ in range(city_count + 1)
    ]
    current_costs[1][0] = 0

    # Save choices so we can rebuild the selected route later.
    parent = {}
    best_cost = infinity
    best_flight_count = None
    best_coupons_used = None

    for flights_taken in range(1, max_flights + 1):
        next_costs = [
            [infinity] * (coupon_count + 1)
            for _ in range(city_count + 1)
        ]

        for city in range(1, city_count + 1):
            for coupons_used in range(coupon_count + 1):
                cost_so_far = current_costs[city][coupons_used]

                if cost_so_far == infinity:
                    continue

                # Only check flights leaving the city we are currently in.
                for flight_index, destination, price in outgoing[city]:
                    choices = [(price, coupons_used, False)]

                    if coupons_used < coupon_count:
                        choices.append(
                            (price // 2, coupons_used + 1, True)
                        )

                    for paid_price, new_coupon_count, used_coupon in choices:
                        new_cost = cost_so_far + paid_price

                        if new_cost < next_costs[destination][new_coupon_count]:
                            next_costs[destination][new_coupon_count] = new_cost
                            parent[
                                (flights_taken, destination, new_coupon_count)
                            ] = (
                                city,
                                coupons_used,
                                flight_index,
                                used_coupon
                            )

        # Check all ways of reaching city N with this number of flights.
        for coupons_used, cost in enumerate(next_costs[city_count]):
            if cost < best_cost:
                best_cost = cost
                best_flight_count = flights_taken
                best_coupons_used = coupons_used

        current_costs = next_costs

    if best_flight_count is None:
        return None, []

    route = []
    city = city_count
    coupons_used = best_coupons_used

    for flights_taken in range(best_flight_count, 0, -1):
        previous_city, previous_coupon_count, flight_index, used_coupon = parent[
            (flights_taken, city, coupons_used)
        ]

        route.append({
            "flight_index": flight_index,
            "coupon_used": used_coupon
        })

        city = previous_city
        coupons_used = previous_coupon_count

    route.reverse()
    return int(best_cost), route


def dijkstra(city_count, max_stops, coupon_count, flights):
    """
    Independent cross-check using Dijkstra's algorithm.

    Each state tracks flights taken, current city, and coupons used.
    """

    max_flights = max_stops + 1
    outgoing = [[] for _ in range(city_count + 1)]

    for flight_index, (origin, destination, price) in enumerate(flights):
        outgoing[origin].append((flight_index, destination, price))

    start_state = (0, 1, 0)
    best_cost = {start_state: 0}
    parent = {}
    priority_queue = [(0, start_state)]

    while priority_queue:
        cost, state = heapq.heappop(priority_queue)

        if cost != best_cost.get(state):
            continue

        flights_taken, city, coupons_used = state

        if city == city_count:
            route = []

            while state != start_state:
                previous_state, flight_index, used_coupon = parent[state]
                route.append({
                    "flight_index": flight_index,
                    "coupon_used": used_coupon
                })
                state = previous_state

            route.reverse()
            return cost, route

        if flights_taken == max_flights:
            continue

        for flight_index, destination, price in outgoing[city]:
            choices = [(price, coupons_used, False)]

            if coupons_used < coupon_count:
                choices.append(
                    (price // 2, coupons_used + 1, True)
                )

            for paid_price, new_coupon_count, used_coupon in choices:
                next_state = (
                    flights_taken + 1,
                    destination,
                    new_coupon_count
                )
                new_cost = cost + paid_price

                if new_cost < best_cost.get(next_state, float("inf")):
                    best_cost[next_state] = new_cost
                    parent[next_state] = (
                        state,
                        flight_index,
                        used_coupon
                    )
                    heapq.heappush(
                        priority_queue,
                        (new_cost, next_state)
                    )

    return None, []


DASHBOARD_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Budget Traveller with Coupons</title>
<style>
:root{--bg:#f1f5f1;--card:#fff;--ink:#14231f;--mut:#5d6e68;--line:#dde6df;--navy:#12372f;--green:#1f9d63;--gold:#e0a21a;--red:#d9534f;--orange:#ef8f3a;--node:#e4ede7;--faint:#bccac2;--soft:#f5f8f5;--shadow:0 8px 26px #12372f12}
@media(prefers-color-scheme:dark){:root{--bg:#0d1714;--card:#14231f;--ink:#e6f0eb;--mut:#93a89f;--line:#24382f;--navy:#0a2923;--node:#26392f;--faint:#3d5248;--soft:#192b25;--shadow:0 8px 26px #0006}}
*{box-sizing:border-box}
body{margin:0;padding:22px;background:var(--bg);color:var(--ink);font:14.5px/1.5 Inter,system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1280px;margin:auto}
header{display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;padding:22px 26px;border-radius:18px;color:#fff;background:linear-gradient(120deg,var(--navy),#1b6a52)}
h1{margin:0;font-size:25px;letter-spacing:-.03em}
header p{margin:3px 0 0;color:#cfe4da;font-size:13px}
.badges{display:flex;gap:8px;flex-wrap:wrap}
.badge{padding:6px 12px;border:1px solid #ffffff55;border-radius:999px;font-size:12px;background:#ffffff14}
.badge.ok{background:#1f9d6340;border-color:#6fe0a8}.badge.warn{background:#e0a21a40;border-color:#f3cd74}
nav{display:flex;gap:6px;margin:16px 0 14px;flex-wrap:wrap}
nav button{padding:9px 16px;border:1px solid var(--line);border-radius:999px;background:var(--card);color:var(--ink);font-weight:700;cursor:pointer}
nav button.on{background:var(--navy);color:#fff;border-color:var(--navy)}
.hidden{display:none!important}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:14px}
.card,.panel{background:var(--card);border:1px solid var(--line);border-radius:15px;padding:16px;box-shadow:var(--shadow)}
.card label{display:block;color:var(--mut);font-size:11px;font-weight:800;letter-spacing:.08em;text-transform:uppercase}
.card strong{display:block;margin-top:3px;font-size:26px;letter-spacing:-.02em}
.card small{color:var(--mut);font-size:12px}
.pips{display:flex;gap:4px;flex-wrap:wrap;margin-top:6px;min-height:16px}
.pip{width:15px;height:15px;border-radius:50%;border:2px solid var(--faint);transition:.3s}
.pip.used{background:var(--orange);border-color:var(--orange)}
.tix{width:22px;height:15px;border-radius:4px;border:2px dashed var(--faint);transition:.3s}
.tix.used{background:var(--gold);border:2px solid var(--gold);opacity:.55}
.grid{display:grid;grid-template-columns:minmax(0,1.75fr) minmax(290px,.8fr);gap:14px}
h2{margin:0 0 3px;font-size:16px}h3{margin:18px 0 6px;font-size:14px}
.sub{margin:0 0 12px;color:var(--mut);font-size:12.5px}
.mapwrap{position:relative}
svg.map{display:block;width:100%;height:auto;border:1px solid var(--line);border-radius:12px;background:radial-gradient(ellipse at 50% 45%,var(--soft),var(--card) 80%)}
.edge{fill:none;stroke:var(--faint);stroke-width:1.6;opacity:var(--dim,.55);transition:opacity .2s}
.edge.route{opacity:.9}.edge.hl{opacity:1;stroke:var(--mut);stroke-width:2.4}
.ghost{fill:none;stroke:var(--navy);stroke-width:3.5;stroke-dasharray:2 7;stroke-linecap:round;opacity:.45}
@media(prefers-color-scheme:dark){.ghost{stroke:#9fd8c0}}
.ov{fill:none;stroke-width:5;stroke-linecap:round}.ov.paid{stroke:var(--green)}.ov.coupon{stroke:var(--gold)}
.lab{font:700 11.5px system-ui;fill:var(--mut);text-anchor:middle;paint-order:stroke;stroke:var(--card);stroke-width:5px;stroke-linejoin:round;pointer-events:none}
.lab.route{fill:var(--ink);font-size:13px}.lab.coupon{fill:#b07d00}
@media(prefers-color-scheme:dark){.lab.coupon{fill:#f2c04a}}
.node circle{fill:var(--node);stroke:var(--card);stroke-width:4;transition:.25s}
.node text{font:800 13px system-ui;fill:var(--ink);text-anchor:middle;dominant-baseline:central;pointer-events:none}
.node{cursor:pointer}
.node.start circle{fill:var(--green)}.node.end circle{fill:var(--red)}.node.stop circle{fill:var(--orange)}
.node.planned circle{stroke:var(--orange);stroke-width:4}
.node.start text,.node.end text,.node.stop text{fill:#fff}
.node .tag{font:700 10px system-ui;fill:var(--mut);dominant-baseline:auto}
.colhead{font:700 11px system-ui;fill:var(--mut);text-anchor:middle;letter-spacing:.06em;text-transform:uppercase}
.toast{position:absolute;left:50%;top:14px;transform:translate(-50%,-14px);padding:9px 16px;border-radius:999px;background:var(--gold);color:#2a1d00;font-weight:800;font-size:13px;box-shadow:0 8px 20px #0003;opacity:0;pointer-events:none;transition:.35s}
.toast.show{opacity:1;transform:translate(-50%,0)}
.legend{display:flex;flex-wrap:wrap;gap:6px 16px;margin:10px 0 0;color:var(--mut);font-size:12px}
.legend i{display:inline-block;width:11px;height:11px;border-radius:50%;margin-right:6px;vertical-align:-1px}
.controls{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:12px}
button.b{padding:8px 13px;border:0;border-radius:8px;background:var(--navy);color:#fff;font-weight:700;cursor:pointer}
button.b.sec{background:var(--soft);color:var(--ink);border:1px solid var(--line)}
select,input[type=range]{accent-color:var(--green)}
select{padding:7px;border-radius:8px;border:1px solid var(--line);background:var(--card);color:var(--ink)}
.controls label{font-size:12px;color:var(--mut);display:flex;align-items:center;gap:5px}
.sl{display:grid;grid-template-columns:90px 1fr 34px;align-items:center;gap:8px;margin:6px 0;font-size:13px}
.sl b{text-align:right}
.msg{margin:10px 0;padding:10px 12px;border-radius:10px;background:var(--soft);color:var(--mut);font-size:13px;min-height:44px}
.leg{display:grid;grid-template-columns:28px 1fr auto;gap:8px;align-items:center;padding:9px 10px;margin-bottom:7px;border:1px solid var(--line);border-radius:10px;font-size:13px;transition:.25s}
.leg .n{width:24px;height:24px;border-radius:50%;background:var(--soft);display:grid;place-items:center;font-size:11px;font-weight:800}
.leg.cur{border-color:var(--green);background:#1f9d6314}.leg.done .n{background:var(--green);color:#fff}
.leg.cp{border-left:4px solid var(--gold)}
.leg small{color:var(--mut)}.leg s{color:var(--mut)}
.chip{display:inline-block;padding:1px 7px;border-radius:999px;background:var(--gold);color:#2a1d00;font-size:10.5px;font-weight:800;margin-left:6px}
.tot{display:flex;justify-content:space-between;padding:6px 4px;font-size:13px;border-top:1px solid var(--line)}
.two{display:grid;grid-template-columns:1fr 1fr;gap:14px}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{padding:8px 9px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{color:var(--mut);font-size:11px;text-transform:uppercase;letter-spacing:.05em}
td.r,th.r{text-align:right}
.heat{width:auto}.heat th{white-space:nowrap}.heat td{text-align:center;font-weight:700;border:2px solid var(--card);border-radius:6px;min-width:56px}
.heat td.best{outline:3px solid var(--navy);outline-offset:-3px}
@media(prefers-color-scheme:dark){.heat td.best{outline-color:#fff}}
.pass{color:var(--green);font-weight:800}.fail{color:var(--red);font-weight:800}
svg.chart{width:100%;height:auto;display:block}
.ax{stroke:var(--mut);stroke-width:1}.gl{stroke:var(--line)}.tk{fill:var(--mut);font:11px system-ui}
details{border:1px solid var(--line);border-radius:10px;padding:10px 14px;margin:8px 0;background:var(--soft)}
summary{cursor:pointer;font-weight:700}
code{background:var(--soft);padding:1px 5px;border-radius:5px;font-size:12.5px}
.note{color:var(--mut);font-size:12.5px}
@media(max-width:900px){body{padding:10px}.grid,.two{grid-template-columns:1fr}.stats{grid-template-columns:repeat(2,1fr)}}
</style>
</head>
<body>
<main>
<header>
  <div><h1>✈ Budget Traveller with Coupons</h1>
  <p id="sub"></p></div>
  <div class="badges" id="badges"></div>
</header>
<nav id="tabs">
  <button data-t="journey" class="on">Journey</button>
  <button data-t="whatif">What-if explorer</button>
  <button data-t="analysis">Algorithm analysis</button>
  <button data-t="cases">Corner cases</button>
</nav>

<!-- JOURNEY -->
<section id="journey">
  <div class="stats">
    <div class="card"><label>Minimum total cost</label><strong id="sTotal">—</strong><small id="sSave"></small></div>
    <div class="card"><label>Running cost</label><strong id="sRun">0</strong><small id="sFlights"></small></div>
    <div class="card"><label>Stops used</label><strong id="sStops">0</strong><div class="pips" id="pStops"></div></div>
    <div class="card"><label>Coupons used</label><strong id="sCoup">0</strong><div class="pips" id="pCoup"></div></div>
  </div>
  <div class="grid">
    <div class="panel">
      <h2>Flight network</h2>
      <p class="sub">Hover a city to see its flights. Dotted line = planned route; the plane draws it green (full fare) or gold (coupon).</p>
      <div class="mapwrap"><svg class="map" id="map" viewBox="0 0 1000 600" role="img" aria-label="Flight network with animated route"></svg><div class="toast" id="toast"></div></div>
      <div class="legend">
        <span><i style="background:var(--green)"></i>Start</span><span><i style="background:var(--red)"></i>Destination</span>
        <span><i style="background:var(--orange)"></i>Intermediate stop</span><span><i style="background:var(--green);border-radius:3px"></i>Full-fare flight</span>
        <span><i style="background:var(--gold);border-radius:3px"></i>Coupon flight (price → discounted)</span>
      </div>
      <div class="controls">
        <button class="b sec" id="bPrev">◀ Prev</button><button class="b" id="bPlay">▶ Play</button>
        <button class="b sec" id="bNext">Next ▶</button><button class="b sec" id="bReset">↺ Restart</button>
        <label>Speed <select id="speed"><option value="0.5">0.5×</option><option value="1" selected>1×</option><option value="2">2×</option><option value="4">4×</option></select></label>
        <label>Layout <select id="layout"><option value="layers">Left → right layers</option><option value="circle">Circle</option></select></label>
        <label>Prices <select id="labels"><option value="route">Route only</option><option value="all">All flights</option></select></label>
        <label><input type="checkbox" id="others" checked> Other flights</label>
      </div>
    </div>
    <aside class="panel">
      <h2>What-if controls</h2>
      <p class="sub">Change K or C and the solver re-runs in your browser.</p>
      <div class="sl"><span>Stops K</span><input type="range" id="rK" min="0"><b id="vK"></b></div>
      <div class="sl"><span>Coupons C</span><input type="range" id="rC" min="0" max="10"><b id="vC"></b></div>
      <div class="msg" id="msg"></div>
      <h2>Itinerary</h2>
      <div id="legs"></div>
      <div id="totals"></div>
    </aside>
  </div>
</section>

<!-- WHAT-IF -->
<section id="whatif" class="hidden">
  <div class="panel" style="margin-bottom:14px">
    <h2>Cost by flights taken × coupons used</h2>
    <p class="sub">Each cell is the cheapest way to reach the destination with exactly that many flights and coupons (from the DP table). The outlined cell is the optimum for the current K and C. Use the sliders on the Journey tab to change them.</p>
    <div style="overflow-x:auto"><table class="heat" id="heat"></table></div>
  </div>
  <div class="two">
    <div class="panel"><h2>Cost vs. allowed stops K</h2><p class="sub" id="kNote"></p><svg class="chart" id="chK" viewBox="0 0 520 300"></svg></div>
    <div class="panel"><h2>Cost vs. coupons C</h2><p class="sub" id="cNote"></p><svg class="chart" id="chC" viewBox="0 0 520 300"></svg></div>
  </div>
</section>

<!-- ANALYSIS -->
<section id="analysis" class="hidden">
  <div class="stats" id="aStats"></div>
  <div class="panel" style="margin-bottom:14px">
    <h2>Comparative analysis</h2>
    <p class="sub">Four approaches on identical inputs. N cities, M flights, K max stops, C coupons.</p>
    <table id="cmp"></table>
  </div>
  <div class="two">
    <div class="panel"><h2>Runtime vs. graph size</h2><p class="sub" id="bnNote"></p><svg class="chart" id="chN" viewBox="0 0 520 300"></svg><div class="legend" id="lgN"></div></div>
    <div class="panel"><h2>Runtime vs. stop limit K</h2><p class="sub" id="bkNote"></p><svg class="chart" id="chBK" viewBox="0 0 520 300"></svg><div class="legend" id="lgBK"></div></div>
  </div>
  <div class="panel" style="margin-top:14px">
    <h2>Why this solution is optimal</h2>
    <details open><summary>1 · State space is complete</summary>
      <p>A trip is a walk of at most K+1 flights. Whatever the history, the future cost depends only on (current city, flights used, coupons used). Tracking exactly these three numbers loses no information, so DP over them is exact.</p></details>
    <details open><summary>2 · Induction over layers</summary>
      <p>Layer 0 holds only (city 1, 0 coupons) at cost 0. If layer t stores the true minimum cost for every (city, coupons) reachable in t flights, then layer t+1 is built by relaxing every outgoing flight with both choices (full fare, or ⌊p/2⌋ if a coupon is left). Any cheapest (t+1)-flight walk has a cheapest t-flight prefix (otherwise swap it for a cheaper one), so layer t+1 is also exact. The answer is the minimum over layers 1…K+1 at city N.</p></details>
    <details><summary>3 · Why plain Dijkstra on cities or a greedy coupon rule fails</summary>
      <p>Cheapest path ≠ cheapest path <i>within K+1 flights</i>, and the best coupon placement can change which path wins (a pricier path with one huge fare can beat the cheap path once halved). Concrete trap: flights 1→2 (30), 2→3 (30), 1→3 (80), K=1, C=1. Greedy takes the 60-fare path and halves one leg: 45. Optimal is the direct flight with the coupon: 40. Greedy can also return −1 when its cheapest path needs more flights than K+1 allows. The stress test above counts how often it is wrong.</p></details>
    <details><summary>4 · Why coupons never need “saving”</summary>
      <p>⌊p/2⌋ ≤ p, so spending a coupon never raises the cost. The DP still tracks the exact count because a coupon can be used only once per flight and at most C times overall, and the best flight for a coupon depends on the route.</p></details>
    <details><summary>5 · Complexity</summary>
      <p>Layered DP: <code>O((K+1)(C+1)(N+M))</code> time, <code>O((K+1)N(C+1))</code> space (parent table). Dijkstra on expanded states adds a log factor for the heap. Brute force is <code>O((2M)^(K+1))</code>, exponential in K.</p></details>
  </div>
</section>

<!-- CORNER CASES -->
<section id="cases" class="hidden">
  <div class="panel">
    <h2>Corner-case suite</h2>
    <p class="sub">Every case is run through DP, Dijkstra and brute force, and the returned route is independently re-validated (connected walk, ≤ K+1 flights, ≤ C coupons, cost recomputed).</p>
    <div style="overflow-x:auto"><table id="caseTable"></table></div>
  </div>
</section>
</main>

<script>
const D = __DATA__;
const N = D.n, F = D.flights;

/*CORE_START*/
function solveDP(F, N, K, C) {
  const INF = Infinity, out = Array.from({length: N + 1}, () => []);
  F.forEach((f, i) => out[f.from].push(i));
  const mk = () => Array.from({length: N + 1}, () => new Array(C + 1).fill(INF));
  let cur = mk(); cur[1][0] = 0;
  const par = [null], table = [null];
  let best = INF, bt = -1, bc = -1;
  for (let t = 1; t <= K + 1; t++) {
    const nxt = mk(), p = {};
    for (let v = 1; v <= N; v++) for (let c = 0; c <= C; c++) {
      const base = cur[v][c]; if (base === INF) continue;
      for (const i of out[v]) {
        const f = F[i];
        for (let use = 0; use <= 1; use++) {
          if (use && c === C) continue;
          const nc = c + use, cost = base + (use ? Math.floor(f.price / 2) : f.price);
          if (cost < nxt[f.to][nc]) { nxt[f.to][nc] = cost; p[f.to * (C + 1) + nc] = [v, c, i, use]; }
        }
      }
    }
    par.push(p); table.push(nxt[N].slice());
    for (let c = 0; c <= C; c++) if (nxt[N][c] < best) { best = nxt[N][c]; bt = t; bc = c; }
    cur = nxt;
  }
  if (bt < 0) return {best: null, route: [], table};
  const route = []; let v = N, c = bc;
  for (let t = bt; t >= 1; t--) {
    const [pv, pc, i, use] = par[t][v * (C + 1) + c];
    route.push({fi: i, coupon: !!use}); v = pv; c = pc;
  }
  route.reverse();
  return {best, route, table};
}
/*CORE_END*/

const $ = id => document.getElementById(id), NS = "http://www.w3.org/2000/svg";
const el = (tag, attrs = {}, text) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (text !== undefined) e.textContent = text; return e; };
const paid = (f, coupon) => coupon ? Math.floor(f.price / 2) : f.price;

/* ---------- state ---------- */
const S = {K: D.k, C: D.c, sol: null, route: [], done: 0, prog: 0, hold: 0, playing: false, last: 0, speed: 1, layout: "layers"};
const LEG_MS = 1500, HOLD_MS = 450;
let pts = [], eEl = [], eLab = [], eGeo = [], ghost = [], ov = [], ovLen = [], nodeEl = [], plane = null;

$("sub").textContent = `${N} cities · ${F.length} one-way flights · up to ${D.k} stops · ${D.c} coupons (python reference run)`;
$("rK").max = Math.max(0, N - 1); $("rK").value = S.K; $("rC").value = S.C;

/* ---------- layout ---------- */
function computeLayout(mode, routeNodes, routeSeq) {
  const p = new Array(N + 1);
  if (mode === "circle") {
    const cx = 500, cy = 300, rx = 400, ry = 235;
    p[1] = {x: cx - rx, y: cy}; p[N] = {x: cx + rx, y: cy};
    const onTop = routeSeq.length ? routeSeq : [], rest = [];
    for (let i = 2; i < N; i++) if (!onTop.includes(i)) rest.push(i);
    let topList = onTop.slice(), botList = rest;
    if (!topList.length) { const h = Math.ceil(rest.length / 2); topList = rest.slice(0, h); botList = rest.slice(h); }
    topList.forEach((v, idx) => { const a = Math.PI - Math.PI * (idx + 1) / (topList.length + 1); p[v] = {x: cx + rx * Math.cos(a), y: cy - ry * Math.sin(a)}; });
    botList.forEach((v, idx) => { const a = Math.PI + Math.PI * (idx + 1) / (botList.length + 1); p[v] = {x: cx + rx * Math.cos(a), y: cy - ry * Math.sin(a)}; });
    return {pts: p, heads: []};
  }
  const depth = new Array(N + 1).fill(-1); depth[1] = 0;
  const q = [1], adj = Array.from({length: N + 1}, () => []);
  F.forEach(f => adj[f.from].push(f.to));
  while (q.length) { const v = q.shift(); for (const w of adj[v]) if (depth[w] < 0) { depth[w] = depth[v] + 1; q.push(w); } }
  let maxd = 1; for (let v = 2; v < N; v++) if (depth[v] > maxd) maxd = depth[v];
  const col = new Array(N + 1);
  for (let v = 1; v <= N; v++) col[v] = v === 1 ? 0 : v === N ? maxd + 1 : (depth[v] < 0 ? maxd : Math.max(1, depth[v]));
  const ncol = maxd + 2, groups = Array.from({length: ncol}, () => []);
  for (let v = 1; v <= N; v++) groups[col[v]].push(v);
  const X0 = 60, X1 = 940;
  groups.forEach((g, ci) => {
    g.sort((a, b) => (routeNodes.has(a) ? 0 : 1) - (routeNodes.has(b) ? 0 : 1) || a - b);
    const n = g.length, ys = g.map((_, j) => n === 1 ? 300 : 70 + j * (460 / (n - 1)));
    const order = [...ys.keys()].sort((a, b) => Math.abs(a - (n - 1) / 2) - Math.abs(b - (n - 1) / 2) || a - b);
    g.forEach((v, i) => p[v] = {x: X0 + ci * (X1 - X0) / (ncol - 1), y: ys[order[i]]});
  });
  const heads = [{x: X0, t: "Start"}, {x: X1, t: "Destination"}];
  return {pts: p, heads};
}

/* ---------- build map ---------- */
function buildMap() {
  const svg = $("map"); svg.innerHTML = "";
  const routeIdx = new Map(S.route.map((l, i) => [l.fi, i]));
  const routeNodes = new Set([1, N]); S.route.forEach(l => routeNodes.add(F[l.fi].to));
  const L = computeLayout(S.layout, routeNodes, S.route.map(l => F[l.fi].to).filter(v => v !== N)); pts = L.pts;
  svg.style.setProperty('--dim', F.length > 40 ? 0.26 : 0.55);
  const defs = el("defs"); svg.appendChild(defs);
  L.heads.forEach(h => svg.appendChild(el("text", {x: h.x, y: 24, class: "colhead"}, h.t)));
  const R = 21; eEl = []; eLab = []; eGeo = [];
  const gE = el("g"), gO = el("g"), gL = el("g"), gN = el("g");
  [gE, gO, gL, gN].forEach(g => svg.appendChild(g));
  F.forEach((f, i) => {
    const a = pts[f.from], b = pts[f.to], dx = b.x - a.x, dy = b.y - a.y, len = Math.hypot(dx, dy) || 1;
    const ux = dx / len, uy = dy / len, off = Math.min(46, Math.max(16, len * 0.13));
    const x0 = a.x + ux * R, y0 = a.y + uy * R, x1 = b.x - ux * (R + 4), y1 = b.y - uy * (R + 4);
    const cx = (a.x + b.x) / 2 - uy * off, cy = (a.y + b.y) / 2 + ux * off;
    const d = `M${x0.toFixed(1)} ${y0.toFixed(1)} Q${cx.toFixed(1)} ${cy.toFixed(1)} ${x1.toFixed(1)} ${y1.toFixed(1)}`;
    const isR = routeIdx.has(i);
    const path = el("path", {d, class: "edge" + (isR ? " route" : ""), "marker-end": "url(#ah)"});
    path.dataset.f = f.from; path.dataset.t = f.to;
    gE.appendChild(path); eEl.push(path);
    const lx = .25 * x0 + .5 * cx + .25 * x1, ly = .25 * y0 + .5 * cy + .25 * y1;
    const lab = el("text", {x: lx, y: ly + 4, class: "lab" + (isR ? " route" : "")}, String(f.price));
    gL.appendChild(lab); eLab.push(lab); eGeo.push({d, lx, ly});
  });
  const mkMarker = (id, color) => {
    const m = el("marker", {id, markerWidth: 9, markerHeight: 9, refX: 8, refY: 3, orient: "auto"});
    m.appendChild(el("path", {d: "M0 0 L0 6 L9 3 z", fill: color})); defs.appendChild(m);
  };
  mkMarker("ah", "#8da197");
  ghost = []; ov = []; ovLen = [];
  S.route.forEach((l, i) => {
    const g = el("path", {d: eGeo[l.fi].d, class: "ghost"}); gO.appendChild(g); ghost.push(g);
    const o = el("path", {d: eGeo[l.fi].d, class: "ov " + (l.coupon ? "coupon" : "paid")}); gO.appendChild(o); ov.push(o);
    const len = o.getTotalLength(); ovLen.push(len); o.style.strokeDasharray = `${len} ${len}`; o.style.strokeDashoffset = len;
  });
  nodeEl = [null];
  for (let v = 1; v <= N; v++) {
    const g = el("g", {class: "node", transform: `translate(${pts[v].x.toFixed(1)} ${pts[v].y.toFixed(1)})`});
    g.appendChild(el("circle", {r: R})); g.appendChild(el("text", {}, String(v)));
    g.onmouseenter = () => hover(v, true); g.onmouseleave = () => hover(v, false);
    gN.appendChild(g); nodeEl.push(g);
  }
  plane = el("g", {}); plane.appendChild(el("path", {d: "M16 0 L-10 -10 L-5 0 L-10 10 Z", fill: "var(--navy)", stroke: "#fff", "stroke-width": 2, "stroke-linejoin": "round"}));
  svg.appendChild(plane);
  paint();
}

function hover(v, on) {
  eEl.forEach((e, i) => {
    const rel = +e.dataset.f === v || +e.dataset.t === v;
    e.classList.toggle("hl", on && rel);
    if (on && rel) eLab[i].style.display = "";
    else applyLabelMode(i);
  });
}
function applyLabelMode(i) {
  const isR = eEl[i].classList.contains("route"), all = $("labels").value === "all";
  eLab[i].style.display = (isR || (all && $("others").checked)) ? "" : "none";
  eEl[i].style.display = (isR || $("others").checked) ? "" : "none";
}

/* ---------- paint ---------- */
function paint() {
  const R = S.route, flying = S.prog > 0 && S.done < R.length;
  let run = 0, coup = 0;
  R.forEach((l, i) => {
    const f = F[l.fi], p = i < S.done ? 1 : (i === S.done ? S.prog : 0);
    ov[i].style.strokeDashoffset = ovLen[i] * (1 - p);
    if (p >= 1) { run += paid(f, l.coupon); if (l.coupon) coup++; }
    else if (p > 0) { run += paid(f, l.coupon) * p; if (l.coupon) coup++; }
    const applied = l.coupon && p > 0;
    eLab[l.fi].textContent = applied ? `${f.price} → ${paid(f, true)}` : String(f.price);
    eLab[l.fi].classList.toggle("coupon", applied);
  });
  F.forEach((f, i) => { if (!R.some(l => l.fi === i)) applyLabelMode(i); });
  R.forEach(l => applyLabelMode(l.fi));
  const reached = new Set(); for (let i = 0; i < S.done; i++) reached.add(F[R[i].fi].to);
  const planned = new Set(R.map(l => F[l.fi].to));
  for (let v = 1; v <= N; v++) {
    const c = nodeEl[v].classList;
    c.toggle("start", v === 1); c.toggle("end", v === N && S.route.length > 0 || v === N);
    c.toggle("stop", v !== 1 && v !== N && reached.has(v));
    c.toggle("planned", v !== 1 && v !== N && planned.has(v) && !reached.has(v));
  }
  /* plane */
  let x, y, ang = 0;
  if (R.length === 0) plane.style.display = "none";
  else {
    plane.style.display = "";
    if (flying) {
      const o = ov[S.done], L = ovLen[S.done], at = o.getPointAtLength(L * S.prog), a2 = o.getPointAtLength(Math.min(L, L * S.prog + 2)), a1 = o.getPointAtLength(Math.max(0, L * S.prog - 2));
      x = at.x; y = at.y; ang = Math.atan2(a2.y - a1.y, a2.x - a1.x) * 180 / Math.PI;
    } else {
      const v = S.done === 0 ? 1 : F[R[S.done - 1].fi].to; x = pts[v].x; y = pts[v].y - 33; ang = 0;
      if (S.done > 0) ang = 0;
    }
    plane.setAttribute("transform", `translate(${x.toFixed(1)} ${y.toFixed(1)}) rotate(${ang.toFixed(1)})`);
  }
  /* stats */
  const stops = R.length ? Math.max(0, Math.min(S.done, R.length - 1) - 0 + (S.done >= R.length ? 0 : 0) - (S.done > 0 ? 1 : 0) + (S.done > 0 ? 1 : 0)) : 0;
  const stopsUsed = Math.min(Math.max(0, S.done - (S.done >= R.length ? 1 : 0)), Math.max(0, R.length - 1));
  $("sRun").textContent = Math.round(run);
  $("sStops").textContent = `${stopsUsed} / ${S.K}`;
  $("sCoup").textContent = `${coup} / ${S.C}`;
  pips("pStops", S.K, stopsUsed, "pip"); pips("pCoup", S.C, coup, "tix");
  $("sFlights").textContent = R.length ? `Flight ${Math.min(S.done + (flying ? 1 : 0), R.length)} of ${R.length}` : "";
  $("bPlay").textContent = S.playing ? "❚❚ Pause" : (S.done >= R.length && R.length ? "↺ Replay" : "▶ Play");
  renderLegs();
}
function pips(id, total, used, cls) {
  const box = $(id), show = Math.min(total, 12);
  box.innerHTML = "";
  for (let i = 0; i < show; i++) { const s = document.createElement("span"); s.className = cls + (i < used ? " used" : ""); box.appendChild(s); }
  if (total > show) { const s = document.createElement("small"); s.textContent = `+${total - show}`; box.appendChild(s); }
  if (total === 0) { const s = document.createElement("small"); s.textContent = "none allowed"; box.appendChild(s); }
}
function renderLegs() {
  const R = S.route; let full = 0, pay = 0;
  $("legs").innerHTML = R.map((l, i) => {
    const f = F[l.fi]; full += f.price; pay += paid(f, l.coupon);
    return `<div class="leg ${i < S.done ? "done" : ""} ${i === S.done ? "cur" : ""} ${l.coupon ? "cp" : ""}">
      <span class="n">${i < S.done ? "✓" : i + 1}</span>
      <span><b>${f.from} → ${f.to}</b>${l.coupon ? '<span class="chip">COUPON</span>' : ""}<br><small>${l.coupon ? "half price, rounded down" : "full fare"}</small></span>
      <span>${l.coupon ? `<s>${f.price}</s> → <b>${paid(f, true)}</b>` : `<b>${f.price}</b>`}</span></div>`;
  }).join("") || '<div class="note">No route within the stop limit.</div>';
  $("totals").innerHTML = R.length ? `<div class="tot"><span>Full fares</span><span>${full}</span></div><div class="tot"><span>Coupon savings</span><span>− ${full - pay}</span></div><div class="tot"><b>You pay</b><b>${pay}</b></div>` : "";
}

/* ---------- solve + chrome ---------- */
function resolve(resetAnim = true) {
  S.sol = solveDP(F, N, S.K, S.C); S.route = S.sol.route;
  if (resetAnim) { S.done = 0; S.prog = 0; S.hold = 0; S.playing = false; }
  $("vK").textContent = S.K; $("vC").textContent = S.C;
  const best = S.sol.best;
  $("sTotal").textContent = best === null ? "−1" : best;
  const full = S.route.reduce((s, l) => s + F[l.fi].price, 0);
  $("sSave").textContent = best === null ? "No valid route within the stop limit" : (full > best ? `${full} without coupons · saves ${full - best}` : "coupons do not help here");
  const same = S.K === D.k && S.C === D.c, pyCost = D.py.cost;
  const ok = same && (pyCost === best);
  $("badges").innerHTML =
    (same ? `<span class="badge ${ok ? "ok" : "warn"}">${ok ? "✓ Python result matches browser solver" : "⚠ Python/browser mismatch"}</span>` : `<span class="badge warn">What-if mode (K=${S.K}, C=${S.C})</span>`) +
    `<span class="badge">Python: DP ${D.py.dp_ms} ms · Dijkstra ${D.py.dij_ms} ms</span>`;
  $("msg").textContent = best === null ? "No route exists within K+1 flights. Increase K to search deeper." : `Cheapest trip: ${[1, ...S.route.map(l => F[l.fi].to)].join(" → ")} for ${best}.`;
  buildMap(); drawWhatIf();
}

/* ---------- animation ---------- */
function toast(t) { const e = $("toast"); e.textContent = t; e.classList.add("show"); clearTimeout(toast.h); toast.h = setTimeout(() => e.classList.remove("show"), 2200 / S.speed + 600); }
function announce() {
  const l = S.route[S.done]; if (!l) return; const f = F[l.fi];
  if (l.coupon) toast(`🎟 Coupon applied on ${f.from} → ${f.to}:  ${f.price} → ${paid(f, true)}`);
  $("msg").textContent = l.coupon ? `Flight ${S.done + 1}: ${f.from} → ${f.to}. Coupon halves ${f.price} to ${paid(f, true)}.` : `Flight ${S.done + 1}: ${f.from} → ${f.to} at full fare ${f.price}.`;
}
function tick(ts) {
  if (!S.playing) return;
  const dt = Math.min(60, ts - S.last) * S.speed; S.last = ts;
  if (S.hold > 0) S.hold -= dt;
  else {
    S.prog += dt / LEG_MS;
    if (S.prog >= 1) {
      S.done++; S.prog = 0; S.hold = HOLD_MS;
      if (S.done >= S.route.length) { S.playing = false; $("msg").textContent = `Trip complete. Total paid: ${S.sol.best}.`; }
      else announce();
    }
  }
  paint(); if (S.playing) requestAnimationFrame(tick);
}
function play() {
  if (!S.route.length) return;
  if (S.playing) { S.playing = false; paint(); return; }
  if (S.done >= S.route.length) { S.done = 0; S.prog = 0; }
  S.playing = true; if (S.prog === 0 && S.hold <= 0) announce();
  S.last = performance.now(); requestAnimationFrame(tick); paint();
}
$("bPlay").onclick = play;
$("bNext").onclick = () => { S.playing = false; S.prog = 0; S.done = Math.min(S.route.length, S.done + 1); if (S.done < S.route.length) announce(); paint(); };
$("bPrev").onclick = () => { S.playing = false; S.prog = 0; S.done = Math.max(0, S.done - 1); announce(); paint(); };
$("bReset").onclick = () => { S.playing = false; S.prog = 0; S.done = 0; $("msg").textContent = "Back at city 1."; paint(); };
$("speed").onchange = e => S.speed = +e.target.value;
$("layout").onchange = e => { S.layout = e.target.value; buildMap(); };
$("labels").onchange = $("others").onchange = () => paint();
$("rK").oninput = e => { S.K = +e.target.value; resolve(); };
$("rC").oninput = e => { S.C = +e.target.value; resolve(); };
$("tabs").onclick = e => {
  const t = e.target.dataset.t; if (!t) return;
  for (const b of $("tabs").children) b.classList.toggle("on", b.dataset.t === t);
  ["journey", "whatif", "analysis", "cases"].forEach(id => $(id).classList.toggle("hidden", id !== t));
};

/* ---------- charts ---------- */
function lineChart(svg, xs, series, o = {}) {
  svg.innerHTML = "";
  const W = 520, H = 300, l = 58, r = 14, t = 14, b = 44, all = series.flatMap(s => s.vals).filter(v => v !== null && v !== undefined);
  if (!all.length) { svg.appendChild(el("text", {x: W / 2, y: H / 2, class: "tk", "text-anchor": "middle"}, "No feasible values")); return; }
  let lo = Math.min(...all), hi = Math.max(...all);
  const lg = o.log; if (lg) { lo = Math.max(lo, 1e-4); hi = Math.max(hi, lo * 10); }
  const f = v => lg ? Math.log10(Math.max(v, lo)) : v, a = f(lg ? lo : Math.min(0, lo)), z = f(hi) + (lg ? 0 : (hi - Math.min(0, lo)) * .08 || 1);
  const X = i => l + (xs.length === 1 ? (W - l - r) / 2 : i * (W - l - r) / (xs.length - 1)), Y = v => H - b - (f(v) - a) / (z - a || 1) * (H - b - t);
  for (let k = 0; k <= 4; k++) {
    const val = lg ? Math.pow(10, a + (z - a) * k / 4) : a + (z - a) * k / 4, y = H - b - k / 4 * (H - b - t);
    svg.appendChild(el("line", {x1: l, x2: W - r, y1: y, y2: y, class: "gl"}));
    svg.appendChild(el("text", {x: l - 8, y: y + 4, class: "tk", "text-anchor": "end"}, (o.fmt || (v => v >= 100 ? v.toFixed(0) : v.toFixed(2)))(val)));
  }
  svg.appendChild(el("line", {x1: l, x2: l, y1: t, y2: H - b, class: "ax"})); svg.appendChild(el("line", {x1: l, x2: W - r, y1: H - b, y2: H - b, class: "ax"}));
  xs.forEach((x, i) => svg.appendChild(el("text", {x: X(i), y: H - b + 17, class: "tk", "text-anchor": "middle"}, String(x))));
  svg.appendChild(el("text", {x: (l + W - r) / 2, y: H - 6, class: "tk", "text-anchor": "middle"}, o.xlabel || ""));
  const yl = el("text", {x: 14, y: (t + H - b) / 2, class: "tk", "text-anchor": "middle", transform: `rotate(-90 14 ${(t + H - b) / 2})`}, o.ylabel || ""); svg.appendChild(yl);
  series.forEach(s => {
    let d = "", pen = false;
    s.vals.forEach((v, i) => { if (v === null || v === undefined) { pen = false; return; } d += `${pen ? "L" : "M"}${X(i).toFixed(1)} ${Y(v).toFixed(1)} `; pen = true; });
    svg.appendChild(el("path", {d, fill: "none", stroke: s.color, "stroke-width": 2.6, "stroke-linejoin": "round"}));
    s.vals.forEach((v, i) => { if (v !== null && v !== undefined) { const c = el("circle", {cx: X(i), cy: Y(v), r: 4, fill: s.color}); c.appendChild(el("title", {}, `${s.name}: ${v}`)); svg.appendChild(c); } });
  });
}
function legend(id, series) { $(id).innerHTML = series.map(s => `<span><i style="background:${s.color}"></i>${s.name}</span>`).join(""); }

/* ---------- what-if tab ---------- */
function drawWhatIf() {
  const T = S.sol.table, best = S.sol.best;
  const rows = [], cols = [...Array(S.C + 1).keys()];
  for (let t = 1; t < T.length; t++) if (T[t].some(v => v !== Infinity)) rows.push(t);
  const vals = rows.flatMap(t => T[t]).filter(v => v !== Infinity), lo = Math.min(...vals), hi = Math.max(...vals);
  const heat = $("heat");
  if (!rows.length) { heat.innerHTML = "<tr><td>No route within the stop limit.</td></tr>"; }
  else {
    heat.innerHTML = `<tr><th>Flights ↓ / Coupons →</th>${cols.map(c => `<th>${c}</th>`).join("")}</tr>` + rows.map(t =>
      `<tr><th>${t} flight${t > 1 ? "s" : ""}</th>${cols.map(c => {
        const v = T[t][c]; if (v === Infinity) return '<td style="color:var(--mut);background:var(--soft)">—</td>';
        const k = hi === lo ? 0 : (v - lo) / (hi - lo), hue = 145 - 120 * k;
        return `<td class="${v === best ? "best" : ""}" style="background:hsl(${hue} 55% ${document.documentElement.matches(":root") && matchMedia("(prefers-color-scheme:dark)").matches ? 28 : 82}%)">${v}</td>`;
      }).join("")}</tr>`).join("");
  }
  const kMax = Math.min(N - 1, 10), ks = [...Array(kMax + 1).keys()], cs = [...Array(11).keys()];
  const kv = ks.map(k => solveDP(F, N, k, S.C).best), cv = cs.map(c => solveDP(F, N, S.K, c).best);
  lineChart($("chK"), ks, [{name: "min cost", color: "#1f9d63", vals: kv}], {xlabel: "max stops K", ylabel: "minimum cost", fmt: v => v.toFixed(0)});
  lineChart($("chC"), cs, [{name: "min cost", color: "#e0a21a", vals: cv}], {xlabel: "coupons C", ylabel: "minimum cost", fmt: v => v.toFixed(0)});
  const firstK = kv.findIndex(v => v !== null);
  $("kNote").textContent = firstK < 0 ? `With C=${S.C}, no route exists for any K up to ${kMax}.` : `With C=${S.C}: first feasible at K=${firstK}. Gaps = no route (−1).`;
  const drops = cv.map((v, i) => i && v !== null && cv[i - 1] !== null ? cv[i - 1] - v : 0), useful = drops.filter(x => x > 0).length;
  $("cNote").textContent = `With K=${S.K}: ${useful} coupon${useful === 1 ? "" : "s"} actually reduce${useful === 1 ? "s" : ""} the cost; extra coupons beyond that are wasted.`;
}

/* ---------- analysis tab ---------- */
function drawAnalysis() {
  const A = D.analysis, st = A.stress;
  $("aStats").innerHTML = [
    ["Randomised trials", st.trials.toLocaleString(), "tiny graphs, zero & odd prices"],
    ["DP = Dijkstra", `${st.dp_dij}/${st.trials}`, "identical minimum cost"],
    ["DP = Brute force", `${st.dp_brute}/${st.brute_checked}`, `exhaustive check on ${st.brute_checked} graphs`],
    ["Routes re-validated", `${st.routes_ok}/${st.trials}`, "walk, ≤K+1 flights, ≤C coupons, cost"]
  ].map(([a, b, c]) => `<div class="card"><label>${a}</label><strong>${b}</strong><small>${c}</small></div>`).join("");
  $("cmp").innerHTML = `<tr><th>Approach</th><th>Exact?</th><th>Time</th><th>Space</th><th>Measured on stress test</th><th>Verdict</th></tr>
   <tr><td><b>Layered DP</b> (primary)</td><td class="pass">yes</td><td><code>O((K+1)(C+1)(N+M))</code></td><td><code>O((K+1)N(C+1))</code></td><td>${st.dp_dij}/${st.trials} agree with Dijkstra</td><td>Predictable worst case, no heap, gives the full cost table for the What-if tab. Always scans every layer, so it can be slower than Dijkstra in practice</td></tr>
   <tr><td><b>Dijkstra</b> on (city, flights, coupons)</td><td class="pass">yes</td><td><code>O((K+1)(C+1)(N+M) log V)</code></td><td><code>O((K+1)(C+1)(N+M))</code></td><td>${st.dp_dij}/${st.trials} agree with DP</td><td>Often fastest in the benchmarks (stops once city N is popped); adds a log factor in the worst case</td></tr>
   <tr><td><b>Brute force</b> DFS</td><td class="pass">yes</td><td><code>O((2M)^(K+1))</code></td><td><code>O(K)</code></td><td>${st.dp_brute}/${st.brute_checked} agree · skipped ${st.trials - st.brute_checked} (too big)</td><td>Ground truth for small inputs; unusable as K grows</td></tr>
   <tr><td><b>Greedy</b> (cheapest path + coupons on biggest fares)</td><td class="fail">no</td><td><code>O(M log N)</code></td><td><code>O(N+M)</code></td><td class="fail">wrong on ${st.greedy_wrong}/${st.trials} (${(100 * st.greedy_wrong / st.trials).toFixed(1)}%)</td><td>Fast but ignores the stop limit and coupon interaction</td></tr>`;
  const bn = A.bench_n, bk = A.bench_k;
  const sN = [{name: "Layered DP", color: "#1f9d63", vals: bn.map(r => r.dp_ms)}, {name: "Dijkstra", color: "#e0a21a", vals: bn.map(r => r.dijkstra_ms)}];
  lineChart($("chN"), bn.map(r => r.cities), sN, {xlabel: "number of cities N (K=6, C=2)", ylabel: "ms", log: true}); legend("lgN", sN);
  $("bnNote").textContent = `Random graphs, ${bn[0].flights}–${bn[bn.length - 1].flights} flights. Best of 3 runs per point; log scale.`;
  const sK = [{name: "Layered DP", color: "#1f9d63", vals: bk.map(r => r.dp_ms)}, {name: "Dijkstra", color: "#e0a21a", vals: bk.map(r => r.dijkstra_ms)}, {name: "Brute force", color: "#d9534f", vals: bk.map(r => r.brute_ms)}];
  lineChart($("chBK"), bk.map(r => r.max_stops), sK, {xlabel: "max stops K (N=12, C=2)", ylabel: "ms", log: true}); legend("lgBK", sK);
  $("bkNote").textContent = `Brute force blows up exponentially; points are missing where it exceeded ${A.brute_limit.toLocaleString()} explored states.`;
}

/* ---------- corner cases ---------- */
function drawCases() {
  const f = v => v === null ? "−1" : v === undefined ? "skipped" : v;
  $("caseTable").innerHTML = `<tr><th>#</th><th>Case</th><th>Input</th><th class="r">Expected</th><th class="r">DP</th><th class="r">Dijkstra</th><th class="r">Brute</th><th>Result</th></tr>` +
    D.analysis.cases.map((c, i) => `<tr><td>${i + 1}</td><td><b>${c.name}</b><br><span class="note">${c.why}</span></td><td class="note">${c.input}</td><td class="r">${f(c.expected)}</td><td class="r">${f(c.dp)}</td><td class="r">${f(c.dijkstra)}</td><td class="r">${f(c.brute)}</td><td class="${c.ok ? "pass" : "fail"}">${c.ok ? "✓ pass" : "✗ FAIL"}</td></tr>`).join("");
}

resolve(); drawAnalysis(); drawCases();
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Extra algorithms used for verification and comparative analysis
# ---------------------------------------------------------------------------

class _BudgetExceeded(Exception):
    pass


def brute_force(city_count, max_stops, coupon_count, flights, node_limit=150_000):
    """
    Exhaustive DFS over every walk of at most K + 1 flights and every
    coupon choice. Ground truth for small inputs.

    Returns (cost or None, skipped). skipped is True when the search would
    have explored more than node_limit states.
    Time: O((2M)^(K+1))
    """
    outgoing = [[] for _ in range(city_count + 1)]
    for origin, destination, price in flights:
        outgoing[origin].append((destination, price))

    best = [float("inf")]
    explored = [0]

    def explore(city, flights_left, coupons_left, cost):
        explored[0] += 1
        if explored[0] > node_limit:
            raise _BudgetExceeded
        if city == city_count:
            best[0] = min(best[0], cost)
            return
        if flights_left == 0:
            return
        for destination, price in outgoing[city]:
            explore(destination, flights_left - 1, coupons_left, cost + price)
            if coupons_left:
                explore(destination, flights_left - 1, coupons_left - 1,
                        cost + price // 2)

    try:
        explore(1, max_stops + 1, coupon_count, 0)
    except _BudgetExceeded:
        return None, True, explored[0]

    return (None if best[0] == float("inf") else int(best[0])), False, explored[0]


def greedy_heuristic(city_count, max_stops, coupon_count, flights):
    """
    Tempting but WRONG baseline: take the cheapest-fare path (ignoring the
    stop limit), then spend coupons on its largest fares.
    """
    adjacency = [[] for _ in range(city_count + 1)]
    for origin, destination, price in flights:
        adjacency[origin].append((destination, price))

    dist = {1: 0}
    parent = {}
    heap = [(0, 1)]
    while heap:
        cost, city = heapq.heappop(heap)
        if cost > dist.get(city, float("inf")):
            continue
        for destination, price in adjacency[city]:
            if cost + price < dist.get(destination, float("inf")):
                dist[destination] = cost + price
                parent[destination] = (city, price)
                heapq.heappush(heap, (cost + price, destination))

    if city_count not in dist:
        return None

    prices = []
    city = city_count
    while city != 1:
        city, price = parent[city]
        prices.append(price)

    if len(prices) > max_stops + 1:
        return None  # the greedy path breaks the stop limit

    savings = sorted((p - p // 2 for p in prices), reverse=True)
    return sum(prices) - sum(savings[:coupon_count])


def verify_route(city_count, max_stops, coupon_count, flights, cost, route):
    """Independently re-check a reported route and its cost."""
    if cost is None:
        return route == []

    if not route or len(route) > max_stops + 1:
        return False

    city = 1
    total = 0
    coupons = 0
    for leg in route:
        origin, destination, price = flights[leg["flight_index"]]
        if origin != city:
            return False
        total += price // 2 if leg["coupon_used"] else price
        coupons += 1 if leg["coupon_used"] else 0
        city = destination

    return city == city_count and coupons <= coupon_count and total == cost


# ---------------------------------------------------------------------------
# Corner-case suite and randomised stress test
# ---------------------------------------------------------------------------

# (name, why it matters, N, K, C, flights, expected minimum cost or None)
CORNER_CASES = [
    ("Direct flight, no coupon", "Zero stops, zero coupons baseline.",
     2, 0, 0, [(1, 2, 12)], 12),
    ("Odd fare with coupon", "9 // 2 = 4: rounding is down, not nearest.",
     2, 0, 1, [(1, 2, 9)], 4),
    ("Stop limit blocks route", "K = 0 allows exactly one flight, so 1->2->3 is illegal.",
     3, 0, 0, [(1, 2, 3), (2, 3, 4)], None),
    ("Direct beats connection", "A cheaper-looking detour is not always cheaper.",
     3, 1, 0, [(1, 3, 8), (1, 2, 2), (2, 3, 10)], 8),
    ("No flights at all", "M = 0 must give -1, not crash.",
     2, 3, 2, [], None),
    ("Only a backward flight", "Flights are one-way: 2->1 does not help 1->2.",
     2, 0, 1, [(2, 1, 5)], None),
    ("Destination unreachable", "Flights exist but never reach city N.",
     3, 2, 1, [(2, 1, 5), (3, 2, 5)], None),
    ("One coupon per flight", "Three coupons cannot stack on one 100 fare.",
     2, 0, 3, [(1, 2, 100)], 50),
    ("More coupons than flights", "Extra coupons are simply unused.",
     3, 1, 5, [(1, 2, 10), (2, 3, 10)], 10),
    ("Coupon goes on the biggest fare", "100 -> 50 saves more than 10 -> 5, so 50 + 10.",
     3, 1, 1, [(1, 2, 100), (2, 3, 10)], 60),
    ("Two odd fares, two coupons", "3 -> 1 twice; floors add up.",
     3, 1, 2, [(1, 2, 3), (2, 3, 3)], 2),
    ("Coupon makes a flight free", "1 // 2 = 0.",
     2, 0, 1, [(1, 2, 1)], 0),
    ("Zero-price flight", "Free flights are legal and must be counted as a flight.",
     3, 1, 0, [(1, 2, 0), (2, 3, 0)], 0),
    ("Parallel flights", "Two flights on the same pair: pick the cheaper.",
     2, 0, 0, [(1, 2, 50), (1, 2, 30)], 30),
    ("Cycle never helps", "Looping 1->2->1 only adds cost.",
     3, 3, 0, [(1, 2, 5), (2, 1, 1), (2, 3, 5)], 10),
    ("Stop limit forces expensive direct", "K = 1 forbids the 3-flight chain.",
     4, 1, 0, [(1, 2, 1), (2, 3, 1), (3, 4, 1), (1, 4, 100)], 100),
    ("Relaxed limit unlocks cheap chain", "Same graph with K = 2.",
     4, 2, 0, [(1, 2, 1), (2, 3, 1), (3, 4, 1), (1, 4, 100)], 3),
    ("Greedy trap", "Cheapest-fare path 30+30 -> 45 with a coupon, but direct 80 -> 40.",
     3, 1, 1, [(1, 2, 30), (2, 3, 30), (1, 3, 80)], 40),
    ("Coupon changes the winning route", "Direct 100 -> 50, but detour 20 + 40 -> 20 + 20 = 40.",
     3, 1, 1, [(1, 3, 100), (1, 2, 20), (2, 3, 40)], 40),
    ("K much larger than needed", "Unused stops are fine.",
     3, 10, 2, [(1, 2, 4), (2, 3, 4)], 4),
    ("Large prices", "No overflow or float rounding in Python ints.",
     2, 0, 1, [(1, 2, 10**15 + 1)], (10**15 + 1) // 2),
]


def _describe(city_count, stops, coupons, flights):
    shown = ", ".join(f"{a}→{b}:{p}" for a, b, p in flights[:5])
    if len(flights) > 5:
        shown += ", …"
    return f"N={city_count}, K={stops}, C={coupons}" + (f" · {shown}" if shown else " · no flights")


def run_corner_cases():
    rows = []
    for name, why, n, k, c, flights, expected in CORNER_CASES:
        dp_cost, dp_route = dynamic_programming(n, k, c, flights)
        dij_cost, dij_route = dijkstra(n, k, c, flights)
        brute_cost, skipped, _ = brute_force(n, k, c, flights)

        ok = (
            dp_cost == expected
            and dij_cost == expected
            and (skipped or brute_cost == expected)
            and verify_route(n, k, c, flights, dp_cost, dp_route)
            and verify_route(n, k, c, flights, dij_cost, dij_route)
        )
        rows.append({
            "name": name, "why": why, "input": _describe(n, k, c, flights),
            "expected": expected, "dp": dp_cost, "dijkstra": dij_cost,
            "brute": None if skipped else brute_cost, "ok": ok,
        })

    failed = [row["name"] for row in rows if not row["ok"]]
    if failed:
        raise RuntimeError("Corner-case check failed: " + ", ".join(failed))

    print(f"Corner-case suite passed ({len(rows)} cases).")
    return rows


def stress_test(trials=2000, seed=2026):
    """Compare DP, Dijkstra and brute force on many tiny random graphs."""
    rng = random.Random(seed)
    stats = {
        "trials": trials, "dp_dij": 0, "dp_brute": 0, "brute_checked": 0,
        "routes_ok": 0, "greedy_wrong": 0,
    }

    for _ in range(trials):
        n = rng.randint(2, 7)
        m = rng.randint(0, 2 * n)
        flights = []
        for _ in range(m):
            origin = rng.randint(1, n)
            destination = rng.randint(1, n)
            if origin != destination:
                flights.append((origin, destination, rng.randint(0, 40)))
        k = rng.randint(0, 4)
        c = rng.randint(0, 4)

        dp_cost, dp_route = dynamic_programming(n, k, c, flights)
        dij_cost, dij_route = dijkstra(n, k, c, flights)
        brute_cost, skipped, _ = brute_force(n, k, c, flights, node_limit=60_000)

        if dp_cost != dij_cost:
            raise RuntimeError(f"DP and Dijkstra disagree: {n, k, c, flights}")
        stats["dp_dij"] += 1

        if not skipped:
            stats["brute_checked"] += 1
            if brute_cost != dp_cost:
                raise RuntimeError(f"DP and brute force disagree: {n, k, c, flights}")
            stats["dp_brute"] += 1

        if (verify_route(n, k, c, flights, dp_cost, dp_route)
                and verify_route(n, k, c, flights, dij_cost, dij_route)):
            stats["routes_ok"] += 1
        else:
            raise RuntimeError(f"Invalid route returned: {n, k, c, flights}")

        if greedy_heuristic(n, k, c, flights) != dp_cost:
            stats["greedy_wrong"] += 1

    print(
        f"Stress test: {trials} random graphs, DP = Dijkstra on {stats['dp_dij']}, "
        f"DP = brute force on {stats['dp_brute']}/{stats['brute_checked']}; "
        f"greedy baseline wrong on {stats['greedy_wrong']}."
    )
    return stats


# ---------------------------------------------------------------------------
# Benchmarks
# ---------------------------------------------------------------------------

def _best_ms(function, *args, repeat=3):
    best = float("inf")
    for _ in range(repeat):
        start = time.perf_counter()
        function(*args)
        best = min(best, (time.perf_counter() - start) * 1000)
    return best


def run_benchmarks(quick=False, seed=7, brute_limit=150_000):
    """Runtime vs graph size, and runtime vs K (where brute force explodes)."""
    saved_state = random.getstate()
    random.seed(seed)
    try:
        sizes = [10, 20, 40, 80] if quick else [10, 20, 40, 80, 160, 320]
        bench_n = []
        for city_count in sizes:
            flights = generate_graph(city_count, 6, 0.08)
            dp_cost, _ = dynamic_programming(city_count, 6, 2, flights)
            dij_cost, _ = dijkstra(city_count, 6, 2, flights)
            if dp_cost != dij_cost:
                raise RuntimeError("Algorithms disagreed during benchmarking.")
            bench_n.append({
                "cities": city_count, "flights": len(flights),
                "dp_ms": round(_best_ms(dynamic_programming, city_count, 6, 2, flights), 4),
                "dijkstra_ms": round(_best_ms(dijkstra, city_count, 6, 2, flights), 4),
                "minimum_cost": dp_cost,
            })

        city_count = 12
        flights = generate_graph(city_count, 7, 0.3)
        bench_k = []
        for stops in range(0, 8):
            dp_cost, _ = dynamic_programming(city_count, stops, 2, flights)
            brute_cost, skipped, explored = brute_force(
                city_count, stops, 2, flights, node_limit=brute_limit
            )
            if not skipped and brute_cost != dp_cost:
                raise RuntimeError("Brute force disagreed during benchmarking.")
            brute_ms = None
            if not skipped:
                brute_ms = round(_best_ms(
                    brute_force, city_count, stops, 2, flights, brute_limit, repeat=1
                ), 4)
            bench_k.append({
                "max_stops": stops,
                "dp_ms": round(_best_ms(dynamic_programming, city_count, stops, 2, flights), 4),
                "dijkstra_ms": round(_best_ms(dijkstra, city_count, stops, 2, flights), 4),
                "brute_ms": brute_ms,
                "brute_states": None if skipped else explored,
                "minimum_cost": dp_cost,
            })
    finally:
        random.setstate(saved_state)

    for filename, rows in (("benchmark.csv", bench_n), ("benchmark_k.csv", bench_k)):
        with open(filename, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    print("Benchmarks saved to benchmark.csv and benchmark_k.csv.")
    return bench_n, bench_k


# ---------------------------------------------------------------------------
# Graph generation, CSV output, dashboard
# ---------------------------------------------------------------------------

def generate_graph(city_count, max_stops, density):
    """Generate random flights and guarantee a route within the stop limit."""
    max_flights = max_stops + 1
    middle_city_count = min(city_count - 2, max_flights - 1)

    middle_cities = sorted(
        random.sample(range(2, city_count), middle_city_count)
    )
    guaranteed_route = [1] + middle_cities + [city_count]

    flights = []
    used_pairs = set()

    for index in range(len(guaranteed_route) - 1):
        origin = guaranteed_route[index]
        destination = guaranteed_route[index + 1]
        flights.append((origin, destination, random.randint(80, 500)))
        used_pairs.add((origin, destination))

    for origin in range(1, city_count + 1):
        for destination in range(1, city_count + 1):
            if origin == destination or (origin, destination) in used_pairs:
                continue
            if random.random() < density:
                flights.append((origin, destination, random.randint(50, 700)))
                used_pairs.add((origin, destination))

    return flights


def save_flights_csv(filename, flights):
    with open(filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["from", "to", "price"])
        writer.writerows(flights)


def save_result_csv(filename, flights, route):
    """The graph with the chosen path marked 'x' and coupon flights flagged."""
    chosen = {
        leg["flight_index"]: (step, leg)
        for step, leg in enumerate(route, start=1)
    }

    with open(filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([
            "from", "to", "price", "chosen_path", "leg_no",
            "coupon_used", "price_paid",
        ])

        for index, (origin, destination, price) in enumerate(flights):
            if index not in chosen:
                writer.writerow([origin, destination, price, "", "", "", ""])
                continue

            step, leg = chosen[index]
            used = leg["coupon_used"]
            writer.writerow([
                origin, destination, price, "x", step,
                "x" if used else "", price // 2 if used else price,
            ])


def save_dashboard(filename, city_count, max_stops, coupon_count, flights,
                   total_cost, route, timings, analysis):
    data = {
        "n": city_count, "k": max_stops, "c": coupon_count,
        "flights": [{"from": a, "to": b, "price": p} for a, b, p in flights],
        "py": {
            "cost": total_cost,
            "route": [{"fi": leg["flight_index"], "coupon": leg["coupon_used"]}
                      for leg in route],
            "dp_ms": round(timings["dp"], 3),
            "dij_ms": round(timings["dijkstra"], 3),
        },
        "analysis": analysis,
    }
    payload = json.dumps(data).replace("</", "<\\/")
    Path(filename).write_text(
        DASHBOARD_TEMPLATE.replace("__DATA__", payload), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Input helpers and main program
# ---------------------------------------------------------------------------

def ask_integer(prompt, minimum=0):
    while True:
        try:
            value = int(input(prompt))
            if value < minimum:
                print(f"Enter a whole number of at least {minimum}.")
                continue
            return value
        except ValueError:
            print("Please enter a whole number.")


def read_pair(prompt):
    values = input(prompt).split()
    if len(values) != 2:
        raise ValueError("Expected exactly two whole numbers on that line.")
    return int(values[0]), int(values[1])


def main():
    quick = "--quick" in sys.argv
    open_browser = "--no-browser" not in sys.argv

    print("\nBUDGET TRAVELLER WITH COUPONS")
    corner_rows = run_corner_cases()

    print("\nCity 1 is the start; city N is the destination.\n")
    print("1. Type the graph:   N M / K C / M lines of 'u v p'")
    print("2. Load a CSV file:  K C, then from,to,price rows")
    print("3. Generate a random graph for your K and C\n")

    mode = input("Choose option 1, 2, or 3: ").strip()

    try:
        if mode == "1":
            city_count, flight_count = read_pair("N M: ")
            max_stops, coupon_count = read_pair("K C: ")
            flights = []
            for index in range(flight_count):
                values = input(f"Flight {index + 1} (u v p): ").split()
                if len(values) != 3:
                    raise ValueError("Each flight needs exactly: u v p")
                flights.append(tuple(map(int, values)))

        elif mode == "2":
            max_stops, coupon_count = read_pair("K C: ")
            filename = input("CSV file (Enter for flights.csv): ").strip() or "flights.csv"
            flights = read_csv(filename)
            if not flights:
                raise ValueError("The CSV file contains no flights.")
            largest = max(max(a, b) for a, b, _ in flights)
            text = input(f"Destination city N (Enter for {largest}): ").strip()
            city_count = int(text) if text else largest
            city_count = max(city_count, 2)

        elif mode == "3":
            city_count = ask_integer("Number of cities N (2-40): ", 2)
            max_stops, coupon_count = read_pair("K C: ")
            density_text = input("Extra-flight density 0-1 (Enter for 0.15): ").strip()
            density = float(density_text) if density_text else 0.15
            seed_text = input("Random seed (Enter for a random graph): ").strip()
            if not 0 <= density <= 1:
                raise ValueError("Density must be between 0 and 1.")
            if max_stops < 0 or max_stops > city_count - 1:
                raise ValueError("K must be between 0 and N - 1.")
            if seed_text:
                random.seed(int(seed_text))
            flights = generate_graph(city_count, max_stops, density)
            save_flights_csv("flights.csv", flights)
            print("Generated graph saved in flights.csv.")

        else:
            print("Please choose option 1, 2, or 3.")
            return

        if city_count < 2:
            raise ValueError("N must be at least 2.")
        if max_stops < 0 or coupon_count < 0:
            raise ValueError("K and C cannot be negative.")
        validate_flights(city_count, flights)

    except (ValueError, OSError) as error:
        print(f"\nInput error: {error}")
        return

    timings = {}
    start = time.perf_counter()
    total_cost, route = dynamic_programming(city_count, max_stops, coupon_count, flights)
    timings["dp"] = (time.perf_counter() - start) * 1000

    start = time.perf_counter()
    check_cost, check_route = dijkstra(city_count, max_stops, coupon_count, flights)
    timings["dijkstra"] = (time.perf_counter() - start) * 1000

    start = time.perf_counter()
    brute_cost, skipped, _ = brute_force(city_count, max_stops, coupon_count, flights)
    timings["brute"] = None if skipped else (time.perf_counter() - start) * 1000

    if total_cost != check_cost or (not skipped and brute_cost != total_cost):
        print("Error: the algorithms returned different costs.")
        return
    if not verify_route(city_count, max_stops, coupon_count, flights, total_cost, route):
        print("Error: the reconstructed route failed validation.")
        return

    print(f"\nOutput 1 - minimum cost: {-1 if total_cost is None else total_cost}")

    if total_cost is not None:
        cities = [1] + [flights[leg["flight_index"]][1] for leg in route]
        print("Route:", " -> ".join(map(str, cities)))
        print(f"Flights: {len(route)} | Stops: {max(0, len(route) - 1)} | "
              f"Coupons used: {sum(leg['coupon_used'] for leg in route)}")
        for leg in route:
            if leg["coupon_used"]:
                origin, destination, price = flights[leg["flight_index"]]
                print(f"  Coupon on {origin} -> {destination}: {price} -> {price // 2}")

    print("\nVerified: DP, Dijkstra" + ("" if skipped else ", brute force")
          + " agree; route re-validated.")
    print(f"DP {timings['dp']:.4f} ms | Dijkstra {timings['dijkstra']:.4f} ms | "
          + ("brute force skipped (input too large)" if skipped
             else f"brute force {timings['brute']:.4f} ms"))

    save_result_csv("result.csv", flights, route)
    print("\nOutput 2 - result.csv written (path = 'x', coupon flights flagged).")

    print("Running stress test and benchmarks for the analysis tab...")
    stress = stress_test(300 if quick else 2000)
    bench_n, bench_k = run_benchmarks(quick=quick)
    analysis = {
        "cases": corner_rows, "stress": stress,
        "bench_n": bench_n, "bench_k": bench_k, "brute_limit": 150_000,
    }

    save_dashboard("route.html", city_count, max_stops, coupon_count, flights,
                   total_cost, route, timings, analysis)
    print("Created route.html (journey, what-if, analysis, corner cases).")

    if open_browser:
        try:
            webbrowser.open(Path("route.html").resolve().as_uri())
        except OSError:
            print("Open route.html in a browser to see the dashboard.")


if __name__ == "__main__":
    main()
