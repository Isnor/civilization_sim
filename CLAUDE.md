# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

**civilization_sim** is an agent-based civilization simulation using Mesa. It explores how human cultures emerge from individual traits, social dynamics, and group behavior. The simulation models agents with 16 traits that drift over time, forming groups that develop social technologies (taboo, religion, philosophy, economy, governance) based on average trait profiles.

**Key question being explored:** Why do cultures diverge even when starting conditions are similar?

---

## Commands

### Running the Simulation

```bash
# Live dashboard (Solara web app)
solara run app.py

# CLI mode with default settings (300 ticks, 100 agents)
python main.py

# Custom configuration
python main.py --config config/my_experiment.yaml --output output/custom --seed 42

# Override number of ticks
python main.py --ticks 500

# Use alternative utility function
python main.py --utility enlightenment

# Quiet mode (no progress output)
python main.py --quiet
```

### Building/Testing

No formal test suite exists yet. The simulation is typically developed by:
1. Modifying config/default.yaml to experiment with trait distributions
2. Running `python main.py --ticks 100 --quiet` for quick iterations
3. Analyzing output CSVs in `output/<name>/`

### Output Files

Each run produces three CSVs in the output directory:

| File | Contents |
|---|---|
| `model_data.csv` | One row per tick: population, group count, average traits, social technology adoption rates, belief orientation fractions |
| `agent_data.csv` | One row per agent per tick: all 16 traits, resources, age, last action, metagame, belief orientation |
| `events.csv` | One row per Unknown Player event: tick, type, magnitude, resource effect |

---

## Code Architecture

### Directory Structure

```
civ_sim/
├── app.py                          # Solara web UI component
├── main.py                         # CLI entry point
├── config/
│   └── default.yaml                # Default scenario configuration
├── core/
│   ├── agent.py                   # Player (mesa.Agent) - atomic unit
│   ├── beliefs.py                 # BeliefSystem - agent's model of Unknown Player
│   ├── groups.py                  # Group/RelationshipState - emergent coalitions
│   ├── social_tech.py             # SocialTechnology registry & effects
│   └── traits.py                  # TraitVector, drift, inheritance
├── simulation/
│   ├── events.py                  # UnknownPlayerEvent generation & effects
│   ├── scenario.py                # CivilizationScenario (Mesa Scenario)
│   └── model.py                   # CivilizationModel (Mesa Model)
└── analysis/
    └── collectors.py               # Mesa DataCollector
```

### Key Classes and Modules

#### `core/traits.py`
- `TraitVector`: Dataclass holding 16 traits as floats in [0, 1]
- `random_traits()`: Sample traits from normal distributions
- `inherit_traits()`: Create offspring traits from two parents
- `drift_traits()`: Apply experience-based trait drift
- `spontaneous_inspiration()`: Rare mutations to base traits
- `TRAIT_NAMES`: 16 traits: curiosity, pattern_recognition, abstraction, memory_narrative, social_desire, dominance, empathy, trust, conformity, risk_tolerance, aggression, industriousness, patience, wonder, attribution_style, reverence

#### `core/agent.py`
- `Player`: Mesa Agent subclass representing a human
- Each tick: forage/rest/socialize/compete/contemplate → apply drift
- Social technologies apply multipliers to action weights via `_get_active_effects()`
- Metagame classification: "religion", "governance", "economy", "philosophy", "taboo"

#### `core/groups.py`
- `Group`: Emergent coalition with members, dominant voice, social technologies, latent sentiment
- `RelationshipState`: Trust/affinity tracking between two agents
- Group formation: `avg(social_desire) * relationship_strength > threshold`

#### `core/social_tech.py`
- `REGISTRY`: 5 social technologies with emergence conditions and effects
- `taboo`: empathy≥0.45, conformity≥0.45 → 50% in-group aggression reduction
- `religion`: wonder≥0.55, reverence≥0.55, attribution≥0.55, conformity≥0.5 → strong cohesion, curiosity suppression
- `philosophy`: curiosity≥0.60, abstraction≥0.55, pattern_recognition≥0.55 → triples inspiration rate
- `economy`: trust≥0.55, patience≥0.55, industriousness≥0.55 → 50% forage bonus
- `governance`: dominance≥0.55, social_desire≥0.60, conformity≥0.55 → coordinated action

#### `core/beliefs.py`
- `BeliefSystem`: Agent's model of Unknown Player
- Orientations: "attributor" (assigns intent), "modeler" (seeks patterns), "indifferent"
- Beliefs spread via `receive_belief()` weighted by trust and conformity

#### `simulation/scenario.py`
- `CivilizationScenario`: Holds all configurable parameters
- Trait distributions: `(mean, std_dev)` tuples for each trait
- End games: "max_population", "all_humans_dead", "max_ticks"

#### `simulation/model.py`
- `CivilizationModel`: Mesa Model that orchestrates the simulation
- Each `step()`:
  1. Generate Unknown Player event (maybe)
  2. Step all living agents
  3. Apply trait drift
  4. Spontaneous inspiration check
  5. Update group memberships
  6. Check social technology emergence
  7. Process reproduction
  8. Remove dead agents
  9. Collect data
  10. Check endgame conditions

#### `simulation/events.py`
- `UnknownPlayerEvent`: Drought/windfall/disease/etc. with random magnitude
- `maybe_generate_event()`: Creates event with probability from config
- `apply_event()`: Applies resource effects to agents
- `check_spontaneous_inspiration()`: Triggers trait mutations

### Configuration (config/default.yaml)

Mirrors `CivilizationScenario` fields. Key sections:
- `population`: initial size, max size, utility function ("survival" or "enlightenment")
- `resources`: costs, gains, reproduction thresholds
- `traits_*`: initial distributions for each trait as `[mean, std_dev]`
- `social_*`: encounter probability, group formation threshold, cooperation bonus
- `heritability_variance`: variance for offspring trait sampling
- `inspiration_probability`: probability of spontaneous trait mutation
- `unknown_player_event_probability`: probability of random event per tick
- `endgames_max_steps`: step limit for max_ticks endgame

### Utility Functions

Two modes via `population_utility_fn`:

**"survival" (default)**: Agents prioritize foraging, resting, competing to avoid starvation

**"enlightenment"**: Agents prioritize contemplation, socializing, curiosity-driven exploration
- Reduces foraging/competing weight by 40%/60%
- Increases contemplation weight by 150%
- Increases socializing weight by 30%

---

## Design Patterns and Conventions

### Agent Lifecycle

1. Spawn with `random_traits()` from config distributions
2. Each tick: pay survival cost → act → record experience → drift
3. Reproduction: consume resources → offspring inherits blended traits + noise
4. Death: starvation (resources ≤ 0) or age limit (80 ticks)

### Social Technology Emergence

Groups are checked each tick. When trait averages cross thresholds, technology activates:
- Norm broadcast to members (e.g., "taboo:no_in_group_killing")
- Effects apply as multipliers to action/resource functions
- Technologies stack multiplicatively

### The Unknown Player

Not an agent. A random event generator producing drought/windfall/disease/etc.
- Agents with wonder engage via `contemplate()` action
- High wonder + reverence → Attributors (form religion)
- High curiosity + modeler orientation → Philosophers (seek patterns)
- Beliefs about Unknown Player spread through social networks

### Trait Drift Model

Each agent has:
- `base_traits`: Heritable, stable (only via spontaneous inspiration)
- `current_traits`: Drifts toward/away from base based on experience

Drift formula: `current += experience_delta * rate`, bounded by `base ± max_deviation`

---

## Dependencies

```
mesa[rec]       # Mesa with recorder (data collection)
numpy           # Numerical operations
pandas          # DataFrame handling
pyyaml          # Config parsing
networkx        # Graph utilities
seaborn         # Plots for dashboard
```

Install: `pip install -r requirements.txt`

---

## Experiment Workflow

1. Copy config: `cp config/default.yaml config/aggressive.yaml`
2. Edit traits: e.g., `traits_aggression: [0.75, 0.15]`, `traits_empathy: [0.25, 0.15]`
3. Run: `python main.py --config config/aggressive.yaml --output output/aggressive --seed 42`
4. Compare: `python main.py --seed 42 --output output/baseline`

---

## Theoretical Foundations

Built on:
- Evolutionary game theory (Hawk-Dove dynamics)
- Tit-for-Tat cooperation principles (Axelrod)
- Nature-as-a-player (Harsanyi)
- Arrow's Impossibility Theorem (dominant voice model)
- Dunbar's Number (group size limits)
- Mesa ABM framework

---

## Future Improvements (Not yet implemented)

- Environmental differentiation (geography, climate)
- Inter-group conflict and absorption mechanics
- Non-human agents (deer, predators)
- Graph-based visualization for social networks
