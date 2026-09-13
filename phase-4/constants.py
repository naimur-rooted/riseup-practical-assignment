"""Game-wide constants for the Pac-Man A* project.

All geometry mirrors the original hbokmann/Pacman skeleton (a 606x606 maze
built from 6px-thick wall segments on a 19x19 grid of 30px cells). We keep the
exact wall rectangles as the single source of truth and derive a fine 6px tile
map at runtime so wall / passage detection is exact (see ``maze.py``).
"""

# --- Maze / grid geometry -------------------------------------------------
TILE_SIZE = 6            # pixel size of the fine navigation tile
CELL_SIZE = 30           # pixel size of one maze grid cell (5 tiles wide)
GRID_COLS = 19           # maze is 19x19 cells (matches the skeleton food grid)
GRID_ROWS = 19
MAZE_W_PX = 606          # total maze width  (5 * CELL_SIZE + 2 * GRID_OFFSET + ... )
MAZE_H_PX = 606
GRID_OFFSET = 6          # pixel offset of the maze interior from the screen edge

# --- Spawn positions (grid cells) -----------------------------------------
# Derived from the skeleton: Pacman at w=303-16=287, p_h=7*60+19=439 -> (14, 9)
PACMAN_START = (14, 9)
# Ghosts: Blinky above the house; Pinky/Inky/Clyde inside the ghost house.
BLINKY_START = (6, 9)
PINKY_START = (8, 9)
INKY_START = (8, 8)
CLYDE_START = (8, 10)
GHOST_STARTS = [BLINKY_START, PINKY_START, INKY_START, CLYDE_START]
GHOST_NAMES = ["Blinky", "Pinky", "Inky", "Clyde"]

# --- Movement timing -------------------------------------------------------
PACMAN_SPEED = 1            # grid cells Pac-Man advances per tick
GHOST_TICK_EVERY = 2        # ghosts move once every N Pac-Man ticks
GHOST_CHASE_BIAS = 0.5      # probability a ghost biases toward Pac-Man (else random walk)

# --- A* ghost-avoidance tuning --------------------------------------------
# A ghost's own cell is always impassable for Pac-Man; cells immediately
# adjacent to a ghost (Manhattan distance 1) are heavily penalised so A* routes
# around danger while still guaranteeing a path exists.
GHOST_CELL_BLOCKED = True        # hard block the cell a ghost currently occupies
GHOST_ADJACENT_PENALTY = 50      # extra cost added to cells adjacent to a ghost

# --- Rendering -------------------------------------------------------------
BG_COLOR = (0, 0, 0)             # black
WALL_COLOR = (0, 0, 255)         # blue
GATE_COLOR = (255, 255, 255)     # white (gate)
FOOD_COLOR = (255, 255, 255)     # white dots
PACMAN_COLOR = (255, 255, 0)     # yellow
GHOST_COLORS = [
    (255, 0, 0),       # Blinky - red
    (255, 0, 255),     # Pinky - pink (purple-ish)
    (0, 255, 255),     # Inky - cyan
    (255, 165, 0),     # Clyde - orange
]

# Ghost-house interior cells (blocked for Pac-Man; passable for ghosts).
# Matches the skeleton's food-grid skip region.
GHOST_HOUSE_CELLS = [(7, 8), (7, 9), (7, 10), (8, 8), (8, 9), (8, 10)]
