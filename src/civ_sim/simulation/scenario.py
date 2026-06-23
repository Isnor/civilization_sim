"""
Scenario for the CivilizationModel.

"""

from typing import List
from mesa.experimental.scenarios import Scenario
from civ_sim.simulation.events import (
    EVENT_TYPES,
)


# TODO: add "social tech achieved"
END_GAMES: List[str] = ['max_population', 'all_humans_dead', 'max_ticks']


# TODO: it'd be kind of neat to put annotations on the fields to map them to UI bits;
#  e.g. the different solara UI components that are used for configuring runs
class CivilizationScenario(Scenario):
    # population
    population_initial_size: int = 100
    population_max_size: int = 1000
    population_utility_fn: str = "survival"

    # resources
    resources_initial:float = 10.0              # starting resources for each agent
    resources_initial_offspring:float = 5.0     # starting resources for newborns
    resources_survival_cost:float = 1.0         # resources consumed per tick
    resources_rest_gain:float = 0.3             # resources recovered by resting
    resources_forage_gain:tuple[float, float] = (1.5, 3.5)   # [min, max] resources gained by foraging
    resources_reproduction_threshold:float = 15.0  # min resources to reproduce
    resources_reproduction_cost:float = 5.0     # resources spent by each parent
    resources_min_reproduction_age:float = 13   # agents begin to reproduce after this many ticks
    resources_max_reproduction_age:float = 60   # agents stop reproducing after this many ticks
    resources_max_age:float = 80                # agents die after this many ticks

    # initial trait distribution; each tuple is (average, std_deviation)
    # trait values themselves are clamped to [0, 1]
    traits_curiosity: tuple[float, float] = (.5, .2)
    traits_pattern_recognition: tuple[float, float] = (.5, .2)
    traits_abstraction: tuple[float, float] = (.4, .2)
    traits_memory_narrative: tuple[float, float] = (.5, .2)
    traits_social_desire: tuple[float, float] = (.6, .2)
    traits_dominance: tuple[float, float] = (.5, .2)
    traits_empathy: tuple[float, float] = (.5, .2)
    traits_trust: tuple[float, float] = (.45, .2)
    traits_conformity: tuple[float, float] = (.5, .2)
    traits_risk_tolerance: tuple[float, float] = (.5, .2)
    traits_aggression: tuple[float, float] = (.45, .2)
    traits_industriousness: tuple[float, float] = (.5, .2)
    traits_patience: tuple[float, float] = (.5, .2)
    traits_wonder: tuple[float, float] = (.4, .2)
    traits_attribution_style: tuple[float, float] = (.5, .25)
    traits_reverence: tuple[float, float] = (.4, .2)

    # trait drift / growth
    trait_drift_rate: float = .02
    trait_drift_max_deviation: float = .03

    # social
    social_encounter_probability: float = .25
    social_group_formation_threshold: float = .45
    social_cooperation_bonus: float = .30

    # heritability
    heritability_variance: float = .10

    # inspiration
    inspiration_probability: float = .01

    # unknown_player events
    unknown_player_event_probability: float = .01
    unknown_player_event_types: List[str] = EVENT_TYPES

    # endgames
    endgames: List[str] = END_GAMES
    endgames_max_steps: int = 1000


# this is defined so that we can uniquely identify runs. We only use it to name results tabs right now
def __hash__(self):
    return sum(hash(a) for a in [
        self.population_initial_size,
        self.population_max_size,
        self.population_utility_fn,
        self.resources_initial,
        self.resources_initial_offspring,
        self.resources_survival_cost,
        self.resources_rest_gain,
        self.resources_forage_gain,
        self.resources_reproduction_threshold,
        self.resources_reproduction_cost,
        self.resources_min_reproduction_age,
        self.resources_max_reproduction_age,
        self.resources_max_age,
        self.traits_curiosity,
        self.traits_pattern_recognition,
        self.traits_abstraction,
        self.traits_memory_narrative,
        self.traits_social_desire,
        self.traits_dominance,
        self.traits_empathy,
        self.traits_trust,
        self.traits_conformity,
        self.traits_risk_tolerance,
        self.traits_aggression,
        self.traits_industriousness,
        self.traits_patience,
        self.traits_wonder,
        self.traits_attribution_style,
        self.traits_reverence,
        self.trait_drift_rate,
        self.trait_drift_max_deviation,
        self.social_encounter_probability,
        self.social_group_formation_threshold,
        self.social_cooperation_bonus,
        self.heritability_variance,
        self.inspiration_probability,
        self.unknown_player_event_probability,
    ])