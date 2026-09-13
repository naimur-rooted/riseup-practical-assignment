"""Maze representation & wall detection for Pac-Man.

The original skeleton (hbokmann/Pacman) defines the maze as a list of 6px-thick
wall rectangles.  Movement, however, happens in 30px increments, so the walls
end up sitting *between* the 19x19 grid cells rather than inside them.

To do exact wall / passage detection we therefore:

1. Rasterise the wall rectangles onto a fine **6px tile map** (101x101).  A tile
   is a wall if its centre falls inside any wall (or the gate) rectangle.
2. Derive a 19x19 grid (each cell = 5x5 tiles).  Two cells are adjacent only
   when the **doorway** between them (the boundary tiles) contains no wall, so
   A* never walks through walls.
3. Two navigation graphs are exposed:
   * **Pacman graph** - the gate and the ghost-house interior are blocked, so
     Pac-Man can never enter the ghost house (mirrors the skeleton, where the
     gate blocks the player sprite).
   * **Ghost graph**  - only solid walls block; the gate is passable so ghosts
     can leave the house through it.

Everything below is a pure-Python deterministic derivation of the skeleton's
``WALLS`` list, so no image assets are required.
"""
from collections import deque

from constants import (
    CELL_SIZE,
    GHOST_HOUSE_CELLS,
    GRID_COLS,
    GRID_ROWS,
    GRID_OFFSET,
    MAZE_W_PX,
    PACMAN_START,
    TILE_SIZE,
)


def _center_in_rect(cx, cy, rect):
    """True if point (cx, cy) lies inside an [x, y, w, h] rectangle."""
    x, y, w, h = rect
    return x <= cx < x + w and y <= cy < y + h


# --------------------------------------------------------------------------- #
# Wall rectangles straight from the hbokmann skeleton.
# Each entry: [x, y, width, height]  (pixels)
# --------------------------------------------------------------------------- #
WALLS = [
    [0, 0, 6, 600], [0, 0, 600, 6], [0, 600, 606, 6], [600, 0, 6, 606],
    [300, 0, 6, 66], [60, 60, 186, 6], [360, 60, 186, 6], [60, 120, 66, 6],
    [60, 120, 6, 126], [180, 120, 246, 6], [300, 120, 6, 66], [480, 120, 66, 6],
    [540, 120, 6, 126], [120, 180, 126, 6], [120, 180, 6, 126], [360, 180, 126, 6],
    [480, 180, 6, 126], [180, 240, 6, 126], [180, 360, 246, 6],
    [420, 240, 6, 126], [240, 240, 42, 6], [324, 240, 42, 6], [240, 240, 6, 66],
    [240, 300, 126, 6], [360, 240, 6, 66], [0, 300, 66, 6], [540, 300, 66, 6],
    [60, 360, 66, 6], [60, 360, 6, 186], [480, 360, 66, 6], [540, 360, 6, 186],
    [120, 420, 366, 6], [120, 420, 6, 66], [480, 420, 6, 66], [180, 480, 246, 6],
    [300, 480, 6, 66], [120, 540, 126, 6], [360, 540, 126, 6],
]

# The gate (Pac-Man cannot pass; ghosts can).
GATE = [282, 242, 42, 2]


class Maze:
    """The Pac-Man maze: wall detection, grid conversion and navigation."""

    TILES_PER_CELL = CELL_SIZE // TILE_SIZE     # 5
    N_TILES = MAZE_W_PX // TILE_SIZE            # 101

    def __init__(self):
        # Fine 6px wall tile map (True = wall tile).
        self._tile_wall = [[False] * self.N_TILES for _ in range(self.N_TILES)]
        self._tile_gate = [[False] * self.N_TILES for _ in range(self.N_TILES)]
        for r in range(self.N_TILES):
            for c in range(self.N_TILES):
                cx = c * TILE_SIZE + TILE_SIZE // 2
                cy = r * TILE_SIZE + TILE_SIZE // 2
                self._tile_wall[r][c] = any(
                    _center_in_rect(cx, cy, rect) for rect in WALLS)
                # NOTE: the gate is intentionally NOT included here so that
                # ghosts (for_pacman=False) can leave the house through it.
                self._tile_gate[r][c] = _center_in_rect(cx, cy, GATE)
        self._house = set(GHOST_HOUSE_CELLS)
        self._pacman_grid = self._build_grid(True)
        self._ghost_grid = self._build_grid(False)
        self._food_cells = self._compute_food()

    # -- tile / cell helpers ------------------------------------------------
    def _cell_origin(self, index):
        """First tile index belonging to grid cell ``index`` (cell 0 -> tile 1)."""
        return 1 + self.TILES_PER_CELL * index

    def _center_tile(self, r, c):
        """Tile (row, col) whose centre sits at the centre of cell (r, c)."""
        tr = self._cell_origin(r) + self.TILES_PER_CELL // 2
        tc = self._cell_origin(c) + self.TILES_PER_CELL // 2
        return tr, tc

    def _is_gate_tile(self, tr, tc):
        """True if tile (tr, tc) centre lies inside the gate rectangle."""
        if not (0 <= tr < self.N_TILES and 0 <= tc < self.N_TILES):
            return False
        return self._tile_gate[tr][tc]

    def _cell_is_blocked(self, r, c, for_pacman):
        """A cell is blocked if its centre tile is a wall, or (for Pac-Man) if it
        lies inside the ghost house or on the gate."""
        tr, tc = self._center_tile(r, c)
        blocked = self._tile_wall[tr][tc]
        if for_pacman and (self._is_gate_tile(tr, tc) or (r, c) in self._house):
            blocked = True
        return blocked

    def _build_grid(self, for_pacman):
        grid = [[0] * GRID_COLS for _ in range(GRID_ROWS)]
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                if self._cell_is_blocked(r, c, for_pacman):
                    grid[r][c] = 1
        return grid

    # -- door / passage detection -------------------------------------------
    def _door_open(self, r1, c1, r2, c2, for_pacman):
        """True when the passage between two orthogonally adjacent cells is open.

        Wall segments are 1 tile (6px) thick and sit on the boundary between
        cells, so we inspect the boundary tiles: if *any* of them is a wall (or
        the gate, for Pac-Man) the passage is closed.
        """
        t1r = self._cell_origin(r1)
        t1c = self._cell_origin(c1)
        dr, dc = r2 - r1, c2 - c1
        if dc == 1:                       # east
            cols = (t1c + 4, t1c + 5)
            rows = (t1r + 1, t1r + 2, t1r + 3)
        elif dc == -1:                    # west
            cols = (t1c - 1, t1c)
            rows = (t1r + 1, t1r + 2, t1r + 3)
        elif dr == 1:                     # south
            cols = (t1c + 1, t1c + 2, t1c + 3)
            rows = (t1r + 4, t1r + 5)
        elif dr == -1:                    # north
            cols = (t1c + 1, t1c + 2, t1c + 3)
            rows = (t1r - 1, t1r)
        else:
            return False
        for rr in rows:
            for cc in cols:
                if self._tile_wall[rr][cc]:
                    return False
                if for_pacman and self._is_gate_tile(rr, cc):
                    return False
        return True

    # -- public navigation API ----------------------------------------------
    def in_bounds(self, r, c) -> bool:
        return 0 <= r < GRID_ROWS and 0 <= c < GRID_COLS

    def is_walkable(self, r, c, for_pacman=True) -> bool:
        """True if (r, c) is in-bounds and not a blocked cell for the mover."""
        return self.in_bounds(r, c) and not self._cell_is_blocked(r, c, for_pacman)

    def neighbors(self, r, c, for_pacman=True):
        """Walkable, door-connected neighbours of (r, c)."""
        out = []
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if self.is_walkable(nr, nc, for_pacman) and \
                    self._door_open(r, c, nr, nc, for_pacman):
                out.append((nr, nc))
        return out

    def _compute_food(self):
        """All cells Pac-Man can reach from his start (the collectible dots).

        Starting from ``PACMAN_START`` we flood-fill the Pac-Man graph.  This
        automatically excludes the unreachable pocket tucked behind the ghost
        house, guaranteeing that 'collect every dot' is always achievable and
        that A* never returns a path to an unreachable cell.
        """
        start = PACMAN_START
        seen = {start}
        queue = deque([start])
        while queue:
            r, c = queue.popleft()
            for nr, nc in self.neighbors(r, c, for_pacman=True):
                if (nr, nc) not in seen:
                    seen.add((nr, nc))
                    queue.append((nr, nc))
        seen.discard(start)
        return seen

    @property
    def food_cells(self):
        """Set of grid cells that contain a dot Pac-Man must collect."""
        return set(self._food_cells)

    def distance_to(self, src, dst) -> int:
        """Exact shortest path length between two cells (BFS, ghosts ignored).

        Returns -1 if no path exists."""
        if src == dst:
            return 0
        seen = {src}
        queue = deque([(src, 0)])
        while queue:
            (r, c), d = queue.popleft()
            for nr, nc in self.neighbors(r, c, for_pacman=True):
                if (nr, nc) == dst:
                    return d + 1
                if (nr, nc) not in seen:
                    seen.add((nr, nc))
                    queue.append(((nr, nc), d + 1))
        return -1

    # -- coordinate conversion ----------------------------------------------
    def grid_to_pixel(self, r, c):
        """Pixel centre of grid cell (r, c)."""
        return (GRID_OFFSET + c * CELL_SIZE + CELL_SIZE // 2,
                GRID_OFFSET + r * CELL_SIZE + CELL_SIZE // 2)

    def pixel_to_grid(self, x, y):
        """Grid cell (row, col) containing pixel (x, y)."""
        return ((y - GRID_OFFSET) // CELL_SIZE,
                (x - GRID_OFFSET) // CELL_SIZE)

    # -- visualisation helpers ----------------------------------------------
    def wall_rects(self):
        """Original wall rectangles - used by the graphical renderer."""
        return list(WALLS)

    def gate_rect(self):
        return GATE

    def render_cells(self):
        """Coarse 19x19 overview: '#' for blocked cells, '.' otherwise."""
        return [['#' if self._cell_is_blocked(r, c, True) else '.'
                 for c in range(GRID_COLS)] for r in range(GRID_ROWS)]


# A module-level singleton keeps the (deterministic) maze in one place.
MAZE = Maze()

