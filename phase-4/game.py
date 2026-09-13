"""Autopilot game loop - runs Pac-Man with A* pathfinding (no keyboard input).

The game owns the maze, Pac-Man, the ghosts and the remaining dots.  Every tick
Pac-Man either follows his current A* path or re-plans toward the nearest
remaining dot; the ghosts wander on their own graph.  Ghost avoidance lives in
``astar.py`` (their cells are blocked, adjacent cells penalised), so Pac-Man
collects all food without ever moving onto a ghost.
"""
from enum import Enum

import astar
from entities import PacMan, make_ghosts
from maze import MAZE
from renderers import TerminalRenderer


class GameState(Enum):
    PLAYING = "playing"
    WON = "won"
    LOST = "lost"


class Game:
    """Pac-Man driven entirely by A* - no keyboard input required."""

    def __init__(self, maze=None, renderer=None, ghost_tick_every=2,
                 ghost_seed=None):
        self.maze = maze or MAZE
        self.renderer = renderer                      # optional pygame renderer
        self.ghost_tick_every = ghost_tick_every
        self.total_food = set(self.maze.food_cells)
        self.remaining_food = set(self.maze.food_cells)
        self.pacman = PacMan((14, 9), self.maze)
        self.ghosts = make_ghosts(self.maze, ghost_seed)
        self.score = 0
        self.tick = 0
        self.state = GameState.PLAYING
        # terminal renderer is always available for text / log output
        self._term = TerminalRenderer(self.maze)
        # seed an initial path toward the nearest dot
        self._replan_pacman(self._ghost_cells())

    # -- helpers ------------------------------------------------------------
    def _ghost_cells(self):
        return [g.cell for g in self.ghosts]

    def _replan_pacman(self, ghost_cells):
        target = astar.nearest_food(
            self.maze, self.pacman.cell, self.remaining_food, ghost_cells)
        if target is None:
            self.pacman.set_path([self.pacman.cell])
            return False
        path = astar.a_star(self.maze, self.pacman.cell, target, ghost_cells)
        if not path:
            return False
        self.pacman.set_path(path)
        return True

    # -- one simulation step ------------------------------------------------
    def step(self):
        if self.state != GameState.PLAYING:
            return

        # 1) Move ghosts first.  They never step onto Pac-Man's current cell, and
        #    we resolve collisions between ghosts by tracking live occupancy.
        if self.tick % self.ghost_tick_every == 0:
            occupied = {self.pacman.cell}
            for g in self.ghosts:
                occupied.discard(g.cell)
                g.move(self.maze, self.pacman.cell, occupied)
                occupied.add(g.cell)

        ghost_cells = self._ghost_cells()

        # 2) Pac-Man: replan if he has no path, finished his path, or his next
        #    cell is now occupied by a ghost.
        if self.pacman.replan_needed(ghost_cells):
            self._replan_pacman(ghost_cells)
        self.pacman.advance()

        # 3) eat dot
        if self.pacman.cell in self.remaining_food:
            self.remaining_food.discard(self.pacman.cell)
            self.score += 1
            self.pacman.eaten += 1

        # 4) collision check (guard - avoidance should prevent this)
        if self.pacman.cell in ghost_cells:
            self.state = GameState.LOST
            return

        # 5) win check
        if not self.remaining_food:
            self.state = GameState.WON

        self.tick += 1

    # -- rendering ----------------------------------------------------------
    def render_lines(self):
        return self._term.render(self)

    def draw(self):
        """Draw with the pygame renderer if present (no-op otherwise)."""
        if self.renderer is not None:
            self.renderer.render(self)

    # -- running ------------------------------------------------------------
    def run(self, max_ticks=300000, render_every=0, on_frame=None):
        """Run until Pac-Man wins/loses or ``max_ticks`` elapse.

        ``render_every`` - print a terminal frame every N ticks (0 = never).
        ``on_frame``    - callback(frame_no, lines) for custom output/logging.
        """
        while self.state == GameState.PLAYING and self.tick < max_ticks:
            self.step()
            if render_every and self.tick % render_every == 0 and on_frame is not None:
                on_frame(self.tick, self.render_lines())
        # final frame
        if on_frame is not None:
            on_frame(self.tick, self.render_lines())
        self.draw()
        return self.state
