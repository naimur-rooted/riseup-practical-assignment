# Phase 4 — Pac-Man A* Pathfinding

Automated pathfinding for Pac-Man: **A\*** drives the yellow fellow through the
classic maze, collecting every dot while avoiding the four ghosts — completely
**without keyboard input**.

Built by refactoring the reference skeleton
[hbokmann/Pacman (pacman.py)](https://github.com/hbokmann/Pacman/blob/master/pacman.py)
into clean, modular Python.

---

## Objectives met

| Objective | Where |
|---|---|
| Implement A* for automated pathfinding | `astar.py` |
| Modularise code: direction enum | `directions.py` |
| Modularise code: wall detection | `maze.py` |
| Modularise code: ghost avoidance | `astar.py` (`_ghost_danger_zone`, penalties) |
| Collect all food while avoiding ghosts | `game.py` autopilot loop |
| Automated demo without keyboard input | `run_demo.py` |

---

## Module overview

```
phase-4/
├── constants.py           grid / spawn / tuning constants
├── directions.py          Direction enum (N/S/E/W) + Manhattan distance
├── maze.py                wall rectangles, 6px tile rasterisation, two grids
│                          (Pac-Man graph: gate+house blocked; ghost graph:
│                          gate open), food cells, pixel<->grid conversion
├── astar.py               A* search + ghost avoidance + nearest-dot picker
├── entities.py            PacMan (path follower) and Ghost (wanderer)
├── renderers.py           TerminalRenderer (text) + PygameRenderer (graphics)
├── game.py                Game autopilot loop (no keyboard)
├── run_demo.py            ← automated demo entry point (no keyboard)
├── render_walkthrough.py  saves visual-walkthrough PNGs (matplotlib)
├── test_astar.py          19 unit tests
└── walkthrough/           sample frames saved by render_walkthrough.py
```

### How the maze is modelled (wall detection)

The skeleton defines the maze as **6px-thick wall rectangles** while Pac-Man
moves in **30px steps** — so the walls sit *between* the 19×19 grid cells rather
than inside them. `maze.py` therefore:

1. rasterises every wall rectangle onto a fine **6px tile map** (101×101);
2. derives the 19×19 cell grid (each cell = 5×5 tiles);
3. decides two adjacent cells are connected only when the **doorway** between
   them (the boundary tiles) is clear — this is exactly what stops A* from
   walking through a wall;
4. exposes **two graphs** to mirror the skeleton's gate behaviour:
   * *Pac-Man graph* — the gate and the ghost-house interior are blocked;
   * *Ghost graph* — the gate is passable, so ghosts can leave the house;
5. computes the food as the set of cells reachable from Pac-Man's spawn, which
   automatically excludes the unreachable pocket behind the ghost house, so
   *"collect all dots" is always achievable*.

### A* with ghost avoidance (`astar.py`)

* heuristic: Manhattan distance (admissible),
* **blocked** cells: the cell any ghost currently occupies,
* **penalised** cells: any cell orthogonally adjacent to a ghost (large extra
  cost in the g-score), so the route steers around danger whenever an
  alternative exists — yet a path is still found if the ghost is unavoidable.

### Autopilot loop (`game.py`)

Every tick:

1. ghosts wander (biased random walk on the ghost graph, never onto Pac-Man),
2. if Pac-Man's path is exhausted / his next cell is a live ghost cell, he
   **re-plans** with A* toward the nearest remaining dot,
3. Pac-Man advances one cell; dots are eaten; ghost hit ⇒ `lost`,
4. all dots gone ⇒ `won`.

Nothing reads from the keyboard.

---

## Running

```bash
cd phase-4

# 1) automated demo - collect every dot, no keyboard input
python run_demo.py

# 2) demo with a maze frame printed periodically (the "text walkthrough")
python run_demo.py --render-every 200

# 3) every tick (very chatty)
python run_demo.py --full-render

# 4) graphical pygame renderer (if pygame is installed; not required)
python run_demo.py --pygame

# 5) unit tests
python -m unittest test_astar -v

# 6) save visual-walkthrough PNGs (matplotlib, no pygame needed)
python render_walkthrough.py
```

Expected demo result:

```
RESULT : WIN - Pac-Man collected every dot !
ticks      : ~600-740  (depends on the ghost seed)
score      : 349/349
dots left  : 0
```

---

## Design notes & limitations

* **Ghosts** use a biased random walk (moving obstacles) rather than the
  original hard-coded direction lists or full chase AI — this keeps them dynamic
  (they leave the house through the gate) while the focus stays on Pac-Man's A*.
* **Nearest-dot strategy** is a greedy heuristic (re-plan after each dot); it is
  *not* the optimal travelling-salesman tour, but it clears the maze in ~730
  ticks every run.
* Rendering is **decoupled** from logic: the game runs identically headless,
  in a terminal, via matplotlib PNGs, or through pygame (pygame absent here —
  Python 3.14 has no wheel — so the terminal / matplotlib paths are default).
* No external image, sound, or font assets are required.

## References

* Code skeleton: <https://github.com/hbokmann/Pacman/blob/master/pacman.py>
* A* tutorial video: <https://www.youtube.com/watch?v=-L-WgKMFuhE>