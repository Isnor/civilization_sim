"""
TraitVector: the core representation of an agent's heritable and drifting traits.

All traits are floats in [0, 1].
Each agent carries two vectors:
  - base_traits:    inherited at birth, stable (only altered by spontaneous inspiration)
  - current_traits: drifts over time via Experience accumulation
"""

from __future__ import annotations

import math
from dataclasses import dataclass, fields, astuple
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from numpy.random import Generator


TRAIT_NAMES = [
    # Cognitive
    "curiosity",
    "pattern_recognition",
    "abstraction",
    "memory_narrative",
    # Social
    "social_desire",
    "dominance",
    "empathy",
    "trust",
    "conformity",
    # Survival / Agency
    "risk_tolerance",
    "aggression",
    "industriousness",
    "patience",
    # Unknown Orientation
    "wonder",
    "attribution_style",   # 0.0 = pure Modeler, 1.0 = pure Attributor
    "reverence",
]


@dataclass
class TraitVector:
    # Cognitive
    curiosity: float = 0.5
    pattern_recognition: float = 0.5
    abstraction: float = 0.5
    memory_narrative: float = 0.5
    # Social
    social_desire: float = 0.5
    dominance: float = 0.5
    empathy: float = 0.5
    trust: float = 0.5
    conformity: float = 0.5
    # Survival / Agency
    risk_tolerance: float = 0.5
    aggression: float = 0.5
    industriousness: float = 0.5
    patience: float = 0.5
    # Unknown Orientation
    wonder: float = 0.5
    attribution_style: float = 0.5
    reverence: float = 0.5

    def to_array(self) -> np.ndarray:
        return np.array(astuple(self), dtype=float)

    @classmethod
    def from_array(cls, arr: np.ndarray) -> TraitVector:
        return cls(*arr.tolist())

    def get(self, name: str) -> float:
        return getattr(self, name)

    def clamp(self) -> TraitVector:
        """Return a new TraitVector with all values clamped to [0, 1]."""
        arr = np.clip(self.to_array(), 0.0, 1.0)
        return TraitVector.from_array(arr)

    def mean(self) -> float:
        return float(np.mean(self.to_array()))


def random_traits(distributions: dict, rng: Generator) -> TraitVector:
    """
    Sample a TraitVector from per-trait normal distributions.

    distributions: flat dict of {trait_name: [mean, std_dev]}
    Missing traits default to [0.5, 0.2].
    """
    values = {}
    for name in TRAIT_NAMES:
        mean, std = distributions.get(name, [0.5, 0.2])
        values[name] = float(np.clip(rng.normal(mean, std), 0.0, 1.0))
    return TraitVector(**values)


def inherit_traits(
    parent1: TraitVector,
    parent2: TraitVector,
    variance: float,
    rng: Generator,
) -> TraitVector:
    """
    Produce offspring base traits.

    Each trait is drawn from a normal distribution centered on the parents'
    average, with the given variance. Spontaneous inspiration can produce
    values well outside the parent range.
    """
    p1 = parent1.to_array()
    p2 = parent2.to_array()
    midpoint = (p1 + p2) / 2.0
    noise = rng.normal(0, variance, size=len(midpoint))
    offspring = np.clip(midpoint + noise, 0.0, 1.0)
    return TraitVector.from_array(offspring)


def drift_traits(
    current: TraitVector,
    base: TraitVector,
    experience_deltas: np.ndarray,
    rate: float,
    max_deviation: float,
) -> TraitVector:
    """
    Nudge current_traits based on accumulated experience deltas.

    experience_deltas: array of shape (16,), each value in [-1, 1].
      Positive = trait-reinforcing experiences; negative = trait-suppressing.
    rate: max change per call (scales the delta).
    max_deviation: how far current can stray from base.

    The drift is applied toward the direction of experience but is bounded by
    max_deviation from base_traits so that nature constrains nurture.
    """
    current_arr = current.to_array()
    base_arr = base.to_array()

    delta = experience_deltas * rate
    proposed = current_arr + delta

    # Enforce max_deviation from base
    low = np.clip(base_arr - max_deviation, 0.0, 1.0)
    high = np.clip(base_arr + max_deviation, 0.0, 1.0)
    drifted = np.clip(proposed, low, high)

    return TraitVector.from_array(drifted)


def spontaneous_inspiration(
    base: TraitVector,
    magnitude: float,
    rng: Generator,
) -> TraitVector:
    """
    Apply a random mutation to base_traits (rare event).

    Selects 1-3 random traits and shifts them by up to `magnitude`.
    Models a sudden cognitive or philosophical leap.
    """
    # TODO: maybe the traits chosen shouldn't be random, and should instead be weighted
    # by their most recent action(s) and highest trait values
    arr = base.to_array()
    n_affected = rng.integers(1, 4)
    indices = rng.choice(len(arr), size=n_affected, replace=False)
    for i in indices:
        arr[i] = float(np.clip(arr[i] + rng.uniform(-magnitude, magnitude), 0.0, 1.0))
    return TraitVector.from_array(arr)
