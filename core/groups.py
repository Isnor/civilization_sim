"""
Groups (tribes, coalitions) emerge when agents with sufficient social_desire
build strong enough relationships with each other.

Groups are not Mesa agents — they are data structures managed by the Model.
The Model is responsible for creating, updating, and dissolving groups.

Key concepts:
  - RelationshipState: tracks the bond between two specific agents
  - Group: an emergent coalition with a dominant voice and active social technologies
  - Dominant voice: the group member with highest dominance trait; their utility
    function shapes the group's collective behavior
  - Latent sentiment: accumulated tension between individual and group utility;
    high tension can trigger a dominant voice change or group fracture
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


@dataclass
class RelationshipState:
    """
    The state of a directed relationship from agent A to agent B.

    trust:             how much A trusts B's intentions (0-1)
    affinity:          how much A likes/values B (0-1)
    interaction_count: total number of interactions
    positive_count:    number of cooperative/positive interactions
    negative_count:    number of competitive/hostile interactions
    """

    trust: float = 0.3
    affinity: float = 0.3
    interaction_count: int = 0
    positive_count: int = 0
    negative_count: int = 0

    def update(self, outcome: str, empathy: float) -> None:
        """
        Update relationship after an interaction.

        outcome: "cooperative", "hostile", "neutral", "trade", "belief_shared"
        empathy: the receiver's empathy trait (amplifies positive, dampens negative)
        """
        self.interaction_count += 1
        if outcome in ("cooperative", "trade", "belief_shared"):
            self.positive_count += 1
            delta_trust = 0.05 + empathy * 0.05
            delta_affinity = 0.05 + empathy * 0.03
            self.trust = min(self.trust + delta_trust, 1.0)
            self.affinity = min(self.affinity + delta_affinity, 1.0)
        elif outcome == "hostile":
            self.negative_count += 1
            delta_trust = -(0.1 - empathy * 0.05)
            delta_affinity = -(0.08 - empathy * 0.03)
            self.trust = max(self.trust + delta_trust, 0.0)
            self.affinity = max(self.affinity + delta_affinity, 0.0)
        # neutral does not change trust/affinity but increments count

    @property
    def strength(self) -> float:
        """Combined bond strength used for group formation threshold."""
        return (self.trust + self.affinity) / 2.0


@dataclass
class Group:
    """
    An emergent social coalition.

    Members are identified by their Mesa unique_id.
    social_technologies: set of technology names currently active (see social_tech.py).
    collective_beliefs: aggregated belief stats across members (lazily updated by Model).
    latent_sentiment: 0 = group utility aligns with individual utility;
                      1 = maximum tension; triggers restructuring at threshold.
    tech_tick: last tick when social technology emergence was evaluated.
    """

    id: int
    members: set[int] = field(default_factory=set)
    dominant_voice_id: int | None = None
    social_technologies: set[str] = field(default_factory=set)
    collective_beliefs: dict = field(default_factory=dict)
    latent_sentiment: float = 0.0
    tech_tick: int = 0

    def add_member(self, agent_id: int) -> None:
        self.members.add(agent_id)

    def remove_member(self, agent_id: int) -> None:
        self.members.discard(agent_id)
        if self.dominant_voice_id == agent_id:
            self.dominant_voice_id = None

    def size(self) -> int:
        return len(self.members)

    def is_empty(self) -> bool:
        return len(self.members) == 0

    def has_technology(self, tech: str) -> bool:
        return tech in self.social_technologies

    def activate_technology(self, tech: str) -> None:
        self.social_technologies.add(tech)

    def elect_dominant_voice(self, agents_by_id: dict) -> None:
        """
        Set dominant_voice_id to the living member with the highest dominance trait.
        Ties broken by unique_id.
        """
        best_id = None
        best_dominance = -1.0
        for aid in self.members:
            agent = agents_by_id.get(aid)
            if agent is None:
                continue
            d = agent.current_traits.dominance
            if d > best_dominance or (d == best_dominance and (best_id is None or aid < best_id)):
                best_dominance = d
                best_id = aid
        self.dominant_voice_id = best_id

    def accumulate_sentiment(self, dominant_agent, member_agents: list) -> None:
        """
        Increase latent_sentiment when dominant voice utility diverges from members'.

        Approximation: compare dominant agent's aggression/dominance to group mean.
        High dominance + aggression in leader while members have high empathy = tension.
        """
        if dominant_agent is None or not member_agents:
            return
        leader_score = (
            dominant_agent.current_traits.dominance
            + dominant_agent.current_traits.aggression
        ) / 2.0
        member_empathy = sum(a.current_traits.empathy for a in member_agents) / len(member_agents)
        tension = max(0.0, leader_score - member_empathy)
        self.latent_sentiment = min(self.latent_sentiment + tension * 0.01, 1.0)

    def update_collective_beliefs(self, member_agents: list) -> None:
        """Aggregate orientation counts across members."""
        counts = {"attributor": 0, "modeler": 0, "indifferent": 0}
        for a in member_agents:
            counts[a.beliefs.orientation] += 1
        self.collective_beliefs = counts
