"""
Player: the atomic unit of the simulation.

Each player is a Mesa Agent. On each tick, a player:
  1. Decides an action based on their current_traits and utility function
  2. Executes that action (forage, rest, socialize, compete, contemplate)
  3. Logs the experience for later trait drift

Reproduction is handled by the Model (requires two willing agents).
Trait drift is applied by the Model at the end of each tick cycle.

Actions:
  forage      — gather resources from the environment
  rest        — recover, low cost, no gain
  socialize   — strengthen a relationship with a known or new agent
  compete     — attempt to take resources from another agent
  contemplate — engage with an unexplained phenomenon (Unknown Player)

Action weights are computed from current_traits. The Model applies social
technology effect multipliers before sampling.
"""

from __future__ import annotations

import mesa
import numpy as np

from core.traits import TraitVector, inherit_traits, drift_traits, spontaneous_inspiration
from core.beliefs import BeliefSystem
from core.groups import RelationshipState


ACTIONS = ["forage", "rest", "socialize", "compete", "contemplate"]


class Player(mesa.Agent):
    """
    A single agent (human) in the civilization simulation.

    Parameters
    ----------
    model : CivilizationModel
    base_traits : TraitVector
        Heritable trait vector set at birth.
    utility_fn : str
        "survival" or "enlightenment" — shapes action weights.
    parent_ids : tuple[int, int] | None
        IDs of parents, for lineage tracking.
    """

    def __init__(
        self,
        model,
        base_traits: TraitVector,
        utility_fn: str = "survival",
        parent_ids: tuple[int, int] | None = None,
    ):
        super().__init__(model)
        self.base_traits: TraitVector = base_traits
        self.current_traits: TraitVector = TraitVector.from_array(base_traits.to_array())
        self.utility_fn: str = utility_fn
        self.parent_ids: tuple[int, int] | None = parent_ids

        self.beliefs: BeliefSystem = BeliefSystem.from_attribution_style(
            base_traits.attribution_style
        )

        # Relationships: other_agent_unique_id -> RelationshipState
        self.relationships: dict[int, RelationshipState] = {}

        # Experience log: list of (trait_name, delta) tuples accumulated this tick-cycle
        self._experience_deltas: np.ndarray = np.zeros(16, dtype=float)
        self._experience_count: int = 0

        self.resources: float = model.config["resources"]["initial"]
        self.age: int = 0
        self.alive: bool = True

        # Group membership (set of group IDs)
        self.group_ids: set[int] = set()

        # Track what action was taken this tick (for data collection)
        self.last_action: str = "none"

    # ------------------------------------------------------------------
    # Mesa step
    # ------------------------------------------------------------------

    def step(self) -> None:
        if not self.alive:
            return

        cfg = self.model.config
        survival_cost = cfg["resources"]["survival_cost"]

        # Pay survival cost
        self.resources -= survival_cost
        self.age += 1

        if self.resources <= 0:
            self.alive = False
            self.last_action = "died_starvation"
            return

        max_age = cfg["resources"].get("max_age", 80)
        if self.age >= max_age:
            self.alive = False
            self.last_action = "died_age"
            return

        # Compute action weights with social tech effects applied
        effects = self._get_active_effects()
        weights = self._action_weights(effects)

        # Sample action
        action = self.model.rng.choice(ACTIONS, p=weights)
        self.last_action = action
        self._execute_action(action, effects)

    # ------------------------------------------------------------------
    # Action weights
    # ------------------------------------------------------------------

    def _action_weights(self, effects: dict) -> np.ndarray:
        """
        Compute normalized action probability weights from current_traits.

        utility_fn == "enlightenment" shifts weight from forage/compete
        toward contemplate/socialize.
        """
        t = self.current_traits
        in_grp_agg = effects.get("in_group_aggression_mult", 1.0)

        # Base weights
        w_forage = 0.35 + t.industriousness * 0.25
        w_rest = 0.05 + (1.0 - t.risk_tolerance) * 0.05
        w_socialize = 0.15 + t.social_desire * 0.25
        w_compete = (0.10 + t.aggression * 0.20 - t.empathy * 0.05) * in_grp_agg
        w_contemplate = 0.05 + t.wonder * 0.15 + t.curiosity * 0.10

        if self.utility_fn == "enlightenment":
            w_forage *= 0.6
            w_compete *= 0.4
            w_contemplate *= 2.5
            w_socialize *= 1.3

        weights = np.array([w_forage, w_rest, w_socialize, w_compete, w_contemplate])
        weights = np.clip(weights, 0.001, None)
        return weights / weights.sum()

    # ------------------------------------------------------------------
    # Action execution
    # ------------------------------------------------------------------

    def _execute_action(self, action: str, effects: dict) -> None:
        cfg = self.model.config
        rng = self.model.rng

        if action == "forage":
            lo, hi = cfg["resources"]["forage_gain"]
            gain = rng.uniform(lo, hi) * effects.get("forage_gain_mult", 1.0)
            self.resources += gain
            self._record_experience("industriousness", +0.3)
            self._record_experience("patience", +0.1)

        elif action == "rest":
            self.resources += cfg["resources"].get("rest_gain", 0.3)

        elif action == "socialize":
            self._do_socialize(effects)

        elif action == "compete":
            self._do_compete(effects)

        elif action == "contemplate":
            self._do_contemplate()

    def _do_socialize(self, effects: dict) -> None:
        """
        Attempt to strengthen a relationship with another agent.

        Picks a known agent (preferring lower-affinity relationships for growth)
        or a stranger if social_desire is high enough.
        """
        t = self.current_traits
        rng = self.model.rng

        target = self._pick_social_target()
        if target is None:
            return

        if target.unique_id not in self.relationships:
            self.relationships[target.unique_id] = RelationshipState()
        if self.unique_id not in target.relationships:
            target.relationships[self.unique_id] = RelationshipState()

        # Cooperate or exchange beliefs
        outcome = "cooperative"
        bonus = self.model.config["social"].get("cooperation_bonus", 0.2)
        bonus *= effects.get("cooperation_bonus_mult", 1.0)
        self.resources += bonus
        target.resources += bonus

        self.relationships[target.unique_id].update(outcome, t.empathy)
        target.relationships[self.unique_id].update(outcome, target.current_traits.empathy)

        # Belief exchange
        if t.trust > 0.4:
            self.beliefs.receive_belief(target.beliefs, t.trust, t.conformity)

        self._record_experience("social_desire", +0.2)
        self._record_experience("trust", +0.1)
        self._record_experience("empathy", +0.1)

    def _do_compete(self, effects: dict) -> None:
        """
        Attempt to take resources from another agent.

        Success probability scales with relative aggression.
        Failure damages the relationship and may trigger retaliation.
        """
        t = self.current_traits
        rng = self.model.rng

        out_grp_mult = effects.get("out_group_aggression_mult", 1.0)

        # Prefer out-group targets
        target = self._pick_compete_target()
        if target is None:
            return

        # Adjust aggression for in/out group
        is_in_group = bool(self.group_ids & target.group_ids)
        agg = t.aggression * (1.0 if is_in_group else out_grp_mult)

        win_prob = agg / (agg + target.current_traits.aggression + 0.001)
        if rng.random() < win_prob:
            stolen = min(target.resources * 0.2, target.resources - 0.1)
            stolen = max(stolen, 0.0)
            self.resources += stolen
            target.resources -= stolen
            outcome = "hostile"
            self._record_experience("aggression", +0.3)
            self._record_experience("risk_tolerance", +0.2)
        else:
            # Failed attack costs energy
            self.resources -= 0.5
            outcome = "hostile"
            self._record_experience("aggression", -0.1)

        if target.unique_id not in self.relationships:
            self.relationships[target.unique_id] = RelationshipState()
        if self.unique_id not in target.relationships:
            target.relationships[self.unique_id] = RelationshipState()

        self.relationships[target.unique_id].update(outcome, t.empathy)
        target.relationships[self.unique_id].update(outcome, target.current_traits.empathy)

    def _do_contemplate(self) -> None:
        """
        Engage with the Unknown Player.

        If there are pending Unknown Player events in the model, process one.
        Otherwise just record the experience of wondering.
        """
        t = self.current_traits

        # Pull the latest Unknown Player event if available
        events = getattr(self.model, "recent_unknown_events", [])
        if events:
            event = self.model.rng.choice(events)
            self.beliefs.receive_event(
                tick=self.model.steps,
                event_type=event.event_type,
                wonder=t.wonder,
                reverence=t.reverence,
                attribution_style=t.attribution_style,
            )

        self._record_experience("wonder", +0.2)
        self._record_experience("curiosity", +0.15)
        if t.attribution_style > 0.5:
            self._record_experience("reverence", +0.1)

    # ------------------------------------------------------------------
    # Target selection helpers
    # ------------------------------------------------------------------

    def _pick_social_target(self):
        """Return a candidate agent to socialize with."""
        rng = self.model.rng
        t = self.current_traits

        known = list(self.relationships.keys())
        encounter_prob = self.model.config["social"]["encounter_probability"]

        # Sometimes meet a stranger
        if not known or rng.random() < encounter_prob * t.social_desire:
            candidates = [
                a for a in self.model.agents
                if a.unique_id != self.unique_id and a.alive
            ]
            if candidates:
                return rng.choice(candidates)

        if known:
            target_id = rng.choice(known)
            agent = self.model.agents_by_id.get(target_id)
            if agent and agent.alive:
                return agent
        return None

    def _pick_compete_target(self):
        """Return a candidate agent to compete with, preferring out-group."""
        rng = self.model.rng
        living = [a for a in self.model.agents if a.unique_id != self.unique_id and a.alive]
        if not living:
            return None

        out_group = [a for a in living if not (self.group_ids & a.group_ids)]
        if out_group and rng.random() < 0.7:
            return rng.choice(out_group)
        return rng.choice(living)

    # ------------------------------------------------------------------
    # Trait drift helpers
    # ------------------------------------------------------------------

    def _record_experience(self, trait_name: str, delta: float) -> None:
        """Accumulate an experience delta for a named trait."""
        from core.traits import TRAIT_NAMES
        if trait_name in TRAIT_NAMES:
            idx = TRAIT_NAMES.index(trait_name)
            self._experience_deltas[idx] += delta
            self._experience_count += 1

    def apply_drift(self, rate: float, max_deviation: float) -> None:
        """
        Apply accumulated experience deltas to current_traits.
        Called by the Model at end of tick.
        """
        if self._experience_count == 0:
            return
        normalized = np.clip(self._experience_deltas / max(self._experience_count, 1), -1.0, 1.0)
        self.current_traits = drift_traits(
            self.current_traits, self.base_traits, normalized, rate, max_deviation
        )
        self._experience_deltas[:] = 0
        self._experience_count = 0

    def apply_inspiration(self, magnitude: float, rng) -> None:
        """Mutate base_traits via spontaneous inspiration (rare)."""
        self.base_traits = spontaneous_inspiration(self.base_traits, magnitude, rng)
        # Partially reset current traits toward new base
        self.current_traits = TraitVector.from_array(
            (self.current_traits.to_array() + self.base_traits.to_array()) / 2.0
        )

    # ------------------------------------------------------------------
    # Reproduction
    # ------------------------------------------------------------------

    def can_reproduce(self) -> bool:
        cfg = self.model.config["resources"]
        return (
            self.alive
            and self.resources >= cfg["reproduction_threshold"]
            and self.age >= cfg.get("min_reproduction_age", 5)
            and self.age <= cfg.get("max_reproduction_age", 60)
        )

    def reproduce_with(self, partner: Player) -> Player:
        """
        Create an offspring agent. Consumes resources from both parents.
        Offspring inherits base_traits from parents with variance.
        """
        cfg = self.model.config
        cost = cfg["resources"]["reproduction_cost"]
        variance = cfg["heritability"]["variance"]

        self.resources -= cost
        partner.resources -= cost

        offspring_traits = inherit_traits(
            self.base_traits, partner.base_traits, variance, self.model.rng
        )

        # Small chance of spontaneous inspiration at birth
        insp_prob = cfg["inspiration"]["probability"]
        if self.model.rng.random() < insp_prob * 5:  # higher at birth
            offspring_traits = spontaneous_inspiration(offspring_traits, 0.15, self.model.rng)

        child = Player(
            model=self.model,
            base_traits=offspring_traits,
            utility_fn=self.utility_fn,
            parent_ids=(self.unique_id, partner.unique_id),
        )
        child.resources = cfg["resources"].get("initial_offspring", cfg["resources"]["initial"] * 0.5)
        return child

    # ------------------------------------------------------------------
    # Utility / reporting helpers
    # ------------------------------------------------------------------

    def _get_active_effects(self) -> dict:
        """Retrieve stacked social technology effects for this agent's groups."""
        from core.social_tech import get_active_effects
        active_techs: set[str] = set()
        for gid in self.group_ids:
            group = self.model.groups.get(gid)
            if group:
                active_techs |= group.social_technologies
        return get_active_effects(active_techs)

    @property
    def metagame(self) -> str:
        """
        Classify this agent's primary metagame based on group technologies.
        Returns the first matching label, or "none".
        """
        active_techs: set[str] = set()
        for gid in self.group_ids:
            group = self.model.groups.get(gid)
            if group:
                active_techs |= group.social_technologies
        if not active_techs:
            return "none"
        priority = ["religion", "governance", "economy", "philosophy", "taboo"]
        for p in priority:
            if p in active_techs:
                return p
        return next(iter(active_techs))
