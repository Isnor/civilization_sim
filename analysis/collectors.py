"""
Data collection and CSV export.

make_data_collector() returns a configured Mesa DataCollector that records:
  - Model-level: population, group count, belief orientation fractions,
    social technology adoption, average trait values for key traits
  - Agent-level: unique_id, age, resources, last_action, metagame,
    belief orientation, and the full current_traits vector

export_csvs() writes both model and agent dataframes to the output directory.
"""

from __future__ import annotations

import os

import mesa


# Key traits to track at the model level (population averages)
_MODEL_TRAIT_REPORTERS = [
    "curiosity",
    "abstraction",
    "social_desire",
    "empathy",
    "trust",
    "aggression",
    "patience",
    "wonder",
    "attribution_style",
    "reverence",
]

# Social technologies to track adoption for
_TECH_REPORTERS = ["taboo", "religion", "philosophy", "economy", "governance"]


def make_data_collector() -> mesa.DataCollector:
    model_reporters: dict = {
        "population": lambda m: m.living_count(),
        "groups": lambda m: m.group_count(),
        "attributors": lambda m: m.attributor_fraction(),
        "modelers": lambda m: m.modeler_fraction(),
    }

    # Average trait reporters
    for trait in _MODEL_TRAIT_REPORTERS:
        model_reporters[f"avg_{trait}"] = _make_trait_reporter(trait)

    # Social technology adoption reporters
    for tech in _TECH_REPORTERS:
        model_reporters[f"tech_{tech}"] = _make_tech_reporter(tech)

    agent_reporters: dict = {
        "age": "age",
        "resources": "resources",
        "last_action": "last_action",
        "metagame": "metagame",
        "belief_orientation": lambda a: a.beliefs.orientation,
        "group_count": lambda a: len(a.group_ids),
        # Full current trait vector
        "curiosity": lambda a: a.current_traits.curiosity,
        "pattern_recognition": lambda a: a.current_traits.pattern_recognition,
        "abstraction": lambda a: a.current_traits.abstraction,
        "memory_narrative": lambda a: a.current_traits.memory_narrative,
        "social_desire": lambda a: a.current_traits.social_desire,
        "dominance": lambda a: a.current_traits.dominance,
        "empathy": lambda a: a.current_traits.empathy,
        "trust": lambda a: a.current_traits.trust,
        "conformity": lambda a: a.current_traits.conformity,
        "risk_tolerance": lambda a: a.current_traits.risk_tolerance,
        "aggression": lambda a: a.current_traits.aggression,
        "industriousness": lambda a: a.current_traits.industriousness,
        "patience": lambda a: a.current_traits.patience,
        "wonder": lambda a: a.current_traits.wonder,
        "attribution_style": lambda a: a.current_traits.attribution_style,
        "reverence": lambda a: a.current_traits.reverence,
    }

    return mesa.DataCollector(
        model_reporters=model_reporters,
        agent_reporters=agent_reporters,
    )


def export_csvs(model, output_dir: str) -> tuple[str, str]:
    """
    Write model and agent data to CSV files.

    Returns (model_csv_path, agent_csv_path).
    """
    os.makedirs(output_dir, exist_ok=True)

    model_df = model.datacollector.get_model_vars_dataframe()
    agent_df = model.datacollector.get_agent_vars_dataframe()

    model_path = os.path.join(output_dir, "model_data.csv")
    agent_path = os.path.join(output_dir, "agent_data.csv")

    model_df.to_csv(model_path)
    agent_df.to_csv(agent_path)

    return model_path, agent_path


def export_events(model, output_dir: str) -> str:
    """Write the Unknown Player event log to CSV."""
    import pandas as pd
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "events.csv")
    if model.event_log:
        pd.DataFrame(model.event_log).to_csv(path, index=False)
    else:
        # Write empty file with headers
        pd.DataFrame(columns=["tick", "type", "magnitude", "resource_delta"]).to_csv(
            path, index=False
        )
    return path


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _make_trait_reporter(trait_name: str):
    def reporter(m):
        return m.avg_trait(trait_name)
    reporter.__name__ = f"avg_{trait_name}"
    return reporter


def _make_tech_reporter(tech_name: str):
    def reporter(m):
        return m.tech_adoption(tech_name)
    reporter.__name__ = f"tech_{tech_name}"
    return reporter
