"""Renderers for the Pac-Man autopilot demo.

Two renderers are provided:

* :class:`TerminalRenderer` - ASCII/ANSI-free text rendering that works in any
  environment (used by default here, and by the headless demo).
* :class:`PygameRenderer`  - graphical rendering that mirrors the original
  skeleton's look, but draws everything with primitives (no external image or
  sound assets required).  Used automatically when pygame is importable.

Both renderers consume the same :class:`game.Game` state, so the game logic is
completely decoupled from how it is drawn.
"""

from constants import (
    BG_COLOR,
    FOOD_COLOR,
    GATE_COLOR,
    GRID_COLS,
    GRID_ROWS,
    PACMAN_COLOR,
    WALL_COLOR,
)


class Renderer:
    """Base renderer. Subclasses implement ``render(game)`` -> list[str]."""
    def render(self, game):
        raise NotImplementedError


class TerminalRenderer(Renderer):
    """Low-res text maze: walls as '#'/lines, food as '.', agents lettered."""

    def __init__(self, maze):
        self.maze = maze

    def _cell_char(self, game, r, c):
        # agents take priority
        if game.pacman.cell == (r, c):
            return 'P'
        for i, g in enumerate(game.ghosts):
            if g.cell == (r, c):
                return str(i + 1)
        if (r, c) in game.remaining_food:
            return '.'
        # empty corridor
        return ' '

    def _has_wall_below(self, r, c):
        """Horizontal wall between (r,c) and (r+1,c) on Pac-Man's graph."""
        if r + 1 >= GRID_ROWS:
            return True
        a = self.maze.is_walkable(r, c, True)
        b = self.maze.is_walkable(r + 1, c, True)
        if not a or not b:
            return True
        return not self.maze._door_open(r, c, r + 1, c, True)


    def render(self, game):
        maze = self.maze
        lines = []
        lines.append(
            f"tick={game.tick}  score={game.score}/{len(game.total_food)}  "
            f"food_left={len(game.remaining_food)}  "
            f"state={game.state.name if hasattr(game.state, 'name') else game.state}"
        )
        # --- classic ASCII maze: wall lines start with '+' and use '---' for a
        # closed passage, content lines use '|' for a vertical wall -------------
        def vertical_wall(r, c):
            """Vertical wall between cell (r, c-1) and (r, c) [or left border]."""
            if c == 0:
                return True
            a = maze.is_walkable(r, c, True)
            b = maze.is_walkable(r, c - 1, True)
            if not a or not b:
                return True
            return not maze._door_open(r, c - 1, r, c, True)

        # top border
        lines.append('+' + '---+' * GRID_COLS)
        for r in range(GRID_ROWS):
            # content line
            row_cells = ''
            for c in range(GRID_COLS):
                blocked = not maze.is_walkable(r, c, True)
                ch = '#' if blocked else self._cell_char(game, r, c)
                row_cells += ('|' if vertical_wall(r, c) else ' ') + ' ' + ch + ' '
            row_cells += '|'
            lines.append(row_cells)
            # horizontal-wall line below this row
            row_walls = '+'
            for c in range(GRID_COLS):
                row_walls += '---' if self._has_wall_below(r, c) else '   '
                row_walls += '+'
            lines.append(row_walls)
        return lines


class PygameRenderer(Renderer):
    """Graphical renderer (only used when pygame is importable)."""

    def __init__(self, maze):
        import pygame  # noqa: WPS433 - optional, imported lazily
        self.pygame = pygame
        self.maze = maze
        self.screen = pygame.display.set_mode((606, 606))
        pygame.display.set_caption("Pac-Man A* Autopilot")
        self.font = pygame.font.Font(None, 28)

    def _px(self, r, c):
        return self.maze.grid_to_pixel(r, c)

    def render(self, game):
        pg = self.pygame
        screen = self.screen
        screen.fill(BG_COLOR)
        # walls
        for rect in self.maze.wall_rects():
            x, y, w, h = rect
            pg.draw.rect(screen, WALL_COLOR, pg.Rect(x, y, w, h))
        gx, gy, gw, gh = self.maze.gate_rect()
        pg.draw.rect(screen, GATE_COLOR, pg.Rect(gx, gy, gw, gh))
        # food
        for (r, c) in game.remaining_food:
            px, py = self._px(r, c)
            pg.draw.ellipse(screen, FOOD_COLOR,
                            pg.Rect(px - 3, py - 3, 6, 6))
        # ghosts
        for g in game.ghosts:
            px, py = self._px(*g.cell)
            pg.draw.circle(screen, g.color, (px, py), 10)
        # pacman
        px, py = self._px(*game.pacman.cell)
        pg.draw.circle(screen, PACMAN_COLOR, (px, py), 12)
        # score
        img = self.font.render(
            f"score {game.score}/{len(game.total_food)}", True, (255, 0, 0))
        screen.blit(img, (8, 4))
        pg.display.flip()


def get_renderer(maze, prefer_pygame=True):
    """Pick a pygame renderer when available, else fall back to the terminal."""
    if prefer_pygame:
        try:
            import pygame  # noqa: WPS433
            pygame.init()
            return PygameRenderer(maze)
        except Exception:
            pass
    return TerminalRenderer(maze)
