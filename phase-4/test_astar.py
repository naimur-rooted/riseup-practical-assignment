"""Unit tests for the Pac-Man A* pathfinding modules.

Run from the ``phase-4`` directory (or with ``python -m unittest test_astar``).

Covers:
* ``Direction`` enum (module ``directions``)
* Wall detection & maze graph (module ``maze`` - passage/gate/house rules)
* A* search & ghost avoidance (module ``astar``)
* End-to-end autopilot: every dot collected without dying (module ``game``)
"""
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import astar
from directions import Direction, manhattan
from entities import Ghost
from game import Game, GameState
from maze import MAZE


class DirectionTests(unittest.TestCase):
    def test_cardinal_deltas(self):
        self.assertEqual(Direction.NORTH.delta(), (-1, 0))
        self.assertEqual(Direction.SOUTH.delta(), (1, 0))
        self.assertEqual(Direction.WEST.delta(), (0, -1))
        self.assertEqual(Direction.EAST.delta(), (0, 1))

    def test_move(self):
        self.assertEqual(Direction.NORTH.move(14, 9), (13, 9))
        self.assertEqual(Direction.EAST.move(14, 9), (14, 10))

    def test_opposite(self):
        self.assertIs(Direction.NORTH.opposite(), Direction.SOUTH)
        self.assertIs(Direction.EAST.opposite(), Direction.WEST)

    def test_from_delta(self):
        self.assertIs(Direction.from_delta(0, 1), Direction.EAST)
        self.assertIsNone(Direction.from_delta(1, 1))

    def test_manhattan(self):
        self.assertEqual(manhattan((0, 0), (3, 4)), 7)


class MazeTests(unittest.TestCase):
    def test_dimensions(self):
        self.assertEqual(MAZE.grid_to_pixel(0, 0), (21, 21))
        self.assertEqual(MAZE.pixel_to_grid(21, 21), (0, 0))
        self.assertEqual(MAZE.pixel_to_grid(291, 441), (14, 9))  # Pac-Man spawn

    def test_pacman_spawn_corridor(self):
        self.assertTrue(MAZE.is_walkable(14, 9, for_pacman=True))

    def test_ghost_house_rules(self):
        # Pac-Man can never enter the ghost house ...
        for cell in MAZE._house:
            self.assertFalse(MAZE.is_walkable(*cell, for_pacman=True))
        # ... but ghosts can live inside it and pass through the gate.
        self.assertTrue(MAZE.is_walkable(8, 9, for_pacman=False))
        self.assertTrue(MAZE._door_open(7, 9, 8, 9, for_pacman=False))
        self.assertFalse(MAZE._door_open(7, 9, 8, 9, for_pacman=True))

    def test_internal_wall_detection(self):
        # Vertical wall at x=180 (y=240..366) blocks east-west around row 9 ...
        self.assertFalse(MAZE._door_open(9, 5, 9, 6, for_pacman=True))
        # ... but the same wall does not reach below y=366 (row 14), so it is
        # open there.
        self.assertTrue(MAZE._door_open(14, 5, 14, 6, for_pacman=True))

    def test_walkable_and_food_count(self):
        walkable = sum(1 for r in range(19) for c in range(19)
                       if MAZE.is_walkable(r, c, for_pacman=True))
        self.assertEqual(walkable, 355)
        self.assertEqual(len(MAZE.food_cells), 349)
        # every reachable cell is collectable by A*
        src = (14, 9)
        for cell in list(MAZE.food_cells)[:50]:
            self.assertGreater(MAZE.distance_to(src, cell), 0)

    def test_all_food_reachable(self):
        src = (14, 9)
        for cell in MAZE.food_cells:
            self.assertGreaterEqual(MAZE.distance_to(src, cell), 0)
        unreachable = [cell for cell in MAZE.food_cells
                       if MAZE.distance_to(src, cell) < 0]
        self.assertEqual(unreachable, [])


class AStarTests(unittest.TestCase):
    def test_short_adjacent_path(self):
        path = astar.a_star(MAZE, (14, 9), (14, 8))
        self.assertEqual(path, [(14, 9), (14, 8)])

    def test_path_is_valid_on_grid(self):
        goal = (1, 1)
        path = astar.a_star(MAZE, (14, 9), goal)
        self.assertTrue(path)
        self.assertEqual(path[0], (14, 9))
        self.assertEqual(path[-1], goal)
        for a, b in zip(path, path[1:]):
            self.assertIn(b, MAZE.neighbors(*a, for_pacman=True))

    def test_visits_ghost_house_cell(self):
        # Pac-Man's graph forbids the ghost house entirely.
        path = astar.a_star(MAZE, (14, 9), (7, 9))
        self.assertEqual(path, [])

    def test_avoids_ghost(self):
        ghost = (6, 3)
        goal = (6, 2)
        path = astar.a_star(MAZE, (14, 9), goal, ghost_positions=[ghost])
        self.assertNotIn(ghost, path)
        self.assertEqual(path[-1], goal)

    def test_nearest_food(self):
        self.assertEqual(astar.nearest_food(MAZE, (14, 9), MAZE.food_cells),
                         (14, 8))

    def test_a_star_cannot_enter_blocked_cell(self):
        for goal in ((7, 8), (7, 9), (7, 10), (8, 8), (8, 9), (8, 10)):
            self.assertEqual(astar.a_star(MAZE, (14, 9), goal), [])


class GhostTests(unittest.TestCase):
    def test_ghosts_can_exit_house(self):
        # From inside the house, a ghost can step north through the open gate.
        maze = MAZE
        self.assertIn((7, 9), maze.neighbors(8, 9, for_pacman=False))


class GameTests(unittest.TestCase):
    def test_autopilot_collects_every_dot(self):
        random.seed(7)
        game = Game(ghost_tick_every=4)
        state = game.run(max_ticks=60000)
        self.assertEqual(state, GameState.WON)
        self.assertEqual(game.score, len(game.total_food))
        self.assertEqual(game.remaining_food, set())


if __name__ == "__main__":
    unittest.main(verbosity=2)