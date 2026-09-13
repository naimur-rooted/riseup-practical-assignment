"""Generate a visual walkthrough of the A* autopilot as PNG images.

No pygame is required - frames are drawn with matplotlib (Agg backend).  By
default it saves a handful of key frames spanning the whole run::

    python render_walkthrough.py                 # saves to ./walkthrough/
    python render_walkthrough.py --every 100     # also save every 100 ticks
    python render_walkthrough.py --save-dir out
"""
import argparse
import os
import random
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, Rectangle  # noqa: E402

sys.path.insert(0, ".")

from game import Game, GameState  # noqa: E402
from maze import MAZE            # noqa: E402


def _rgb(color):
    """Convert a 0-255 RGB tuple to 0-1 floats for matplotlib."""
    return tuple(c / 255.0 for c in color)


def save_frame(game, path):
    """Render the current game state to a PNG using a fresh figure."""
    maze = game.maze
    fig, ax = plt.subplots(figsize=(6.2, 6.2), dpi=100)
    ax.set_xlim(0, 606)
    ax.set_ylim(606, 0)                # screen coordinates: y grows downward
    ax.axis("off")
    for rect in maze.wall_rects():
        x, y, w, h = rect
        ax.add_patch(Rectangle((x, y), w, h, fc=_rgb((0, 0, 255)), ec="none"))
    gx, gy, gw, gh = maze.gate_rect()
    ax.add_patch(Rectangle((gx, gy), gw, gh, fc=_rgb((255, 255, 255)), ec="none"))
    for (r, c) in game.remaining_food:
        px, py = maze.grid_to_pixel(r, c)
        ax.add_patch(Circle((px, py), 3, fc=_rgb((255, 255, 0)), ec="none"))
    for g in game.ghosts:
        px, py = maze.grid_to_pixel(*g.cell)
        ax.add_patch(Circle((px, py), 10, fc=_rgb(g.color), ec="none"))
    px, py = maze.grid_to_pixel(*game.pacman.cell)
    ax.add_patch(Circle((px, py), 12, fc=_rgb((255, 255, 0)), ec="black"))
    ax.set_title(f"tick {game.tick}  score {game.score}/{len(game.total_food)}",
                 fontsize=10)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print("  saved", path)


def main(argv=None):
    p = argparse.ArgumentParser(description="Pac-Man A* visual walkthrough (PNG).")
    p.add_argument("--save-dir", default="walkthrough")
    p.add_argument("--every", type=int, default=0,
                   help="also save a frame every N ticks")
    p.add_argument("--max-ticks", type=int, default=100000)
    p.add_argument("--seed", type=int, default=7)
    args = p.parse_args(argv)

    os.makedirs(args.save_dir, exist_ok=True)
    random.seed(args.seed)
    game = Game(maze=MAZE)
    total = len(game.total_food)

    milestones = [0.0, 0.25, 0.5, 0.75]
    saved = 0
    print("running autopilot and capturing frames ...")
    while game.state == GameState.PLAYING and game.tick < args.max_ticks:
        game.step()
        eaten = total - len(game.remaining_food)
        frac = eaten / total if total else 1.0
        if milestones and frac >= milestones[0]:
            label = f"{int(milestones[0] * 100):03d}pct_tick{game.tick}"
            save_frame(game, os.path.join(args.save_dir, f"frame_{label}.png"))
            saved += 1
            milestones.pop(0)
        if args.every and game.tick % args.every == 0:
            save_frame(game, os.path.join(args.save_dir, f"frame_tick{game.tick}.png"))
            saved += 1

    label = "win" if game.state == GameState.WON else game.state.name
    save_frame(game, os.path.join(args.save_dir, f"frame_final_{label}.png"))
    saved += 1

    print(f"state={game.state.name}  ticks={game.tick}  "
          f"score={game.score}/{total}  frames_saved={saved}")
    return 0


if __name__ == "__main__":
    sys.exit(main())