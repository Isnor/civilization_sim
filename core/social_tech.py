"""
Social Technologies: emergent group-level mechanisms that modify agent behavior.

Each technology has:
  - emergence_conditions: avg trait thresholds that must be met in the group
  - effects: multipliers applied to action probabilities and resource flows

Technologies are registered in REGISTRY. The Model checks emergence conditions
each tick and activates technologies when groups cross the threshold.

All effects are applied as *multipliers* against base values, so a value of 1.0
means no change. Technologies stack multiplicatively.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SocialTechnology:
    """
    Defines a social technology's emergence conditions and behavioral effects.

    emergence_conditions: {trait_name: min_avg_value_in_group}
    effects: {effect_key: multiplier}

    Effect keys:
      in_group_aggression_mult    — scales aggression actions within the group
      out_group_aggression_mult   — scales aggression toward non-members
      cooperation_bonus_mult      — scales resource sharing within group
      forage_gain_mult            — scales resources gained from foraging
      inspiration_probability_mult — scales rate of spontaneous inspiration
      drift_rate_mult             — scales how fast current_traits drift
      group_cooperation_mult      — overall cooperation multiplier
    """

    name: str
    description: str
    emergence_conditions: dict[str, float]
    effects: dict[str, float] = field(default_factory=dict)

    def conditions_met(self, avg_traits: dict[str, float]) -> bool:
        """Return True if all emergence conditions are satisfied."""
        for trait, threshold in self.emergence_conditions.items():
            if avg_traits.get(trait, 0.0) < threshold:
                return False
        return True

    def effect(self, key: str, default: float = 1.0) -> float:
        return self.effects.get(key, default)


# ---------------------------------------------------------------------------
# Registry — all social technologies available to groups
# ---------------------------------------------------------------------------

REGISTRY: dict[str, SocialTechnology] = {
    "taboo": SocialTechnology(
        name="taboo",
        description=(
            "Informal norms forbidding harmful in-group actions. "
            "The most primitive social technology — emerges whenever "
            "empathy and conformity are both present."
        ),
        emergence_conditions={"empathy": 0.45, "conformity": 0.45},
        effects={
            "in_group_aggression_mult": 0.5,
        },
    ),
    "religion": SocialTechnology(
        name="religion",
        description=(
            "Shared belief system centered on the Unknown Player. "
            "Generates extraordinary cohesion and willingness to sacrifice "
            "for the group, at the cost of curiosity suppression."
        ),
        emergence_conditions={
            "wonder": 0.55,
            "reverence": 0.55,
            "attribution_style": 0.55,
            "conformity": 0.50,
        },
        effects={
            "in_group_aggression_mult": 0.3,
            "out_group_aggression_mult": 1.3,
            "cooperation_bonus_mult": 1.4,
            "inspiration_probability_mult": 0.5,   # suppresses curiosity
        },
    ),
    "philosophy": SocialTechnology(
        name="philosophy",
        description=(
            "Systematic inquiry into the nature of the world and the Unknown. "
            "Slow to develop, produces compounding advantages through better "
            "world-models and more frequent inspiration."
        ),
        emergence_conditions={
            "curiosity": 0.60,
            "abstraction": 0.55,
            "pattern_recognition": 0.55,
        },
        effects={
            "inspiration_probability_mult": 3.0,
            "drift_rate_mult": 0.6,   # more intentional trait change
        },
    ),
    "economy": SocialTechnology(
        name="economy",
        description=(
            "Systematic resource exchange and specialization. "
            "Requires surplus, trust, and the patience to delay consumption. "
            "Creates interdependence that makes war costly."
        ),
        emergence_conditions={
            "trust": 0.55,
            "patience": 0.55,
            "industriousness": 0.55,
        },
        effects={
            "forage_gain_mult": 1.5,
            "cooperation_bonus_mult": 1.3,
            "out_group_aggression_mult": 0.8,   # trade reduces war incentives
        },
    ),
    "governance": SocialTechnology(
        name="governance",
        description=(
            "Formal leadership structures and codified rules. "
            "Concentrates decision-making, enabling fast coordinated action. "
            "Aligns group utility with dominant voice, for better or worse."
        ),
        emergence_conditions={
            "dominance": 0.55,
            "social_desire": 0.60,
            "conformity": 0.55,
        },
        effects={
            "group_cooperation_mult": 1.4,
            "in_group_aggression_mult": 0.6,
            "out_group_aggression_mult": 1.2,   # coordinated external projection
        },
    ),
}


def get_active_effects(active_technologies: set[str]) -> dict[str, float]:
    """
    Compute stacked multipliers for a set of active technology names.

    Multiple technologies stack multiplicatively for each effect key.
    Returns a dict of {effect_key: combined_multiplier}.
    """
    combined: dict[str, float] = {}
    for tech_name in active_technologies:
        tech = REGISTRY.get(tech_name)
        if tech is None:
            continue
        for key, mult in tech.effects.items():
            combined[key] = combined.get(key, 1.0) * mult
    return combined


def compute_group_avg_traits(member_agents: list) -> dict[str, float]:
    """Compute average current_trait values across a list of agents."""
    if not member_agents:
        return {}
    from core.traits import TRAIT_NAMES
    totals: dict[str, float] = {name: 0.0 for name in TRAIT_NAMES}
    for agent in member_agents:
        for name in TRAIT_NAMES:
            totals[name] += agent.current_traits.get(name)
    n = len(member_agents)
    return {name: totals[name] / n for name in TRAIT_NAMES}
