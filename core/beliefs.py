"""
BeliefSystem: an agent's working model of the Unknown Player and the world.

Agents hold beliefs with varying confidence. The attribution_style trait
determines whether an agent interprets unexplained events as intentional
(Attributor), mechanical (Modeler), or ignores them (Indifferent).

Beliefs spread between agents through social interaction, weighted by trust,
conformity, and the relative confidence of the transmitter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


OrientationType = Literal["attributor", "modeler", "indifferent"]


@dataclass
class AttributedEvent:
    """A single unexplained event that an agent has formed a belief about."""
    tick: int
    event_type: str          # e.g. "drought", "windfall", "disease"
    interpretation: str      # free-form label the agent assigned
    confidence: float        # how certain the agent is (0-1)


@dataclass
class BeliefSystem:
    """
    An agent's model of the Unknown Player and causal forces in the world.

    orientation: derived from attribution_style trait at init; can shift
                 through experience or social influence.
    unknown_player_confidence: how strongly this agent believes the Unknown
                               Player is an intentional actor (0=not at all,
                               1=absolute certainty).
    attributed_events: history of unexplained events and how the agent
                       interpreted them.
    shared_norms: set of group norms this agent has accepted (string labels,
                  e.g. "taboo:no_in_group_killing", "religion:offer_sacrifice").
    """

    orientation: OrientationType = "indifferent"
    unknown_player_confidence: float = 0.0
    attributed_events: list[AttributedEvent] = field(default_factory=list)
    shared_norms: set[str] = field(default_factory=set)

    @classmethod
    def from_attribution_style(cls, attribution_style: float) -> BeliefSystem:
        """
        Derive initial orientation and confidence from the attribution_style trait.

          attribution_style < 0.35  → Modeler
          attribution_style > 0.65  → Attributor
          otherwise                 → Indifferent
        """
        if attribution_style < 0.35:
            orientation: OrientationType = "modeler"
            confidence = (0.35 - attribution_style) / 0.35
        elif attribution_style > 0.65:
            orientation = "attributor"
            confidence = (attribution_style - 0.65) / 0.35
        else:
            orientation = "indifferent"
            confidence = 0.0
        return cls(
            orientation=orientation,
            unknown_player_confidence=float(min(confidence, 1.0)),
        )

    def receive_event(
        self,
        tick: int,
        event_type: str,
        wonder: float,
        reverence: float,
        attribution_style: float,
    ) -> None:
        """
        Process an Unknown Player event.

        Agents with high wonder always form some interpretation.
        Modelers record a pattern; Attributors assign intent; Indifferents ignore.
        Reverence amplifies the confidence of Attributors.
        """
        if wonder < 0.2:
            return  # agent doesn't engage with the unexplained

        if self.orientation == "attributor":
            interpretation = f"unknown_player_caused_{event_type}"
            confidence = min(wonder * reverence + attribution_style * 0.3, 1.0)
        elif self.orientation == "modeler":
            interpretation = f"natural_pattern:{event_type}"
            confidence = min(wonder * (1.0 - attribution_style) * 0.5, 1.0)
        else:
            # Indifferent agents may still notice if wonder is very high
            if wonder < 0.6:
                return
            interpretation = f"unexplained:{event_type}"
            confidence = wonder * 0.3

        self.attributed_events.append(
            AttributedEvent(tick, event_type, interpretation, confidence)
        )
        # Repeated similar events reinforce confidence
        similar = sum(1 for e in self.attributed_events if e.event_type == event_type)
        if similar > 1:
            self.unknown_player_confidence = min(
                self.unknown_player_confidence + 0.05 * similar, 1.0
            )

    def receive_belief(
        self,
        other_belief: BeliefSystem,
        trust: float,
        conformity: float,
    ) -> None:
        """
        Social transmission of belief from another agent.

        High conformity + high trust in the other agent nudges this agent's
        orientation toward the transmitter's orientation.
        The transmitter's confidence and the receiver's conformity gate adoption.
        """
        susceptibility = trust * conformity
        if susceptibility < 0.2:
            return

        # Adopt shared norms from the other agent
        for norm in other_belief.shared_norms:
            if susceptibility > 0.5:
                self.shared_norms.add(norm)

        # Nudge orientation toward other's if their confidence is high
        if other_belief.unknown_player_confidence > self.unknown_player_confidence:
            delta = (
                other_belief.unknown_player_confidence - self.unknown_player_confidence
            ) * susceptibility * 0.1
            self.unknown_player_confidence = min(
                self.unknown_player_confidence + delta, 1.0
            )
            # If nudge is strong enough and orientations differ, consider shifting
            if (
                susceptibility > 0.7
                and other_belief.orientation != self.orientation
                and other_belief.unknown_player_confidence > 0.7
            ):
                self.orientation = other_belief.orientation

    def accept_norm(self, norm: str) -> None:
        self.shared_norms.add(norm)

    def has_norm(self, norm: str) -> bool:
        return norm in self.shared_norms
