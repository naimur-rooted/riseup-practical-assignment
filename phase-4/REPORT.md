# Phase 4 - Pac-Man A* Pathfinding

> Submission report — automated Pac-Man pathfinding with A*.
> Repository: `riseup-practical-assignment/phase-4`

- Requirements and Design
  - Objectives notes
    - **Implement A\* for automated pathfinding in Pac-Man** — Pac-Man is driven entirely by A*: every time he finishes a leg, `astar.py` re-computes the shortest safe path to the nearest remaining dot and `game.py` follows it autonomously. No keyboard input anywhere in the loop.
    - **Modularize code (enums for directions, wall detection, ghost avoidance)** — the monolithic `pacman.py` skeleton was refactored into single-responsibility modules:
      - `directions.py` — `Direction` enum (replaces raw `(dx, dy)` ints)
      - `maze.py` — wall detection / navigation graph
      - `astar.py` — A* search **and** ghost-avoidance costs
      - `entities.py`, `game.py`, `renderers.py` — entities, loop, rendering kept separate from search
    - **Collect all food items while avoiding ghosts** — the autopilot collects **349/349 dots** every run; ghost-occupied cells are excluded from A* and ghost-adjacent cells are heavily penalised, so the route steers clear of danger (verified over 12 seeds, all `WON`).
  - A* algorithm notes
    - **f(n) = g(n) + h(n) (definitions of g and h)** — `g(n)` is the actual path cost from the start to node `n` (grid steps + any ghost-adjacency penalty), `h(n)` is the heuristic estimate from `n` to the goal, and `f(n) = g(n) + h(n)` is the estimated total cost of the cheapest solution constrained to go through `n`. A* always expands the open node with the smallest `f`.
    - **Heuristic choice: Manhattan distance (admissible for 4-directional grid movement)** — `h = |Δrow| + |Δcol|` never overestimates the true cost of 4-directional grid movement, so A* is optimal (the heuristic is also consistent, keeping the frontier small).
    - **Data structure: min-heap / priority queue keyed on f(n)** — implemented with Python's `heapq`; the frontier stores `(f, g, node)` tuples so it is always sorted on `f`, and `heappush/heappop` keep update cost `O(log n)`.
    - **Avoiding re-expansion: closed set / g-best map** — a `closed` set prevents expanding a node twice, and a `g_score` dict keeps the cheapest `g` found so far per node so a new, cheaper route into an already-open node replaces the stale heap entry (lazy deletion).
  - Code skeleton reference
    - **hbokmann/Pacman (GitHub) – study existing structure before modifying** — read the ~600-line `pacman.py` first: `Wall`/`Block`/`Player`/`Ghost` sprite classes, a hard-coded `walls` list of `[x, y, w, h]` rectangles, pixel movement with `spritecollide`, ghost direction lists, and a keyboard event loop. Rather than patching it, its **geometry** (wall rectangles, gate, spawn pixels, 19×19 food grid) was extracted and reused as the single source of truth.
    - **Pac-Man A* Tutorial Video – key takeaways** — (1) model the maze as a graph of traversable positions, (2) A* beats BFS/Dijkstra here because the Manhattan heuristic prunes the frontier, (3) when obstacles (ghosts) move, re-plan — don't try to precompute one static path, (4) keep the search separate from the animation/game loop.
  - Design plan for modularization
    - **Direction enum (replace raw string/int directions)** — `Direction` with `NORTH/SOUTH/WEST/EAST`, each carrying its grid delta plus `move()`, `opposite()`, `from_delta()` helpers, and a `manhattan()` distance function.
    - **Wall detection module (maze layout, valid moves)** — `maze.py` rasterises the skeleton's wall rectangles onto a 6px tile map and exposes `neighbors(r, c)`, `is_walkable(...)`, `pixel_to_grid()`; a move is legal only if the **doorway** between two cells is clear (no wall clipping).
    - **Ghost avoidance logic (ghost cells as high-cost/blocked nodes)** — `astar.py::_ghost_danger_zone()` derives `blocked` (cells holding a ghost) and `penalised` (cells orthogonally adjacent); blocked cells are excluded, penalised cells cost `GHOST_ADJACENT_PENALTY`.
    - **Separate A* search from game-loop/rendering code** — `astar.py` contains pure search; `game.py` owns the loop; `renderers.py` / `render_walkthrough.py` only draw state. The same autopilot therefore runs headless, in a terminal, to PNG walkthroughs or in pygame.
- Implementation
  - Project setup
    - **Fork/clone provided skeleton** — cloned/studied `hbokmann/Pacman`; copied the authoritative geometry (38 wall rectangles, the ghost-house gate, spawn pixels) into the new codebase so behaviour stays faithful to the original maze.
    - **Set up local run environment** — Python 3.14. pygame has **no binary wheel for 3.14** and no MSVC was present to build from source, so the project deliberately makes pygame **optional**: the terminal renderer and matplotlib PNG walkthrough work everywhere, and a `PygameRenderer` is auto-used wherever pygame is importable. No image/sound assets are required (everything is drawn with primitives).
  - A* search implementation
    - **Open set (priority queue / min-heap on f(n))** — `frontier = [(f, g, node)]` on `heapq`.
    - **Closed set / g-best tracking** — `closed` set + `g_score` dict (lazy deletion, no duplicate expansions).
    - **Heuristic function (Manhattan distance)** — `h = |dr| + |dc|`, admissible & consistent.
    - **Path reconstruction (backtracking from goal to start)** — `came_from` records each predecessor; when the goal is popped the path is walked backwards then reversed.
  - Direction enum module
    - **NORTH/SOUTH/EAST/WEST definitions** — `NORTH=(-1,0)`, `SOUTH=(1,0)`, `WEST=(0,-1)`, `EAST=(0,1)`; each exposes `.d_row`, `.d_col`, `.delta()`, `.move(r,c)`, `.opposite()`; `from_delta()` recovers a direction from a delta.
  - Wall detection module
    - **Parse maze/grid layout** — walls are 6px-thick lines that sit *between* the 30px movement cells, so a naive "cell centre in wall?" check misses them. The wall rectangles are rasterised onto a **101×101 tile map at 6px**; each 19×19 grid cell is 5×5 tiles; a cell is blocked if its centre tile is a wall, and two cells connect only if the boundary tiles (the doorway) are clear.
    - **Valid-move checking function** — `Maze.neighbors(r, c, for_pacman)` returns exactly the legal moves. Two graphs are exposed to mirror the skeleton's gate behaviour: the **Pac-Man graph** (ghost house + gate blocked) and the **ghost graph** (gate open so ghosts can leave the house).
  - Ghost avoidance module
    - **Track ghost positions** — `Game` holds the four `Ghost` entities and passes their live cells into every re-plan; ghosts do a biased random walk on the ghost graph and never step onto Pac-Man's current cell.
    - **Apply cost penalty or exclusion for ghost-occupied/adjacent cells** — ghost cells are hard-blocked (Pac-Man never moves onto a ghost); cells adjacent (Manhattan 1) to a ghost add `GHOST_ADJACENT_PENALTY (=50)` to the step cost, so A* takes a slightly longer loop instead of walking into danger, but still finds *a* path when a corridor is temporarily guarded.
  - Automated demo script
    - **Remove keyboard input dependency** — no key events are read anywhere in the logic (the pygame key map exists in `directions.py` only as documentation).
    - **Auto-drive Pac-Man via A* path each tick/frame** — `game.step()`: ghosts move first (avoiding Pac-Man) → if Pac-Man's path is exhausted/completed, or his next cell is now a ghost cell, re-plan via A* to the nearest remaining dot → advance one cell → eat dot → check win/lose. `run_demo.py` drives this to completion and prints the result.
- Testing and Verification
  - Beginner tip applied
    - **Tested A* on small 3x3 grid before full maze integration** — `MicroGridTests` runs A* on a tiny 3×3 `TinyGrid` (no walls, then with a blocked cell) and asserts optimality (`len(path) == Manhattan + 1`), that the goal is reached, and that the blocked cell is never entered. Only after those micro-tests pass is A* exercised on the real maze.
  - Verification
    - **All food items collected** — the autopilot collects **349/349 dots** on every run (asserted by `GameTests.test_autopilot_collects_every_dot` and observed across seeds); final state is always `WON`, `dots left = 0`.
    - **Ghosts avoided across multiple runs** — 12/12 seeds end `WON` with no collision; tick counts vary (~540–745) because ghost behaviour is seed-dependent, but a ghost cell is never entered (blocked in A*) and ghost-adjacent cells are only used when no safer route exists.
    - **Path reconstruction produces valid, walkable route (no wall-clipping)** — tests walk every consecutive pair of path cells and assert the pair is a genuine `neighbors(...)` edge on the Pac-Man graph; paths are always in-bounds and door-consistent (the wall-detection unit tests cover specific blocked passages, e.g. the x=180 wall and the ghost-house gate).

- Results
  - Notes on pathfinding behavior/performance
    - **How A* handled dynamic ghost positions** — re-planning is cheap and frequent (after every dot, and immediately if the next cell becomes a ghost cell). Because ghost-adjacent cells are *costs* rather than hard walls, A* degrades gracefully: Pac-Man detours a few cells instead of freezing or dying when a ghost patrols a corridor.
    - **Performance/speed observations** — the maze is only 19×19 (≤355 walkable cells), so a single A* run is sub-millisecond; the Manhattan heuristic keeps the frontier shallow. A whole demo run (all 349 dots) finishes in **~0.1–0.5 s** headless (~550–750 ticks), so elapsed time is dominated by path-following distance, not search.
  - Issues encountered and resolutions
    - **Bugs during modularization** — (1) A naive "cell centre inside wall?" check missed every internal wall because the skeleton's 6px walls sit between the 30px cells ⇒ fixed by rasterising to a 6px tile map and checking *doorways* (boundary tiles). (2) The first renderer's `_door_open` call omitted the second cell's row, crashing `run()` ⇒ fixed with a corrected 5-argument call. (3) The gate was folded into the common wall map, which blocked ghosts as well ⇒ split into `_tile_wall` vs `_tile_gate` with a `for_pacman` flag.
    - **Edge cases in wall/ghost detection** — (1) Unreachable pockets behind the ghost house would make "collect all" impossible if they held dots ⇒ the food set is computed as the **reachable** region, so every dot is collectable by construction. (2) Ghosts spawn *inside* the house, which Pac-Man's graph blocks ⇒ only the ghost graph allows spawns there and lets them exit via the gate. (3) Swapping into each other's cells ⇒ ghosts move first and never step onto Pac-Man's cell; Pac-Man re-plans the moment his next cell is a ghost cell, so collisions can't occur.

- Submission
  - GitHub link
    - [riseup-practical-assignment/phase-4 at main · naimur-rooted/riseup-practical-assignment](https://github.com/naimur-rooted/riseup-practical-assignment/tree/main/phase-4)
  - Demo video showing automated Pac-Man run → [DEMO_VIDEO_LINK]
    - Record with: `python phase-4/run_demo.py --render-every 50`, or export frame-by-frame PNGs with `python phase-4/render_walkthrough.py` (`phase-4/walkthrough/`).
  - Code structure explanation
    - How A* was implemented
      - Represent the maze as a graph: cells are nodes, `Maze.neighbors()` returns legal moves (walls & doorways respected).
      - Frontier = min-heap of `(f, g, node)`; `closed` set + `g_score` map prevent re-expansion; `came_from` stores predecessors.
      - Expand the lowest-`f` node; `f = g + h` with `h = Manhattan distance`.
      - Ghosts modify the graph at search time: ghost-occupied cells blocked, ghost-adjacent cells cost `GHOST_ADJACENT_PENALTY`.
      - Stop when the goal is popped; backtrack `came_from` goal → start; re-plan whenever a dot is eaten or a ghost invalidates the current path.
    - Why modularization approach was chosen
      - Single responsibility & testability: `maze.py`, `astar.py`, and `game.py` are each unit-testable in isolation (21 tests).
      - Rendering stays decoupled/optional: the identical autopilot runs headless, in a terminal, to PNG walkthroughs, or in pygame — important because pygame is unavailable in this environment.
      - Faithful refactor, not rewrite: the skeleton's geometry (wall rects, spawns, gate behaviour) is preserved and reused as the source of truth, minimising behavioural drift.
  - Final requirements check

    | Requirement | Status | Evidence |
    |---|---:|---|
    | Implement A* for automated pathfinding | ✅ | `astar.py` — open/closed sets, Manhattan heuristic, path backtracking |
    | Modularize: directions enum | ✅ | `directions.py` — `Direction` enum |
    | Modularize: wall detection | ✅ | `maze.py` — 6px tile rasterisation, doorway checks, dual graphs |
    | Modularize: ghost avoidance | ✅ | `astar.py::_ghost_danger_zone` — blocked + penalised cells |
    | Collect all food while avoiding ghosts | ✅ | 349/349 dots, `WON` in 12/12 seeds |
    | Automated demo (no keyboard) | ✅ | `run_demo.py` — no key events, A* drives every tick |
    | Tests pass | ✅ | 21 unit tests OK (incl. 3×3 micro-grid first) |