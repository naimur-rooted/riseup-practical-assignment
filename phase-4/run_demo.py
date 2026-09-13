"""Automated Pac-Man A* demo - runs the whole game with NO keyboard input.

Pac-Man is fully driven by the A* autopilot: the algorithm re-plans toward the
nearest remaining dot while ghosts wander and are avoided.  Run it with::

    python run_demo.py                 # headless (terminal) - prints frames

Optional flags:
    --max-ticks N     safety cap on simulation steps (default 300000)
    --render-every N  print a maze frame every N ticks (default 250)
    --full-render     print a maze frame every tick (noisy! for walkthroughs)
    --pygame          try the graphical (pygame) renderer if pygame is installed
    --ghost-every N   ghosts move once every N Pac-Man ticks (default 2)
"""
import argparse
import random
import sys
import time

sys.path.insert(0, ".")

from game import Game, GameState  # noqa: E402
from maze import MAZE            # noqa: E402


def build_parser():
    p = argparse.ArgumentParser(description="Pac-Man A* autopilot (no keyboard).")
    p.add_argument("--max-ticks", type=int, default=300000)
    p.add_argument("--render-every", type=int, default=250)
    p.add_argument("--full-render", action="store_true")
    p.add_argument("--pygame", action="store_true")
    p.add_argument("--ghost-every", type=int, default=2)
    p.add_argument("--seed", type=int, default=7, help="random seed for ghosts")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    random.seed(args.seed)
    render_every = 1 if args.full_render else args.render_every

    # optional graphical renderer
    renderer = None
    if args.pygame:
        try:
            from renderers import PygameRenderer
            import pygame  # noqa: F401
            pygame.init()
            renderer = PygameRenderer(MAZE)
            print("[demo] using the pygame graphical renderer")
        except Exception as exc:  # pragma: no cover
            print(f"[demo] pygame unavailable ({exc}); falling back to terminal")

    game = Game(maze=MAZE, renderer=renderer, ghost_tick_every=args.ghost_every,
                ghost_seed=args.seed)

    print("=" * 58)
    print("  PAC-MAN A* AUTOPILOT  (runs without keyboard input)")
    print("=" * 58)
    print(f"  maze dots : {len(game.total_food)}")
    print(f"  ghosts    : {len(game.ghosts)}  (move every {args.ghost_every} ticks)")
    print(f"  seed      : {args.seed}")
    print("-" * 58)

    started = time.time()

    def on_frame(tick, lines):
        if args.full_render or (render_every and tick % render_every == 0):
            for line in lines:
                print(line)
            print("-" * 58)

    final_state = game.run(
        max_ticks=args.max_ticks,
        render_every=render_every,
        on_frame=on_frame,
    )
    elapsed = time.time() - started

    print("=" * 58)
    if final_state == GameState.WON:
        print("  RESULT : WIN - Pac-Man collected every dot !")
    elif final_state == GameState.LOST:
        print("  RESULT : GAME OVER - Pac-Man collided with a ghost.")
    else:
        print("  RESULT : stopped before finishing (max-ticks reached).")
    print("-" * 58)
    print(f"  ticks      : {game.tick}")
    print(f"  score      : {game.score}/{len(game.total_food)}")
    print(f"  dots left  : {len(game.remaining_food)}")
    print(f"  elapsed    : {elapsed:.2f} s")
    print(f"  final cell : {game.pacman.cell}")
    print("=" * 58)
    return 0 if final_state == GameState.WON else 1


if __name__ == "__main__":
    sys.exit(main())