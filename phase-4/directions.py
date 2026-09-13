"""Direction enum for Pac-Man / ghost movement.

Each cardinal direction carries its grid delta ``(d_row, d_col)`` and, when
pygame is available, the matching key it would otherwise be bound to (kept for
parity with the original skeleton's keyboard controls).
"""
from enum import Enum


class Direction(Enum):
    """The four cardinal movement directions on the 19x19 grid."""
    NORTH = (-1, 0)   # up    -> decreasing row
    SOUTH = (1, 0)    # down  -> increasing row
    WEST = (0, -1)    # left  -> decreasing col
    EAST = (0, 1)     # right -> increasing col

    @property
    def d_row(self) -> int:
        return self.value[0]

    @property
    def d_col(self) -> int:
        return self.value[1]

    def delta(self):
        """Return the (dr, dc) tuple for this direction."""
        return self.value

    def move(self, row: int, col: int):
        """Return the grid cell reached by moving one step in this direction."""
        return (row + self.d_row, col + self.d_col)

    def opposite(self) -> "Direction":
        return Direction((-self.d_row, -self.d_col))

    @classmethod
    def from_delta(cls, d_row: int, d_col: int) -> "Direction":
        """Recover a Direction from a (dr, dc) delta, or None if not cardinal."""
        for d in cls:
            if d.value == (d_row, d_col):
                return d
        return None

    @staticmethod
    def pygame_key():
        """Map directions to pygame key constants (None when pygame absent).

        Kept so the original keyboard control scheme is still representable even
        though autopilot mode does not use it.
        """
        try:
            import pygame  # noqa: WPS433  (optional dependency)
        except Exception:  # pragma: no cover - pygame is optional
            return None
        return {
            Direction.NORTH: pygame.K_UP,
            Direction.SOUTH: pygame.K_DOWN,
            Direction.WEST: pygame.K_LEFT,
            Direction.EAST: pygame.K_RIGHT,
        }


def manhattan(a, b) -> int:
    """Manhattan distance between two grid cells ``(r, c)``."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])
