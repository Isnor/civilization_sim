"""
CivilizationModel: the Mesa Model that orchestrates the simulation.

Each call to model.step() runs one tick:
  1. Generate Unknown Player event (maybe)
  2. Step all living agents (perception, decision, action)
  3. Apply trait drift to all agents
  4. Check for spontaneous inspiration
  5. Update group memberships and elect dominant voices
  6. Check social technology emergence in each group
  7. Process reproduction (willing pairs)
  8. Remove dead agents
  9. Collect data
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import mesa
import numpy as np

from core.agent import Player
from core.groups import Group, RelationshipState
from core.social_tech import REGISTRY, compute_group_avg_traits
from core.traits import random_traits, TRAIT_NAMES
from simulation.events import (
    UnknownPlayerEvent,
    maybe_generate_event,
    apply_event,
    check_spontaneous_inspiration,
)


class CivilizationModel(mesa.Model):
    """
    The world of the civilization simulation.

    Parameters
    ----------
    config : dict
        Loaded from config/default.yaml (or any override config).
    """

    def __init__(self, config: dict):
        super().__init__(rng=config["simulation"].get("seed", None))
        self.config = config

        # Group registry: group_id -> Group
        self.groups: dict[int, Group] = {}
        self._next_group_id: int = 0

        # Recent Unknown Player events (last tick); agents read this in contemplate
        self.recent_unknown_events: list[UnknownPlayerEvent] = []

        # Event log for analysis
        self.event_log: list[dict] = []

        # Agents index by unique_id for O(1) lookup
        self.agents_by_id: dict[int, Player] = {}

        # Spawn initial population
        self._spawn_initial_population()

        # Data collector (initialized after agents exist)
        from analysis.collectors import make_data_collector
        self.datacollector = make_data_collector()
        self.datacollector.collect(self)

    # ------------------------------------------------------------------
    # Main step
    # ------------------------------------------------------------------

    def step(self) -> None:
        # 1. Unknown Player event
        self.recent_unknown_events = []
        event = maybe_generate_event(self)
        if event:
            apply_event(self, event)
            self.recent_unknown_events.append(event)
            self.event_log.append({
                "tick": self.steps,
                "type": event.event_type,
                "magnitude": event.magnitude,
                "resource_delta": event.resource_delta,
            })

        # 2. Step all living agents
        living = [a for a in self.agents if a.alive]
        self.random.shuffle(living)
        for agent in living:
            agent.step()

        # 3. Trait drift
        drift_cfg = self.config["drift"]
        for agent in self.agents:
            if agent.alive:
                agent.apply_drift(
                    rate=drift_cfg["rate"],
                    max_deviation=drift_cfg["max_deviation"],
                )

        # 4. Spontaneous inspiration
        check_spontaneous_inspiration(self)

        # 5. Group dynamics
        self._update_groups()

        # 6. Social technology emergence
        self._check_tech_emergence()

        # 7. Reproduction
        self._process_reproduction()

        # 8. Remove dead agents and clean up
        self._reap_dead()

        # 9. Collect data
        self.datacollector.collect(self)

    # ------------------------------------------------------------------
    # Population management
    # ------------------------------------------------------------------

    def _spawn_initial_population(self) -> None:
        cfg = self.config
        n = cfg["population"]["initial_size"]
        utility_fn = cfg["population"].get("utility_fn", "survival")

        # Flatten trait distributions from config
        dist_cfg = cfg.get("traits", {})
        distributions: dict[str, list] = {}
        for section in dist_cfg.values():
            if isinstance(section, dict):
                for trait, params in section.items():
                    distributions[trait] = params

        for _ in range(n):
            traits = random_traits(distributions, self.rng)
            agent = Player(self, traits, utility_fn=utility_fn)
            self.agents_by_id[agent.unique_id] = agent

    def _process_reproduction(self) -> None:
        cfg = self.config
        max_pop = cfg["population"].get("max_size", 2000)
        living = [a for a in self.agents if a.alive]

        if len(living) >= max_pop:
            return

        willing = [a for a in living if a.can_reproduce()]
        self.random.shuffle(willing)

        # Pair up willing agents
        while len(willing) >= 2:
            parent1 = willing.pop()
            # Prefer a partner from a known relationship
            best_partner = None
            best_strength = -1.0
            for candidate in willing:
                rel = parent1.relationships.get(candidate.unique_id)
                strength = rel.strength if rel else 0.1
                if strength > best_strength:
                    best_strength = strength
                    best_partner = candidate

            if best_partner is None:
                break

            willing.remove(best_partner)

            child = parent1.reproduce_with(best_partner)
            self.agents_by_id[child.unique_id] = child

            # Child inherits one group from each parent (if any)
            for gid in list(parent1.group_ids)[:1]:
                group = self.groups.get(gid)
                if group:
                    group.add_member(child.unique_id)
                    child.group_ids.add(gid)

    def _reap_dead(self) -> None:
        """Remove dead agents from groups and id index."""
        dead = [a for a in self.agents if not a.alive]
        for agent in dead:
            for gid in list(agent.group_ids):
                group = self.groups.get(gid)
                if group:
                    group.remove_member(agent.unique_id)
            self.agents_by_id.pop(agent.unique_id, None)
            self.agents.remove(agent)

        # Dissolve empty groups
        empty = [gid for gid, g in self.groups.items() if g.is_empty()]
        for gid in empty:
            del self.groups[gid]

    # ------------------------------------------------------------------
    # Group dynamics
    # ------------------------------------------------------------------

    def _update_groups(self) -> None:
        """
        Form new groups and update existing ones.

        Two agents form a group when:
          avg(social_desire) x relationship_strength > group_formation_threshold
        OR when neither has any group and both have high social_desire.
        """
        cfg = self.config["social"]
        threshold = cfg["group_formation_threshold"]
        living = [a for a in self.agents if a.alive]

        # Evaluate pairwise relationships for group formation
        for agent in living:
            for other_id, rel in agent.relationships.items():
                other = self.agents_by_id.get(other_id)
                if not other or not other.alive:
                    continue
                avg_social = (
                    agent.current_traits.social_desire + other.current_traits.social_desire
                ) / 2.0
                bond = avg_social * rel.strength
                if bond < threshold:
                    continue

                # Already in the same group?
                shared = agent.group_ids & other.group_ids
                if shared:
                    continue

                # Merge into an existing group or form a new one
                if agent.group_ids:
                    gid = next(iter(agent.group_ids))
                    self.groups[gid].add_member(other_id)
                    other.group_ids.add(gid)
                elif other.group_ids:
                    gid = next(iter(other.group_ids))
                    self.groups[gid].add_member(agent.unique_id)
                    agent.group_ids.add(gid)
                else:
                    gid = self._new_group(agent.unique_id, other_id)

        # Update dominant voices and collective beliefs
        for group in self.groups.values():
            member_agents = [
                self.agents_by_id[aid]
                for aid in group.members
                if aid in self.agents_by_id
            ]
            if not member_agents:
                continue
            group.elect_dominant_voice(self.agents_by_id)
            dominant = self.agents_by_id.get(group.dominant_voice_id)
            group.accumulate_sentiment(dominant, member_agents)
            group.update_collective_beliefs(member_agents)

            # High latent sentiment triggers dominant voice change
            if group.latent_sentiment > 0.8:
                group.elect_dominant_voice(self.agents_by_id)
                group.latent_sentiment = 0.0

    def _new_group(self, *member_ids: int) -> int:
        gid = self._next_group_id
        self._next_group_id += 1
        group = Group(id=gid, members=set(member_ids))
        self.groups[gid] = group
        for aid in member_ids:
            agent = self.agents_by_id.get(aid)
            if agent:
                agent.group_ids.add(gid)
        return gid

    def _check_tech_emergence(self) -> None:
        """
        For each group, check if trait averages meet emergence conditions
        for any social technology not yet active.
        """
        for group in self.groups.values():
            if group.size() < 3:
                continue  # Too small to develop social technology

            member_agents = [
                self.agents_by_id[aid]
                for aid in group.members
                if aid in self.agents_by_id
            ]
            avg = compute_group_avg_traits(member_agents)

            for tech_name, tech in REGISTRY.items():
                if tech_name not in group.social_technologies:
                    if tech.conditions_met(avg):
                        group.activate_technology(tech_name)
                        # Broadcast norm adoption to members
                        norm_label = f"{tech_name}:active"
                        for agent in member_agents:
                            agent.beliefs.accept_norm(norm_label)

    # ------------------------------------------------------------------
    # Reporting helpers (used by DataCollector)
    # ------------------------------------------------------------------

    def living_count(self) -> int:
        return sum(1 for a in self.agents if a.alive)

    def group_count(self) -> int:
        return len(self.groups)

    def avg_trait(self, trait_name: str) -> float:
        living = [a for a in self.agents if a.alive]
        if not living:
            return 0.0
        return float(np.mean([a.current_traits.get(trait_name) for a in living]))

    def attributor_fraction(self) -> float:
        living = [a for a in self.agents if a.alive]
        if not living:
            return 0.0
        return sum(1 for a in living if a.beliefs.orientation == "attributor") / len(living)

    def modeler_fraction(self) -> float:
        living = [a for a in self.agents if a.alive]
        if not living:
            return 0.0
        return sum(1 for a in living if a.beliefs.orientation == "modeler") / len(living)

    def tech_adoption(self, tech_name: str) -> float:
        """Fraction of living agents in a group with this technology active."""
        living = [a for a in self.agents if a.alive]
        if not living:
            return 0.0
        count = sum(
            1 for a in living
            if any(
                self.groups.get(gid) and self.groups[gid].has_technology(tech_name)
                for gid in a.group_ids
            )
        )
        return count / len(living)
