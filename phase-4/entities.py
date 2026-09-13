"""Pac-Man and ghost entities (grid-aware, no pygame dependency).

The original skeleton drove Pac-Man from keyboard input and drove ghosts along
hard-coded direction lists.  Here Pac-Man is driven by A* (see
:class:`game.Game`) and the ghosts behave as *moving obstacles* on the same
grid: each ghost does a biased random walk (mostly random, occasionally heading
toward Pac-Man) on the **ghost graph** (gate passable, so they can leave the
house) while never stepping onto Pac-Man's current cell.
"""
import random

from constants import (
    GHOST_CHASE_BIAS,
    GHOST_COLORS,
    GHOST_STARTS,
    PACMAN_COLOR,
)


class Entity:
    """A token living on a maze grid cell."""

    def __init__(self, cell, name, color, symbol):
        self.cell = cell
        self.name = name
        self.color = color
        self.symbol = symbol

    @property
    def position(self):
        return self.cell

    def __repr__(self):
        return f"{self.name}@{self.cell}"


class PacMan(Entity):
    """The player, driven entirely by A* (no keyboard input)."""

    def __init__(self, cell, maze):
        super().__init__(cell, "Pac-Man", PACMAN_COLOR, "P")
        self.maze = maze
        self.path = []          # list of (r, c) to follow
        self.path_index = 0     # next cell to move into
        self.eaten = 0

    # -- path following ------------------------------------------------------
    def set_path(self, path):
        """Install a new path (including the starting cell)."""
        self.path = list(path)
        # Start advancing from the second cell (index 1) - index 0 is 'here'.
        self.path_index = 1 if len(self.path) > 1 else 0

    @property
    def reached_target(self):
        return self.path_index >= len(self.path)

    def next_cell(self):
        if self.path and self.path_index < len(self.path):
            return self.path[self.path_index]
        return None

    def advance(self):
        """Move one cell along the current path.  Returns the cell entered or
        None when there is no path / the path is exhausted."""
        nxt = self.next_cell()
        if nxt is None:
            self.path = []
            self.path_index = 0
            return None
        self.cell = nxt
        self.path_index += 1
        return self.cell

    def replan_needed(self, ghost_cells):
        """True when Pac-Man needs a fresh A* path: no path in hand, target
        reached, or the immediate next cell is occupied by a ghost."""
        if not self.path or self.reached_target:
            return True
        nxt = self.next_cell()
        return nxt is None or nxt in ghost_cells


class Ghost(Entity):
    """A wandering ghost (moving obstacle)."""

    def __init__(self, index, cell, maze, seed=None):
        super().__init__(
            cell,
            ["Blinky", "Pinky", "Inky", "Clyde"][index],
            GHOST_COLORS[index],
            str(index + 1),
        )
        self.index = index
        # seed=None keeps the fixed per-index default (reproducible); a game
        # seed passed here creates varied-but-repeatable ghost behaviour.
        self._rng = random.Random(seed if seed is not None else 1000 + index)

    def move(self, maze, pacman_cell, occupied):
        """Pick one step on the *ghost* graph.

        ``occupied`` is the set of cells held by other entities (Pac-Man and the
        other ghosts) that this ghost must not step onto.  The ghost either
        heads toward Pac-Man (probability ``GHOST_CHASE_BIAS``) or takes a random
        legal step; it never moves onto an occupied cell.
        """
        options = [
            n for n in maze.neighbors(self.cell[0], self.cell[1], for_pacman=False)
            if n not in occupied and n != pacman_cell
        ]
        if not options:
            return  # cornered / at a dead end - stand still
        if self._rng.random() < GHOST_CHASE_BIAS:
            # bias: move to the option closest (Manhattan) to Pac-Man
            options.sort(key=lambda c: (abs(c[0] - pacman_cell[0])
                                        + abs(c[1] - pacman_cell[1]), c))
            self.cell = options[0]
        else:
            self.cell = self._rng.choice(options)


def make_pacman(maze, cell=None):
    """Factory keeping the spawn in one place."""
    from constants import PACMAN_START
    return PacMan(cell or PACMAN_START, maze)


def make_ghosts(maze, seed=None):
    """Factory: create the four ghosts at their canonical starts.

    ``seed`` shared by all four ghosts (None -> deterministic per-index seed)."""
    return [Ghost(i, GHOST_STARTS[i], maze, seed) for i in range(4)]
