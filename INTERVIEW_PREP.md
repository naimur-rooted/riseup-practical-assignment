# Interview Prep — RL Q&A from My Actual Code

**RiseUp practical assignment** · every answer below is backed by a real snippet from this
repo, with the file + function it lives in, so you can open the code and show the interviewer
*exactly* which portion answers the question.

| Where things live | File |
|---|---|
| Part 1 — single-agent tabular Q-learning | `phase-2/part-1/tabular_q_learning_single_agent.ipynb` |
| Part 2 — 2-rover tabular coordination (lake) | `phase-2/part-2/tabular_q_learning_multi_agent.ipynb` |
| Part 3 — 4-rover DQN (⚠ also duplicated in `phase-3/`) | `phase-2/part-3/multi_agent_dqn.ipynb` |
| Phase 4 — A\* Pac-Man | `phase-4/astar.py`, `phase-4/directions.py` |

---

## A. Reinforcement Learning — Explain Like I'm 5

### A1. What is reinforcement learning? (ELI5)

A robot tries things. Good moves earn **stickers** (rewards), bad moves earn **frowns**
(penalties), and the robot slowly figures out which actions earn the most stickers — nobody
ever tells it the right answer, it learns from the *consequences* of its own actions.

**In my code:** the rover gets `+10` for picking up item A, `+100` for delivering it to B,
`-1` for every step and `-2` for bumping a wall. From those numbers alone it learned a
100 %-success route in 19 000 practice runs — no labelled examples anywhere.

```python
# part-1 · GridWorld class constants — the entire "sticker system"
MOVE_REWARD = -1.0      # every step costs -> shortest path emerges
INVALID_REWARD = -2.0   # bumping a wall costs extra -> don't
PICKUP_REWARD = 10.0    # step on A -> sticker
DELIVERY_REWARD = 100.0 # reach B carrying A -> big sticker, episode over
```

### A2. Agent, environment, state, action, reward (one line each, rover task)

| Concept | One-liner (rover task) | Where in code |
|---|---|---|
| **Agent** | The decision-maker: the rover that moves around the grid. | `QLearningAgent` (part-1) |
| **Environment** | Everything the agent can't control: the 5×5 grid + rules that answer each move. | `GridWorld` (part-1) |
| **State** | The situation the agent sees right now. | `(agent_r, agent_c, item_r, item_c, carrying)` |
| **Action** | One choice the agent can make: one of the 8 moves. | `GridWorld.ACTIONS` |
| **Reward** | A number the environment returns after each action telling it how good that was. | `MOVE_REWARD … DELIVERY_REWARD` |

```python
# part-1 · GridWorld.get_state() — the state is a hashable Markov tuple
def get_state(self):
    return (self.agent_pos[0], self.agent_pos[1],   # where am I
            self.item_pos[0], self.item_pos[1],     # where is A
            int(self.carrying))                     # am I holding it?
```

### A3. What is an episode? When does it end in Part 1? In Phase 3 (Part 3)?

**Episode** = one complete run of the environment, from `reset()` until termination —
one full pickup-and-deliver job. It is the unit of training: all learning happens on the
transitions collected during episodes.

- **Part 1 ends** when the agent **delivers A to B** (`done = True` on the delivery step) —
  **or** at the hard cap `MAX_STEPS = 60` (a truncated failure).
- **Part 3** (the 4-rover DQN; the same notebook is duplicated in `phase-3/`) **ends** as soon
  as **all 4 rovers complete their shuttle** (B → A pickup → B drop-off) — it terminates
  *early* on purpose so agents never wander after finishing. In evaluation a scenario not
  finished within the **25-step** budget is a failure.

```python
# part-1 · train_q_learning() — episode ends on done or step budget
for step in range(max_steps):          # max_steps = 60
    action = agent.choose_action(state)
    next_state, reward, done = env.step(action)
    agent.update(state, action, reward, next_state, done)
    state = next_state
    if done:                           # delivery fired -> episode over
        break
```

```python
# part-3 · train() — early termination once every rover has delivered
if all(w.deliveries[i] >= 1 for i in range(N_AGENTS)):
    break                              # all 4 delivered -> episode over
```

### A4. What is a policy (π)? How is it different from the Q-table?

- **Policy π** is the *behaviour*: a mapping **state → action** ("what do I do now?").
- **Q-table** is the *knowledge*: a mapping **(state, action) → expected return**
  ("how good is doing that?").

They are different objects, but the Q-table *induces* the policy via
**π(s) = argmaxₐ Q(s, a)** — my policy is literally defined this way, with random
tie-breaking so it's unbiased:

```python
# part-1 · QLearningAgent._best_action() — the policy, derived from the Q-table
def _best_action(self, q_row):
    """Argmax with uniform random tie-breaking."""
    best = float(np.max(q_row))
    tied = np.flatnonzero(np.isclose(q_row, best))
    return int(self.rng.choice(tied))   # π(s) = argmax_a Q(s,a), unbiased
```

### A5. Why does the agent need to *explore* if it already has a Q-table?

Because the Q-table starts as **all zeros — it knows nothing**. If the agent only ever took
the currently-best-looking action, the first route it stumbled onto would look best forever
and it would never discover that a different action leads to `+100`. Exploration buys
*information*: try sometimes-random actions, observe the rewards, correct the estimates.
Once estimates are good, exploration is dialled down (ε-decay) so the agent *exploits*.

```python
# part-1 · QLearningAgent.choose_action() — ε-greedy: explore with prob ε
def choose_action(self, state, greedy=False):
    idx = self._idx(state)
    q_row = self.q_table[idx]
    if not greedy and self.rng.random() < self.epsilon:   # EXPLORE
        return int(self.rng.integers(0, self.q_table.shape[-1]))
    return self._best_action(q_row)                       # EXPLOIT
```

---

## B. Sensors and Observation Space

### B1. What "sensors" does each agent in Part 2 have?

Exactly four numbers: **own cell** `(row, col)`, its **carrying bit**, and the **single shared
lake bit** — dry `0` / raining `1`. **It does NOT see the other rover.** The lake bit is the
only channel through which the rovers coordinate (besides bumping into each other in the lake).

```python
# part-2 · RoverWorld._observe() — the entire sensor suite: 4 numbers
def _observe(self, kind):
    r, c = self.pos[kind]
    return (r, c, int(self.carry[kind]), int(self.lake))
    #          ↑ own cell    ↑ carrying    ↑ lake state (shared)
```

### B2. What does each agent in Phase 3 observe *by default*?

A **7-dim** vector: own `(r, c)` (normalised), **delta to A**, **delta to B**, and its
**carrying flag**. The *default* observation also does **not** include other agents — seeing
neighbours is exactly what the purchased Sensors option adds (B3).

```python
# part-3 · ShuttleWorld.observe() — the 7 default dims come first
f = [r / (N - 1), c / (N - 1),        # own position
     (ar - r) / 4.0, (ac - c) / 4.0,  # delta to A
     (br - r) / 4.0, (bc - c) / 4.0,  # delta to B
     float(self.carrying[i])]         # carrying flag
```

### B3. What extra sensors can you buy in Phase 3's Cost Table, and what does each cost?

| Purchased option | Cost | What it gives |
|---|---|---|
| **Sensors** | **2** | +12 dims: for each of N/E/S/W — *wall flag*, *any-agent flag*, *opposite-stream-agent flag* |
| **Central Clock** | **1** | Agents act sequentially in round-robin order each tick (`0,1,2,3`) instead of simultaneously |
| **Total complexity cost** | **C = 3** | vs. performance points B = 4 → scaling factor α = 1.000 |

```python
# part-3 · dimension accounting
BASE_DIM = 7            # default observation space
SENSORS_DIM = 4 * 3     # purchased sensors: 4 dirs x (wall, agent, opposite)
OBS_DIM = BASE_DIM + SENSORS_DIM   # 19 -> the DQN input size
```

```python
# part-3 · ShuttleWorld.step() — Central Clock: round-robin acting order
for i in range(N_AGENTS):        # 0, 1, 2, 3, tick by tick
    ...                          # agent i moves, then agent i+1
```

### B4. Why is the observation space the single most important design choice in RL?

**If the agent cannot see it, it cannot learn it.** The observation defines what is even
*distinguishable*; anything left out is invisible no matter how long you train or how you
shape rewards. In Part 2, putting the **lake bit** in the observation is precisely why the
rovers could learn "Type A crosses only dry / Type B only flooded" — without that one bit,
dry and raining worlds would alias and the timing behaviour would be unlearnable. Likewise in
Part 3, collision avoidance is only learnable *after buying Sensors* (seeing neighbouring
agents), because the default 7-dim obs cannot tell "cell next door occupied" from empty.

### B5. If two states *look identical* to the agent but require different actions, what is that called?

**Partial observability**, and the resulting confusion is **perceptual aliasing** — two
genuinely different situations collapse to the same observation, so no single action can be
right for both. Without Part 2's lake bit, "lake dry" and "lake raining" would alias while
the correct action (cross vs wait) differs — the task would be unsolvable. My Part-2 state
tuple includes the lake bit precisely to remove that aliasing.

---

## C. Actions, Exploration, Epsilon (ε)

### C1. How many actions does each phase have, and what are they?

| Phase | # actions | Set |
|---|---|---|
| Part 1 | 8 | N, S, E, W, NE, NW, SE, SW (diagonals allowed) |
| Part 2 | 5 | N, S, E, W, **wait** |
| Part 3 | 4 | N, S, E, W (**no wait** — the Cost Table forbids it) |

```python
# part-1 · GridWorld.ACTIONS — 8 movement vectors
ACTIONS = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1),
           "up_left": (-1, -1), "up_right": (-1, 1),
           "down_left": (1, -1), "down_right": (1, 1)}
```

```python
# part-2 · RoverWorld.ACTIONS — 4 moves + wait
ACTIONS = {"north": (-1, 0), "south": (1, 0),
           "east": (0, 1), "west": (0, -1), "wait": (0, 0)}
```

```python
# part-3 · Direction Enum — strictly 4, no wait
class Direction(Enum):
    NORTH = 0
    SOUTH = 1
    EAST = 2
    WEST = 3
```

### C2. What is ε-greedy?

With probability **ε** pick a **random** action (explore); otherwise pick
**`argmaxₐ Q(s, a)`** (exploit). It's the standard compromise between gathering information
and using it. My tie-breaking is random so the very first steps (all-zero Q) don't bias the agent:

```python
# part-1 · QLearningAgent.choose_action()
if not greedy and self.rng.random() < self.epsilon:      # with prob ε
    return int(self.rng.integers(0, self.q_table.shape[-1]))  # random act
return self._best_action(q_row)                          # else argmax Q
```

### C3. What is epsilon decay and why do we use it?

Start ε **high** (≈1.0 — explore everything), then shrink it gradually so the agent
eventually **exploits** what it learned. My schedules:

```python
# part-1 · config: multiplicative decay, floored
EPSILON_START, EPSILON_MIN, EPSILON_DECAY = 1.0, 0.05, 0.9995

def decay_epsilon(self):   # part-1 · QLearningAgent
    self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
```

```python
# part-3 · linear decay over 220k agent-steps: 0.08 -> 0.01
eps = max(EPS1, EPS0 - (EPS0 - EPS1) * steps / EPS_DECAY)
```

Part 2 uses `1.0 → 0.02` (× 0.9997 per episode). The **floor** (`ε_min`) matters: a little
lifelong exploration keeps the agent adaptable and Q-values honest.

### C4. What happens if ε stays at 1.0 forever? At 0.0 from the start?

- **ε = 1.0 forever:** behaviour is a random walk. Q-learning is *off-policy* so the Q-values
  still update, but the agent never *acts* on them — measured success stays at chance level
  and it can never demonstrate the learned policy. Endless re-exploration also keeps
  perturbing states it already mastered.
- **ε = 0.0 from the start:** pure exploitation of an all-zero table — the agent just follows
  arbitrary tie-breaks, never deliberately tries untested actions, most likely never finds
  the `+100` delivery, and never gets the data to fix its mistakes. Classic
  **exploration–exploitation trade-off**: you need both, sequenced correctly.

### C5. Difference between *on-policy* and *off-policy* learning?

- **Off-policy** (Q-learning): the *target* policy being learned (greedy) can be different
  from the *behaviour* policy used to act (ε-greedy). You learn "what is best" while
  sometimes wandering.
- **On-policy** (SARSA): you evaluate and improve the *same* policy you are behaving with,
  including its exploration — the target uses the action actually taken next,
  `Q(s', a_taken)`, not the max.

```python
# part-1 · QLearningAgent.update() — the max makes it OFF-policy:
td_target = reward + self.gamma * float(np.max(self.q_table[self._idx(next_state)]))
#                                    ^^^^^^ best imaginable next action,
#                                    NOT the (possibly random) one actually taken
```

---

## D. Discount Factor (γ) and Returns

### D1. What is the discount factor γ?

A number in **[0, 1)** saying how much the agent cares about future rewards vs immediate ones.
`γ = 0` → only the next reward matters (short-sighted). `γ → 1` → far-future rewards count
almost as much (far-sighted). My values: **0.95** (Part 1), **0.995** (Part 2 — tuned by a
sensitivity study, see D5), **0.95** (Part 3 DQN).

### D2. Formula for the discounted return Gₜ

```
Gₜ = r_{t+1} + γ·r_{t+2} + γ²·r_{t+3} + …  =  Σ_{k=0..∞} γᵏ · r_{t+k+1}
```

### D3. Why must γ < 1 in continuing tasks?

Because the return is an **infinite geometric series** — with `γ ≥ 1` and non-zero rewards it
**diverges** (the agent would chase an infinite total), so values can't be compared. γ < 1
guarantees convergence: `Σ γᵏ = 1/(1−γ)`, a finite bound.

### D4. What is the Bellman optimality equation?

```
Q*(s, a) = E[ r + γ · max_{a'} Q*(s', a') ]
```

"The true value of (s, a) is the immediate reward plus the discounted value of acting
optimally in the next state." Q-learning is a *sampled, incremental* solution of exactly this
equation — see F1.

### D5. In Part 2, why are results *very sensitive* to γ?

The core decision is **timing**: "wait now (−3, safe)" vs "cross the lake now (risk −20 water
damage / collision, but +50 sooner)". That trade lives *entirely in γ*:

- **γ too low (0.85–0.90):** the −3 wait bleeds the return faster than the future +50 can
  repay → rovers become short-sighted, dash into the lake, Type B free-rides dry crossings,
  collisions happen.
- **γ too high / badly paired with episode length:** patience is cheap but the agent can
  over-wait, dragging out episodes.

I didn't guess — I ran a **γ-sensitivity study** (8 000 episodes × 5 γ values) and picked
**γ = 0.995**, the only setting with 100 % collision-free + 100 % water-free coordination:

```python
# part-2 · quick_study() — train + evaluate for each gamma
GAMMA_VALUES = [0.85, 0.90, 0.95, 0.99, 0.995]
gamma_rows = quick_study(GAMMA_VALUES, episodes=8_000, laps=4,
                         max_steps=150, eval_episodes=200)
```

The waiting option only exists because `wait` costs **−3 < −5 move** — the env allows
patience, γ decides whether the agent values saving it for later.

---

## E. NumPy / np.array and Dimensions

### E1. What is `np.array` and how is it different from a Python list?

| | Python `list` | `np.array` |
|---|---|---|
| Size | grows/shrinks | **fixed** once created |
| Contents | mixed types | **single dtype** |
| Memory | pointers to objects | **contiguous** raw buffer |
| Math | manual loops | **vectorised** C-speed (`Q += …`) |

My Q-updates would be ~100× slower in pure Python — `self.q_table[idx][action] += …` is one
vectorised C-level op on a contiguous block.

### E2. What does the *shape* of an array mean?

A tuple `(d₀, d₁, …)` giving the length along each axis. `(5, 5, 2, 8)` = 4-D array with
5 rows, 5 cols, 2 carry-states, 8 actions.

### E3. What shape is the Q-table in Part 1?

State = `(agent_r, agent_c, item_r, item_c, carrying)` + 8 actions →

```
Q.shape == (n, n, n, n, 2, 8)   ->  for n=5: 5⁴ · 2 · 8 = 10 000 cells
```

```python
# part-1 · QLearningAgent.__init__() — the Q-table, one axis per state variable
self.q_table = np.zeros((n, n, n, n, 2, len(GridWorld.ACTION_NAMES)))
# notebook prints: Q-table shape : (5, 5, 5, 5, 2, 8)
```

Indexing is a *direct address*: `Q[ar, ac, ir, ic, carrying]` returns the 8-action row.

### E4. What shape is the Q-table in Part 2 (per agent type)?

`(row, col, carrying, lake_bit, action)` → `(5, 5, 2, 2, 5)` = **500 entries** per rover type.
The extra `lake_bit` axis is what lets the policy *condition on the weather*:

```python
# part-2 · TabularQAgent.__init__()
self.q = np.zeros((GRID, GRID, 2, 2, RoverWorld.N_ACTIONS))  # 5·5·2·2·5 = 500
```

### E5. Difference between `arr.shape`, `arr.ndim`, `arr.size`, `arr.dtype`?

| Attribute | Meaning | Part-1 Q-table |
|---|---|---|
| `shape` | tuple of axis lengths | `(5, 5, 5, 5, 2, 8)` |
| `ndim` | number of axes | `6` |
| `size` | total element count | `10 000` |
| `dtype` | element type | `float64` |

Invariant: `size == prod(shape)`; `ndim == len(shape)`.

### E6. What does `np.argmax(Q[s])` return, and what shape must `Q[s]` be?

It returns the **integer index of the highest-valued action** — the greedy action.
`Q[s]` must be the **1-D action row** for that state, shape `(8,)` (part 1) or `(5,)`
(part 2). `np.argmax` returns the *first* max on ties, which is why I replaced it with
random tie-breaking (`_best_action` — A4) so exploration isn't biased toward "up" early on.

### E7. Why `np.random.default_rng(seed)` instead of `random.random()` for reproducibility?

Two reasons: (1) **one seed must pin every randomness source** — Python's `random`, NumPy's
legacy global, and PyTorch each keep *independent* streams; seeding one leaves the others
nondeterministic. (2) `default_rng` gives each component its **own isolated Generator**
(PCG64), so the env's dice can't shift the agent's dice and every run replays exactly.

```python
# every module creates its own seeded generator — no shared globals
self.rng = np.random.default_rng(seed)      # GridWorld, QLearningAgent, part-2, part-3
rng = np.random.default_rng(seed)           # train loops
torch.manual_seed(seed)                     # part-3 · DQNAgent — torch is a separate stream
```

Plus `SEED = 42` printed in each notebook's config cell — results are bit-reproducible.

---

## F. Q-Learning Update — Walk Through It

### F1. The Q-learning update rule (from memory — verbatim from my code)

```
Q(s,a) ← Q(s,a) + α · [ r + γ · max_{a'} Q(s', a') − Q(s,a) ]
```

```python
# part-1 · QLearningAgent.update() — the whole algorithm in 7 lines
def update(self, state, action, reward, next_state, done):
    idx = self._idx(state)
    current_q = self.q_table[idx][action]
    if done:
        td_target = reward                      # terminal: no bootstrapping
    else:
        td_target = reward + self.gamma * float(np.max(self.q_table[self._idx(next_state)]))
    self.q_table[idx][action] = current_q + self.alpha * (td_target - current_q)
```

### F2. What is α (alpha)?

The **learning rate** — how strongly each new experience overwrites the old estimate:
`new ← old + α·(target − old)`. α = 0.3 (part 1), 0.2 (part 2). Small α = stable but slow;
large α = fast but jumpy.

### F3. What is the *TD error*?

The surprise: **how much reality disagreed with your prediction**.

```
δ = r + γ · max_{a'} Q(s', a') − Q(s, a)
```

In code it's exactly `(td_target - current_q)` in F1; the update nudges Q by α·δ.

### F4. What happens if α = 1? If α = 0?

- **α = 1:** every new sample *completely replaces* the old value — no averaging, so in
  stochastic environments Q-values ping-pong with the last reward (unstable). (Nuance worth
  mentioning: in a fully *deterministic* env like Part 1, α = 1 actually converges fine.)
- **α = 0:** `Q ← Q + 0·δ` — **nothing is ever learned**.

### F5. For a terminal state, what does the update simplify to?

Drop the bootstrap — there is no future after terminal:

```
Q(s, a) ← Q(s, a) + α · [ r − Q(s, a) ]      # td_target = reward
```

```python
if done:
    td_target = reward        # part-1 · update() — no γ·max term
```

The `+100` delivery then propagates backwards one step per episode visit — that's why
value *spreads* over training rather than appearing instantly.

---

## G. DQN (Phase 3 / Part 3 only)

### G1. Why DQN instead of a Q-table in Part 3?

**Scale + generalisation.** The tabular trick (one cell per state) died twice: the 19-dim
observation (own pos + deltas + carrying + 12 sensor dims) can't be enumerated as discrete
axes like Part 1's tuple, four agents multiply the joint space, and the normalised floats
(deltas, sensor flags) have effectively uncountable values. A neural net
`Linear(19→128) → ReLU → Linear(128→128) → ReLU → Linear(128→4)` **approximates** Q(s, a)
and generalises across similar states — one shared network serves all 4 agents (explicitly
allowed), so each of the 4 experiences per tick trains the same weights.

```python
# part-3 · QNet — the function approximator replacing a 10^k-cell table
self.net = nn.Sequential(
    nn.Linear(obs_dim, hidden), nn.ReLU(),     # obs_dim = 19
    nn.Linear(hidden, hidden), nn.ReLU(),
    nn.Linear(hidden, n_actions),              # n_actions = 4
)
```

### G2. What is a replay buffer and why do we need it?

A big circular memory of past transitions `(o, a, r, o', done)`; training samples a random
batch (512) instead of learning on the *latest* transitions only. Two wins: it **breaks the
temporal correlation** between consecutive samples (consecutive steps are near-identical —
SGD on correlated data destabilises), and it **reuses** each experience many times
(sample-efficiency).

```python
# part-3 · ReplayBuffer — circular, NumPy-backed, O(1) push
def push(self, o, a, r, o2, d):
    k = self.i % self.cap                       # wrap around (cap = 200 000)
    self.o[k], self.a[k], self.r[k], self.o2[k], self.d[k] = o, a, r, o2, d

def sample(self, bs, rng):                      # uniform random batch
    idx = rng.integers(0, self.n, size=bs)
    return self.o[idx], self.a[idx], self.r[idx], self.o2[idx], self.d[idx]
```

### G3. What is the target network and why separate from the online network?

The TD target contains `max Q(s', a')` — if the *same* network computes both the prediction
and the target, every gradient step moves the goalpost (chasing a moving target →
oscillation). So a **frozen copy** (`self.tgt`) provides the target and is hard-synced from
the online net only every **2 500 ticks**:

```python
# part-3 · DQNAgent.__init__ — two nets, same init
self.q   = QNet(obs_dim, n_actions)             # online (learns)
self.tgt = QNet(obs_dim, n_actions)             # target (frozen)
self.tgt.load_state_dict(self.q.state_dict())

# part-3 · sync_target(), called every TARGET_SYNC_TICKS = 2500 env ticks
def sync_target(self):
    self.tgt.load_state_dict(self.q.state_dict())
```

### G4. What loss function does DQN minimise?

The squared TD error in theory:
`L = ( r + γ · max_{a'} Q_target(s', a') − Q_online(s, a) )²`.
My implementation uses **Huber loss** (`smooth_l1_loss`) — quadratic near zero like MSE but
*linear* for large errors, so one outlier reward (e.g. a rare −25 collision) can't blow up
the gradient:

```python
# part-3 · DQNAgent.train_step() — the entire DQN learning step
q_sa = self.q(o_t).gather(1, a_t).squeeze(1)            # Q_online(s, a)
with torch.no_grad():                                    # target: no gradient
    y = r_t + GAMMA * (1.0 - d_t) * self.tgt(o2_t).max(1).values
loss = nn.functional.smooth_l1_loss(q_sa, y)             # Huber TD loss
self.opt.zero_grad(); loss.backward()
nn.utils.clip_grad_norm_(self.q.parameters(), GRAD_CLIP) # clip 10
self.opt.step()                                          # Adam, lr 1e-3
```

(Also visible: `1.0 − d` zeroes the bootstrap on terminal transitions — the DQN version of F5.)

### G5. Why is `wait` *not* an action in Part 3?

The assignment's **Cost Table defines the action set as the 4 cardinal directions** —
`Direction(Enum): NORTH/SOUTH/EAST/WEST` — so standing still isn't purchasable. Design
consequence: coordination (avoiding head-on collisions, taking turns) must emerge from
**movement timing + observation**, not from pausing. It also pushes complexity budget toward
what actually earns points (Sensors +2, Central Clock +1 → C = 3, α = 1.000).

```python
# part-3 · the complete action space — no WAIT member exists
class Direction(Enum):
    NORTH = 0; SOUTH = 1; EAST = 2; WEST = 3
```

---

## H. A* (Phase 4 — Pac-Man)

*File: `phase-4/astar.py` (+ `phase-4/directions.py`). Bonus context: my A* adds
**ghost avoidance** — cells with ghosts are blocked, cells *adjacent* to a ghost carry a
big step penalty, so Pac-Man routes away from danger.*

### H1. `f(n) = g(n) + h(n)` — define each term

- **g(n)** — *actual* cost paid from `start` to `n` (code: `tentative_g = cur_g + step_cost`).
- **h(n)** — *estimated* cost from `n` to `goal` (code: `h = manhattan(nxt, goal)`).
- **f(n)** — best guess of total path cost through `n`; the priority queue pops smallest `f`.

```python
# phase-4/astar.py · a_star() — push with f = g + h
g_score[nxt] = tentative_g
came_from[nxt] = current
h = manhattan(nxt, goal)
heapq.heappush(frontier, (tentative_g + h, tentative_g, nxt))   # (f, g, cell)
```

### H2. What makes a heuristic *admissible*? Why does A* need it?

**Admissible = never overestimates** the true remaining cost: `h(n) ≤ h*(n)`. Then `f` is
always an optimistic lower bound, so the first time A* pops the goal it really is on a
cheapest path — the pop order guarantees **optimality**. If h overestimates anywhere, a
truly shorter path can sit in the frontier behind an inflated f and A* returns a
suboptimal route. (Stronger property: *consistent* — `h(n) ≤ cost(n,n') + h(n')` — which
Manhattan is on a unit grid; it guarantees each node expands at most once.)

### H3. Why is Manhattan distance the right heuristic in Pac-Man?

Movement is **4-directional with unit step cost** — every step changes Manhattan distance by
exactly 1, so in an empty grid Manhattan *equals* the true remaining cost, and with walls
it's a strict lower bound. Lower bound ⇒ admissible ⇒ optimal; near-equality in open space ⇒
*tight* ⇒ few expansions. Euclidean would be inadmissible (the diagonal shortcut is shorter
than any legal path); h = 0 degenerates A* into Dijkstra.

```python
# phase-4/directions.py · manhattan()
def manhattan(a, b) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])
```

### H4. What data structure holds the open set, and why?

A **min-heap / priority queue** (`heapq`) keyed on `f`. The whole point of A* is "expand the
most promising node first" — that's exactly `heappop` in O(log n). A list needs an O(n) scan
per expansion; a FIFO queue can't order by f at all (that's BFS).

```python
# phase-4/astar.py · frontier is a heap of (f, g, cell) tuples
frontier = [(start_h, 0, start)]          # g as tie-breaker: cheaper path wins ties
_f, _g, current = heapq.heappop(frontier)
```

### H5. How do you avoid re-expanding nodes?

A **closed set** + a **`g_score` map**, with *lazy deletion*: stale heap entries aren't
removed on update, they're simply skipped when popped.

```python
# phase-4/astar.py · the two guards
if current in closed:
    continue                            # already expanded at its cheapest g
...
if nxt in g_score and tentative_g >= g_score[nxt]:
    continue                            # a cheaper route to nxt is already known
```

Subtlety I can defend: my step costs are **non-uniform** (ghost-adjacent penalty), so a
later-discovered *lower-g* route to a visited node can still be better — that's why the
`g_score` relaxation check, not a naive `if nxt in closed: skip`, is the correct guard.

---

## I. Engineering Sanity Checks

### I1. What random seed did you use, and why is it set for *every* RNG source?

**`SEED = 42`**, everywhere. The principle: reproducibility requires pinning **every
independent randomness stream** — NumPy's Generator, and PyTorch's weights/init and shuffling
each maintain separate state; seeding one leaves the others nondeterministic, so "same code,
same result" would silently break. My design gives **each component its own seeded generator**
rather than one global — so the env's dice can't shift the agent's dice, and a change in one
component can't silently perturb another:

```python
# part-1 · config cell — printed at the top of every run
SEED = 42
...
# every component gets its own isolated Generator (PCG64):
self.rng = np.random.default_rng(seed)     # GridWorld / QLearningAgent / TabularQAgent
rng = np.random.default_rng(seed)          # train_q_learning() / train() (part-3)
torch.manual_seed(seed)                    # part-3 · DQNAgent — torch is a separate stream
```

Evidence it works: every README result table says *"generated by running the notebook,
seed 42"* — anyone can re-run and reproduce the exact numbers (e.g. Part 1: 100 %, avg 5.38
steps; Part 3: 49 834 episodes, 99.50 %).

### I2. Show me where you log episode reward / collision count. Plot it.

Part 1 logs three parallel per-episode lists inside the training loop and smooths them with a
moving average for plotting; Part 3 appends `(return, collisions)` per episode and plots the
reward curve plus the **cumulative** collision line (flat = good).

```python
# part-1 · train_q_learning() — the logging lines
episode_rewards.append(total_reward)       # sum of rewards this episode
episode_steps.append(step + 1 if done else max_steps)
episode_success.append(done)               # did it deliver?

# part-1 · moving_average() + matplotlib — "Plot 1/2: rewards & steps"
mv_reward = moving_average(episode_rewards, MOVING_AVG_WINDOW)   # window 200
ax.plot(mv_reward)
```

```python
# part-3 · train() meters + "Training curves (seed 42)" plot
hist.append((er, em))                      # (episode return, head-on collisions)
ax[0].plot(hist[:, 0])                     # episode return
ax[1].plot(np.cumsum(hist[:, 1]))          # cumulative collisions — flat line = 0 new
```

### I3. Agent plateaus at a bad policy — name 5 things you would try

1. **Tune γ** — wrong horizon is the classic plateau (my Part-2 γ-study exists precisely
   because 0.85–0.95 plateaued at a colliding policy).
2. **Fix exploration** — raise the ε floor / slow the decay / re-heat ε when progress stalls
   (the agent may have explored itself into a corner too early).
3. **Check observation completeness** — is a *needed* variable aliased away? (lake bit,
   neighbour flags); "if it can't see it, it can't learn it" (B4).
4. **Reshape rewards** — too sparse (only +100 at the end) → add small shaping that doesn't
   change the optimum (my −1/step makes shortest-path the incentive); also check
   punishment/cliff magnitudes aren't drowning the signal.
5. **More data / better optimisation** — more episodes, higher α (or LR schedule), larger
   replay batch, faster target sync (DQN), and verify against a different seed to rule out
   seed luck.

### I4. Walk me through one full training step in your code — line by line

One step of Part 1 (`train_q_learning` → `choose_action` → `env.step` → `update`):

```python
action = agent.choose_action(state)
#   ε-greedy: with prob ε -> random action index; else argmax of the 8-value Q-row
next_state, reward, done = env.step(action)
#   env applies the move: wall -> (-2, same cell, done=False)
#   move -> (-1, new cell); entering A while empty -> +10, carrying=1
#   entering B while carrying -> +100, done=True
agent.update(state, action, reward, next_state, done)
#   td_target = reward + γ·max Q(next_state)   (or just reward if done)
#   Q[state][action] += α · (td_target − Q[state][action])      <- the F1 rule
state = next_state
#   the Markov chain advances; the episode repeats until done or MAX_STEPS=60
```

At episode end (not per step): `agent.decay_epsilon()` — ε ×= 0.9995, floored at 0.05 — and
`(total_reward, steps, success)` are appended to the logs (I2). Part 3's equivalent step is
the same loop plus: push all 4 transitions to the replay buffer, every 4th tick run
`train_step()` (G4), every 2 500 ticks `sync_target()` (G3).

---

## Cheat Sheet — Hyperparameters I Can Quote

| | Part 1 | Part 2 | Part 3 (DQN) |
|---|---|---|---|
| Grid / agents | 5×5, 1 | 5×5, 2 | 5×5, 4 |
| Actions | 8 | 5 (+wait) | 4 (no wait) |
| Q representation | `(5,5,5,5,2,8)` = 10 000 | `(5,5,2,2,5)` = 500 | `QNet 19→128→128→4` |
| α / learning rate | 0.3 | 0.2 | Adam lr 1e-3 |
| γ | 0.95 | **0.995** (γ-study) | 0.95 |
| ε schedule | 1.0→0.05 (×0.9995) | 1.0→0.02 (×0.9997) | 0.08→0.01 linear / 220k steps |
| Episodes / budget | 19 000, MAX_STEPS 60 | 30 000, MAX_STEPS 150, LAPS 4 | 1.45 M agent-steps cap |
| Batch / buffer / sync | — | — | 512 / 200 000 / 2 500 ticks |
| Loss | — | — | Huber (`smooth_l1`), grad-clip 10 |
| Seed | 42 | 42 | 42 |
| Result | 100 %, ≤10 steps | 100 %, collision-free | 99.50 % in ≤25 steps, 0 collisions |









