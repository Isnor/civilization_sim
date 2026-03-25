"""
Unknown Player events and spontaneous inspiration.

The Unknown Player is not an actor — it generates no intentional outputs.
This module produces random events that agents will interpret according to
their beliefs. The simulation doesn't need to explain the events; the agents do.

UnknownPlayerEvent: a random occurrence agents may attribute to the Unknown Player.
  - Has a type (drought, flood, windfall, disease, discovery)
  - Has a resource effect applied to all living agents
  - Has no "intent" — but agents with high wonder/reverence will form beliefs

Spontaneous inspiration is handled here as a global check: each tick, each
living agent has a small probability of receiving an inspiration event that
mutates their base_traits.
"""

from __future__ import annotations

from dataclasses import dataclass


EVENT_TYPES = ["drought", "flood", "windfall", "disease", "discovery"]

# Resource effect per event type: multiplier applied to all agents' resources
EVENT_RESOURCE_EFFECTS: dict[str, float] = {
    "drought": -2.0,
    "flood": -1.5,
    "windfall": +2.5,
    "disease": -3.0,
    "discovery": +1.0,
}


@dataclass
class UnknownPlayerEvent:
    """
    A single Unknown Player event.

    tick:          simulation tick when the event occurred
    event_type:    category of the event
    magnitude:     scales the resource effect (drawn from [0.5, 1.5])
    resource_delta: actual resource effect (magnitude × base_effect)
    description:   human-readable label for logs
    """

    tick: int
    event_type: str
    magnitude: float
    resource_delta: float

    @property
    def description(self) -> str:
        direction = "+" if self.resource_delta >= 0 else ""
        return f"{self.event_type} (Δresources {direction}{self.resource_delta:.2f})"


def maybe_generate_event(model) -> UnknownPlayerEvent | None:
    """
    Randomly generate a single Unknown Player event for this tick.

    Returns an event or None based on configured probability.
    """
    cfg = model.config["unknown_player"]
    if model.rng.random() > cfg["event_probability"]:
        return None

    available = cfg.get("event_types", EVENT_TYPES)
    event_type = str(model.rng.choice(available))
    magnitude = float(model.rng.uniform(0.5, 1.5))
    base_effect = EVENT_RESOURCE_EFFECTS.get(event_type, 0.0)
    resource_delta = base_effect * magnitude

    return UnknownPlayerEvent(
        tick=model.steps,
        event_type=event_type,
        magnitude=magnitude,
        resource_delta=resource_delta,
    )


def apply_event(model, event: UnknownPlayerEvent) -> None:
    """
    Apply the resource effect of an Unknown Player event to all living agents.
    Agents with low resources are more severely impacted by negative events.
    """
    for agent in model.agents:
        if not agent.alive:
            continue
        delta = event.resource_delta
        # Disease hits harder if agent is low on resources (weakened)
        if event.event_type == "disease" and agent.resources < 5.0:
            delta *= 1.5
        agent.resources = max(agent.resources + delta, 0.0)


def check_spontaneous_inspiration(model) -> list[int]:
    """
    Check each living agent for a spontaneous inspiration event.

    Returns a list of agent unique_ids that received inspiration this tick.
    Base probability from config, modified by:
      - agent's curiosity and wonder traits
      - active philosophy social technology (multiplier)
    """
    cfg = model.config
    base_prob = cfg["inspiration"]["probability"]
    inspired_ids = []

    for agent in model.agents:
        if not agent.alive:
            continue

        # Per-agent probability: base × trait amplifiers × philosophy multiplier
        t = agent.current_traits
        trait_mult = 1.0 + t.curiosity * 0.5 + t.wonder * 0.3

        effects = agent._get_active_effects()
        tech_mult = effects.get("inspiration_probability_mult", 1.0)

        prob = base_prob * trait_mult * tech_mult
        if model.rng.random() < prob:
            magnitude = float(model.rng.uniform(0.05, 0.20))
            agent.apply_inspiration(magnitude, model.rng)
            inspired_ids.append(agent.unique_id)

    return inspired_ids
