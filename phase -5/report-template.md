# Phase 5 — APA 7 Report Template

> **How to use this scaffold:** keep the `#` headings exactly as they are (APA 7 structure). Each section has a `[Placeholder: …]` line followed by requirement-analysis bullets (Phase 2–4 notes) telling you what to write. Replace the placeholder lines and expand the bullets into polished prose — one section at a time. Cross-reference the finished version in this same folder (`TECHNICAL_REPORT.md`, local-only) for fully written text.

# Abstract

[Placeholder: 150–250 words summary]

- Scope: three practical phases — Phase 2 (tabular Q-learning, single + multi-agent), Phase 3 (multi-agent DQN), Phase 4 (Pac-Man A* autopilot).
- Method in one sentence: from-scratch, seeded (SEED = 42), exhaustively evaluated with frozen parameters.
- Headline numbers to include: Phase 3 — 99.50% (597/600) exhaustive success, 0 head-on collisions, 416.1 s ≤ 600 s budget; Phase 4 — 349/349 dots, WON 12/12 seeds, 21/21 tests.
- End with: discussion themes (independent vs shared learning, cost-bounded engineering, admissibility, re-planning) + limitations/future work in one clause.

# Introduction

[Placeholder: context, references]

- Context: RiseUp Asia Python AI Researcher/Intern practical assignment; the assignment's arc from learned policies (Phases 2–3) to model-based search (Phase 4).
- Framing citations: RL foundations (Sutton & Barto, 2018), Q-learning (Watkins & Dayan, 1992), DQN (Mnih et al., 2015), A* (Hart et al., 1968), MARL survey (Busoniu et al., 2008), search (Russell & Norvig, 2021).
- Three governing principles to state: (1) from-scratch implementation (NumPy/Matplotlib; PyTorch only in Phase 3); (2) exhaustive frozen evaluation (600 scenarios, checksummed parameters); (3) reproducibility (fixed seeds).
- Roadmap paragraph: problem → methodology → results → conclusion.

# Problem Statement

[Phase 2, Phase 3, Phase 4 tasks + acceptance criteria]

- **P1 — Phase 2, Part 1:** 5 × 5 grid, 8 actions (incl. diagonals), item A random per episode, fixed B = (4, 4); state (ar, ac, ir, ic, carrying); rewards −1 move / −2 invalid / +10 pickup / +100 delivery. Acceptance: exhaustive 600-scenario (25 × 24) frozen-greedy evaluation.
- **P1 — Phase 2, Part 2:** two independent rovers (Type A U-payload destroyed in rain; Type B R-payload immune); lake flips dry/raining p = 0.5; LAPS = 4; 5 actions (incl. wait); rewards −5 / −3 / +10 / +50. Acceptance: 2,000-episode greedy eval + γ-sensitivity study (5 γ values).
- **P2 — Phase 3:** four agents deliver B → A → B ≤ 25 steps, zero head-on collisions preferred; budgets ≤ 1,500,000 steps / ≤ 4,000 collisions / ≤ 600 s walltime; complexity market: Sensors = 2, Central Clock = 1 (C = 3 purchased). Acceptance: exhaustive 600 scenarios.
- **P3 — Phase 4:** refactor `hbokmann/Pacman` skeleton into modular code (Direction enum, wall detection, ghost avoidance); automated demo with **no keyboard input**. Acceptance: all food collected, ghosts avoided across seeds, valid wall-free paths, unit tests pass.

# Methodology

[Design principles, algorithms, environments]

- Design principles: from-scratch; seeded reproducibility; frozen-parameter evaluation; exhaustive scenario coverage; separation of concerns (environment / learner / rendering).
- **Phase 2:** Q-tables `Q[5,5,5,5,2,8]` = 10,000 entries (Part 1), `Q[25,2,2,5]` = 500 per type (Part 2); unbiased ε-greedy with random tie-breaking (Part 2 decay 1.0 → 0.02 @ 0.9997); standard TD update with terminal handling; γ-study = 8,000 episodes × 5 values (0.85–0.995).
- **Phase 3:** one shared DQN for all four agents — `Linear(19→128) → ReLU → Linear(128→128) → ReLU → Linear(128→4)`; 19-dim obs = 7 default + 12 purchased sensor dims; round-robin Central Clock; correlated ε-greedy ("platooning") ε 0.08 → 0.01 over 220k steps; Huber TD loss, Adam lr 1e-3, γ 0.95, batch 512, target hard-sync 2,500 ticks, grad-clip 10, replay 200k; episode rule mirrors evaluation (start at B, early termination on all-delivered); guards: 1.45M-step cap, 510 s walltime.
- **Phase 4:** skeleton's 38 wall rectangles → 101 × 101 tile map @ 6 px → 19 × 19 cells (5 × 5 tiles each); doorway connectivity check (no wall clipping); dual graphs (Pac-Man: house+gate blocked; ghost: gate open); A* with heapq frontier `(f, g, node)`, closed set + best-g map (lazy deletion), Manhattan heuristic (admissible/consistent), `came_from` backtracking; ghost cells hard-blocked, ghost-adjacent cells +`GHOST_ADJACENT_PENALTY` = 50; re-plan triggers: dot eaten / next cell becomes ghost cell; greedy-nearest dot ordering (documented: not TSP-optimal); testing: 3 × 3 micro-grid first, then full maze (21 tests).

# Results & Discussion

[Phase 2 outcomes, Phase 3 DQN success, Phase 4 A* autopilot]

- **Phase 2, Part 1:** converges in seconds; full 600-scenario greedy evaluation with Q-table verified unchanged; learning curves (reward/steps moving averages) and learned paths plotted.
- **Phase 2, Part 2:** key finding — at short horizons (low γ) Type B *free-rides* through the dry lake and the rovers collide; longer horizons internalise the shared risk (independent-learner equilibrium failure, cf. Tan, 1993). Wait-cost asymmetry (−3 < −5) makes weather-aware waiting learnable.
- **Phase 3 (Table 1, seed 42):** steps 1,450,000 ≤ 1,500,000 ✓; head-on collisions 0 ≤ 4,000 ✓; walltime 416.1 s ≤ 600 s ✓; 49,834 episodes; 90,594 gradient steps; success 99.50% (597/600); avg steps to full delivery 6.65 (≈ the 6.4-tick Manhattan lower bound → near-shortest policies). Attribute zero collisions structurally: platooning + Central Clock + early termination.
- **Phase 4 (Table 2):** 349/349 dots, WON 12/12 seeds (540–745 ticks); single A* sub-millisecond (≤ 355 walkable cells); full run ~0.1–0.5 s headless; ghost costs → graceful detours instead of freezes; documented limits: greedy dot ordering not TSP-optimal.
- Cross-phase discussion: tabular vs deep (state-space scaling); shared network as implicit coordination channel (mitigates non-stationarity); cost-bounded engineering (C = 3; skeleton geometry reused as source of truth); search vs learning regimes (known map vs unknown/stochastic dynamics).

# Conclusion

[Summary + limitations + future work]

- Summary: three validated deliverables — (a) tabular Q-learning with exhaustive frozen eval + γ-study; (b) four-agent shared DQN at 99.50% success, zero collisions, inside all budgets; (c) modular A* Pac-Man autopilot, all dots, 12/12 seeds, 21 tests.
- Limitations: independent tabular learners non-stationary by construction; platooning trades exploration diversity for safety; greedy dot ordering; pygame optional (no Python 3.14 wheel) — absorbed by decoupled renderers.
- Future work: joint-action critics; TSP dot ordering; learned ghost prediction replacing static adjacency penalties; policy-gradient methods.

# References

[APA 7 formatted references]

- Alphabetical order; hanging indent (approximated by bullets in Markdown).
- Core list: Bellman (1957); Bokmann (n.d., Pacman skeleton); Busoniu et al. (2008); Dijkstra (1959); Harris et al. (2020, NumPy); Hart et al. (1968, A*); Huber (1964); Hunter (2007, Matplotlib); Mnih et al. (2013, 2015); Pac-Man A* tutorial video (n.d.); Paszke et al. (2019, PyTorch); Russell & Norvig (2021); Shinners (n.d., pygame); Sutton & Barto (2018); Tan (1993); Watkins & Dayan (1992).
- Rule: every entry must be cited in-text at least once (see Citations).

# Citations

[In-text citation map]

- APA 7 requires in-text citations at each point of use.
- Build a two-column map: source → sections citing it (e.g., Watkins & Dayan, 1992 → Introduction; Methodology/Phase 2).
- Check: no orphan references, no uncited claims of prior work.

# Appendices

[Hyperparameters, reward tables, pseudocode]

- **Appendix A (Phase 2, Part 1):** reward table; Q-table shape; 600-scenario evaluation protocol.
- **Appendix B (Phase 2, Part 2):** reward table (additive stacking); lake dynamics; ε schedule; γ-sensitivity design + qualitative findings.
- **Appendix C (Phase 3):** purchased-options cost table (Sensors 2 / Clock 1 / C = 3); hyperparameter table (seed 42); measured-results table.
- **Appendix D (Phase 4):** module map (`directions.py`, `maze.py`, `astar.py`, `entities.py`, `game.py`, `renderers.py`, `run_demo.py`, `test_astar.py`); constants (6 px walls / 30 px cells / 19 × 19 grid / penalty 50 / 349 dots); A* pseudocode; 21-test matrix.
- **Appendix E:** repository map + per-phase reproduction commands (`Run All` notebooks; `python phase-4/run_demo.py` → WIN 349/349; `python phase-4/test_astar.py` → 21/21).

