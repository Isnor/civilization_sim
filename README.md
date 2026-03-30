# civilization_sim

A Python agent-based simulation exploring how human cultures emerge from individual traits, social dynamics, and group behavior.

This is a tool to try to help understand *why do cultures diverge even when starting conditions are similar?*

## AI Disclosure

I consulted the great Oracle when creating this, the irony of which is not lost on me. I did what I could to use and reference existing research and document all of the choices made, but all of it was recommended reading per the Great Giver of Knowledge, as was the decision to use agent-based modeling.

---

## Goals

Most civilization simulation games focus on combat and macro-level societal development. This one tries to focus on human culture: with individual humans who want to survive, find companionship, and make sense of a world they don't fully understand.

The goal is not to build the most accurate model of human history. It is to build a *flexible* model that reveals which variables are load-bearing - which traits, social technologies, or utility functions determine whether a culture flourishes, collapses, turns inward, turns violent, or reaches for something beyond survival.

Which trait combinations lead to religion, philosophy, or conquest? Can peaceful cultures survive? What happens if you change a single assumption about what humans are fundamentally trying to do? Run it with default settings. Change one parameter. Run it again. Compare.

---

## Setup

```bash
# Clone or download the project
cd civilization_sim

# Create a virtual environment (Python 3.10+ recommended)
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Usage

### Live Dashboard

[Solara](https://solara.dev/) is used to create a simple webapp to configure, run, and visualize different Civilization experiments. To run this project as a Solara app, run:

`solara run app.py`

### CLI

```bash
python main.py
```

Runs 300 ticks with 100 starting agents. Outputs CSV files to `output/default/`.

### Common options

```bash
# Specify number of ticks
python main.py --ticks 500

# Set a random seed for reproducibility
python main.py --seed 42

# Use the enlightenment utility function
python main.py --utility enlightenment --output output/enlightenment

# Point to a custom config
python main.py --config config/my_experiment.yaml

# Quiet mode (no progress output)
python main.py --quiet
```

### Experiment workflow

The recommended way to explore the simulation is to create config variants:

```bash
cp config/default.yaml config/aggressive.yaml
# Edit config/aggressive.yaml: set aggression mean to 0.75, empathy mean to 0.25
python main.py --config config/aggressive.yaml --output output/aggressive --seed 42

# Compare against baseline with same seed
python main.py --seed 42 --output output/baseline
```

### Output files

All runs produce three CSVs in the output directory:

| File | Contents |
|---|---|
| `model_data.csv` | One row per tick: population, group count, average traits, social technology adoption rates, belief orientation fractions |
| `agent_data.csv` | One row per agent per tick: all 16 traits, resources, age, last action, metagame, belief orientation |
| `events.csv` | One row per Unknown Player event: tick, type, magnitude, resource effect |

These are designed to be loaded into any analysis tool (pandas, R, Excel, a Jupyter notebook).

### Quick analysis example

```python
import pandas as pd
import matplotlib.pyplot as plt

m = pd.read_csv("output/default/model_data.csv", index_col=0)

fig, axes = plt.subplots(2, 2, figsize=(12, 8))

m["population"].plot(ax=axes[0,0], title="Population")
m[["tech_taboo","tech_religion","tech_economy","tech_governance","tech_philosophy"]].plot(
    ax=axes[0,1], title="Social Technology Adoption"
)
m[["attributors","modelers"]].plot(ax=axes[1,0], title="Belief Orientations")
m[["avg_aggression","avg_empathy","avg_trust"]].plot(ax=axes[1,1], title="Key Trait Averages")

plt.tight_layout()
plt.savefig("output/default/summary.png")
```

---

## Core Design Decisions

The foundation of this simulation is the idea that humans contain the capacity for growth, change, and evolution. The simulation models this as **traits**: characteristics that make people who they are that shift over time as they mature. This is represented as two vectors: one of traits that humans are born with, largely based on their parents' traits; and another vector of current traits, which is their base traits modified by their life (*trait drift*).

Along with traits, which is how individuals grow, the simulation provides the construct of "social technologies", which is how groups grow over time. The core idea behind them is that the traits of the agents influences their "discovery", so groups with higher concentrations of some trait combination tend more strongly to some social technologies.

### Traits

The simulation does not have "priest," "warrior," or "philosopher" agent types. These emerge naturally from trait combinations:
- High wonder + high attribution_style + high reverence + high conformity → priestly behavior
- High aggression + high dominance + low empathy → warrior behavior
- High curiosity + high abstraction + modeler orientation → philosophical behavior

The same underlying mechanics, different initial conditions, radically different historical outcomes. This is intentional - it means adding a new "type" is just finding a new region of trait space.

All 16 traits are represented as floats in [0, 1].

| Category | Trait | What it drives |
|---|---|---|
| Cognitive | `curiosity` | Frequency of exploration and questioning |
| | `pattern_recognition` | Speed of developing useful models of the world |
| | `abstraction` | Ability to form concepts beyond the immediate |
| | `memory_narrative` | Transmitting knowledge through story and memory |
| Social | `social_desire` | Drive to form and maintain relationships |
| | `dominance` | Tendency to seek/accept leadership |
| | `empathy` | Cooperation, conflict de-escalation, in-group care |
| | `trust` | Willingness to cooperate with others |
| | `conformity` | Tendency to adopt group norms vs. deviate |
| Survival | `risk_tolerance` | Exploration vs. consolidation |
| | `aggression` | Conflict initiation; resource competition |
| | `industriousness` | Rate of resource acquisition |
| | `patience` | Long-term investment over immediate gain |
| Unknown | `wonder` | Frequency of engaging with the unexplained |
| | `attribution_style` | 0 = Modeler (mechanical), 1 = Attributor (intentional) |
| | `reverence` | Emotional weight given to the Unknown Player |

---

### Social Technologies

Social technologies emerge when a group's average trait profile crosses the defined thresholds. No agent "decides" to invent religion or governance. These technologies activate automatically when a group's average trait profile crosses the emergence thresholds defined in `core/social_tech.py`. They are discovered, not designed - which mirrors how they actually developed in human history.

| Technology | Emergence requires | Effect |
|---|---|---|
| **Taboo** | empathy ≥ 0.45, conformity ≥ 0.45 | Reduces in-group aggression by 50% |
| **Religion** | wonder ≥ 0.55, reverence ≥ 0.55, attribution_style ≥ 0.55, conformity ≥ 0.50 | Strong in-group cohesion; reduces in-group aggression 70%; increases out-group aggression 30%; suppresses inspiration |
| **Philosophy** | curiosity ≥ 0.60, abstraction ≥ 0.55, pattern_recognition ≥ 0.55 | Triples spontaneous inspiration rate |
| **Economy** | trust ≥ 0.55, patience ≥ 0.55, industriousness ≥ 0.55 | Increases forage gains 50%; reduces out-group aggression 20% |
| **Governance** | dominance ≥ 0.55, social_desire ≥ 0.60, conformity ≥ 0.55 | Increases group cooperation; reduces in-group aggression; increases out-group aggression |

---

### The Unknown Player

The Unknown Player does not exist as an agent in the simulation. It is a random event generator. But agents with high wonder and reverence form beliefs about it, and those beliefs spread through social networks via the belief transmission mechanic. Groups of Attributors (who assign intent to the Unknown) develop religion. Groups of Modelers (who seek mechanical patterns) develop philosophy. Groups of Indifferent agents develop neither - and are potentially more vulnerable to Unknown Player events they haven't prepared for.

### Trait Drift: Nature and Nurture

Each agent carries two trait vectors:
- `base_traits`: heritable, set at birth, changes only through spontaneous inspiration (rare mutation)
- `current_traits`: drifts with lived experience, bounded by a maximum deviation from base

This models the tension between nature (what you're born with) and nurture (what experience shapes). A naturally aggressive agent forced into a cooperative group accumulates pressure as their current_traits drift toward cooperation while base_traits remain high - a latent tension that can snap back under stress.

### Physical Environment Excluded (by design)

Real civilizations were profoundly shaped by geography, climate, and available resources. That is true and important, however; this simulation deliberately holds the physical environment constant - homogeneous resources, no terrain - to isolate the variables we care about: *traits, social dynamics, and belief systems*. Adding environmental differentiation is a planned future expansion.

---


## Experiment Ideas

**Does religion emerge?**
Lower the wonder/reverence thresholds in `config/default.yaml` or raise the starting means. Observe whether religion's suppression of inspiration stunts long-term development.

**Can a peaceful culture survive?**
Set aggression to 0.20 mean and empathy to 0.80. Run against a default population with `--seed` fixed. Does the cooperative culture get absorbed? At what rate?

**Enlightenment vs. survival**
Run the same seed with `--utility survival` and `--utility enlightenment`. Compare population curves, social technology emergence, and belief orientation distributions.

**The Unknown Player's role**
Set `event_probability: 0.0` in config (no Unknown Player events). Does religion still emerge? Does wonder have the same drift trajectory?

**What kills civilizations?**
Run `--ticks 1000` and watch for collapses. What trait distributions tend to precede a population crash? What social technologies were present? What were missing?

---

## Future Improvements

- **Environmental differentiation**: geography, climate, resource distribution - how different starting conditions produce different cultural trajectories
- **Inter-group conflict and absorption**: coordinated resource contention, territorial conquest, cultural assimilation
- **Non-human agents**: deer, predators, plant ecosystems - other "players" with simpler utility functions interacting with human agents

---

## Theoretical Foundations

The simulation is built on a set of ideas from evolutionary game theory, social science, and philosophy, none of which I have formal education on.

### Evolutionary Game Theory

The core framework. Unlike classical game theory (which asks what a rational actor *should* do), evolutionary game theory asks what strategies *persist* over time when agents reproduce and die based on their outcomes. Strategies that produce better survival and reproduction spread; losing strategies die off.

Key idea: the simulation's agents are not "playing optimally." They are playing according to their traits, and the population-level distribution of traits shifts as some agents survive and reproduce more than others.

### The Hawk-Dove Game

One of the foundational models in evolutionary game theory. Two strategies compete for a resource:
- **Hawks** always escalate conflict
- **Doves** always retreat from actual violence

Neither pure-Hawk nor pure-Dove populations are stable. Hawks pay heavy costs fighting each other; Doves are invaded by Hawks who take everything. The system settles at a **mixed equilibrium** - a stable ratio of both strategies. This explains why aggression persists in populations alongside cooperation, and why neither completely eliminates the other.

This simulation's aggression trait and compete/cooperate action system embodies Hawk-Dove dynamics at the individual level.

### Tit-for-Tat and Axelrod's Tournaments

In the 1980s, Robert Axelrod ran computer tournaments pitting strategies against each other in iterated Prisoner's Dilemmas (repeated cooperation/defection games). The consistent winner was **Tit-for-Tat**: cooperate by default, retaliate when attacked, forgive quickly, and never defect first.

The lesson: pure pacifism is unstable (it gets invaded by defectors), but **conditional cooperation** - generous by default, retaliatory when necessary - is remarkably durable. In this simulation, high-trust, high-empathy agents with moderate aggression approximate this strategy. The social technology layer (taboo, religion, governance) can be understood as mechanisms that make defection costly enough to push populations toward the cooperative equilibrium.

### Nash Equilibrium

A state in a game where no player can improve their outcome by unilaterally changing their strategy. In this simulation, **social technologies are Nash equilibria** that groups stumble into - stable behavioral agreements where individual defection is too costly (enforced by supernatural belief, law, economic interdependence, or social ostracism). The simulation does not hard-code these technologies; they emerge when group trait averages cross certain thresholds, and once established, they persist because no individual benefits from abandoning them alone.

### Arrow's Impossibility Theorem (1951)

Kenneth Arrow proved that no system can aggregate individual preferences into a consistent group preference that satisfies a small set of basic fairness conditions simultaneously. In plain terms: **pure democratic group utility is mathematically unstable** at scale.

This motivates a design decision in the simulation: groups do not average their members' preferences into a collective utility function. Instead, they develop a **dominant voice** - the highest-dominance member whose preferences effectively become the group's. This reflects historical patterns where even nominally collective groups coalesce around influential individuals. The tension between the dominant voice's interests and the group members' interests is tracked as *latent sentiment*, which can trigger restructuring.

### Dunbar's Number

Robin Dunbar's research suggests that the cognitive limit for stable social relationships in primates (including humans) is approximately 150 individuals. Below this threshold, genuine collective decision-making and mutual monitoring are feasible. Above it, groups require formal social technologies - hierarchy, religion, law - to maintain cohesion.

This is reflected in the simulation's group dynamics: small groups (under 3 members) cannot develop social technologies. Larger groups develop formal structures as they grow, and those structures change the behavior of every member.

### Incomplete Information and "Nature as a Player"

In formal game theory, a fictitious player called **Nature** is sometimes introduced to represent random events with no utility function - pure chance occurrences that all other players must respond to. John Harsanyi formalized this for games of incomplete information (1967-1968).

The **Unknown Player** in this simulation is an evolution of this concept. It does not act, has no utility function, and produces no intentional outputs. It is a random event generator. But agents form beliefs *about* it - attributing intent, seeking patterns, developing rituals - and those beliefs become real strategic variables that shape group cohesion, conflict, and innovation. The Unknown Player is simultaneously nothing and enormously consequential.

### Agent-Based Modeling (ABM)

Rather than modeling populations as aggregate statistics, ABM represents individual agents with their own states, rules, and interactions. Macro-level patterns (tribes, religions, metagames) emerge from micro-level behavior rather than being prescribed. This simulation uses **Mesa**, a Python ABM framework, for agent scheduling, data collection, and model structure.

ABM is particularly suited to this project because the phenomena of interest - cultural emergence, group formation, the spread of beliefs - are inherently about individual interactions producing unexpected collective outcomes.

---

## References and Further Reading

The theoretical foundations are drawn from established fields. These are starting points, not an exhaustive list:

- **Evolutionary game theory**: Maynard Smith, J. & Price, G.R. (1973). *The logic of animal conflict.* Nature.
- **Hawk-Dove game**: Maynard Smith, J. (1982). *Evolution and the Theory of Games.* Cambridge University Press.
- **Tit-for-Tat and cooperation**: Axelrod, R. (1984). *The Evolution of Cooperation.* Basic Books.
- **Incomplete information games / Nature as a player**: Harsanyi, J.C. (1967). *Games with incomplete information played by Bayesian players.* Management Science.
- **Arrow's Impossibility Theorem**: Arrow, K.J. (1951). *Social Choice and Individual Values.* Wiley.
- **Dunbar's Number**: Dunbar, R.I.M. (1992). *Neocortex size as a constraint on group size in primates.* Journal of Human Evolution.
- **Agent-Based Modeling**: Axelrod, R. (1997). *The Complexity of Cooperation.* Princeton University Press.
- **Mesa (Python ABM framework)**: https://mesa.readthedocs.io
