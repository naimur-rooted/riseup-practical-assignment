"""A* pathfinding with ghost avoidance.

The pathfinder works on the 19x19 grid exposed by :class:`maze.Maze`.  It uses
the standard A* algorithm with a Manhattan-distance heuristic (admissible, hence
optimal for the base unit-cost graph) and adds *ghost avoidance* on top:

* a cell currently occupied by a ghost is **blocked** (Pac-Man never steps on a
  ghost), and
* a cell orthogonally adjacent to a ghost carries a large **penalty** cost, so
  the computed route steers well away from danger while still guaranteeing a
  path exists (the maze is well connected, so A* always finds one).

Ghosts move, so the path is recomputed whenever Pac-Man reaches his current
way-point - see :class:`game.Game` for the autopilot loop.
"""
import heapq

from constants import GHOST_ADJACENT_PENALTY
from directions import manhattan


def _ghost_danger_zone(ghost_positions):
    """Return (blocked_cells, penalised_cells) derived from ghost positions.

    ``blocked_cells``   - cells a ghost currently stands on (impassable).
    ``penalised_cells`` - cells orthogonally adjacent to a ghost (high cost).
    """
    blocked = set(ghost_positions)
    penalised = set()
    for r, c in ghost_positions:
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if (nr, nc) not in blocked:
                penalised.add((nr, nc))
    return blocked, penalised


def a_star(maze, start, goal, ghost_positions=()):
    """A* search from ``start`` to ``goal`` on Pac-Man's navigation graph.

    Parameters
    ----------
    maze : maze.Maze
        The maze (uses the Pacman graph - house & gate blocked).
    start, goal : (row, col)
        Grid cells.
    ghost_positions : iterable of (row, col)
        Current ghost cells; treated as moving obstacles.

    Returns
    -------
    list[(row, col)]
        The path including ``start`` and ``goal`` (empty list if no path).
    """
    blocked, penalised = _ghost_danger_zone(ghost_positions)
    ghost_set = set(ghost_positions)

    if goal in ghost_set or start in ghost_set:
        return []

    # (f_score, g_score, cell) heap.  ``closed`` prunes re-expanded nodes
    # (lazy-deletion A* - a node is only processed at its cheapest g_score).
    start_h = manhattan(start, goal)
    frontier = [(start_h, 0, start)]
    g_score = {start: 0}
    came_from = {}
    closed = set()

    while frontier:
        _f, _g, current = heapq.heappop(frontier)
        if current in closed:
            continue
        closed.add(current)
        if current == goal:
            path = [current]
            while path[-1] != start:
                path.append(came_from[path[-1]])
            path.reverse()
            return path

        cur_g = g_score[current]
        for nxt in maze.neighbors(current[0], current[1], for_pacman=True):
            if nxt in blocked:
                continue  # never step onto a living ghost
            step_cost = GHOST_ADJACENT_PENALTY if nxt in penalised else 1
            tentative_g = cur_g + step_cost
            if nxt in g_score and tentative_g >= g_score[nxt]:
                continue
            g_score[nxt] = tentative_g
            came_from[nxt] = current
            h = manhattan(nxt, goal)
            heapq.heappush(frontier, (tentative_g + h, tentative_g, nxt))
    return []


def nearest_food(maze, position, food_cells, ghost_positions=()):
    """Pick the closest remaining food by **Manhattan** distance.

    Manhattan is a cheap lower bound and is all we need to choose a target; the
    actual route (which respects walls and ghosts) is produced by :func:`a_star`.
    Returns the food cell, or None if nothing remains / is reachable.
    """
    ghost_set = set(ghost_positions)
    target = None
    best = None
    for food in food_cells:
        if food in ghost_set or (position == food):
            continue
        d = manhattan(position, food)
        if best is None or d < best:
            best = d
            target = food
    return target
