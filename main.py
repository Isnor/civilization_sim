"""
Entry point for the civilization simulation.

Usage:
    python main.py
    python main.py --config config/default.yaml --ticks 500
    python main.py --config config/default.yaml --ticks 200 --seed 123
    python main.py --config config/default.yaml --utility enlightenment

Arguments:
    --config    Path to YAML config file (default: config/default.yaml)
    --ticks     Number of simulation ticks (overrides config)
    --seed      RNG seed (overrides config; 0 = random)
    --utility   Utility function: survival | enlightenment (overrides config)
    --output    Output directory (overrides config)
    --quiet     Suppress per-tick progress output
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import yaml

from simulation.model import CivilizationModel
from analysis.collectors import export_csvs, export_events
from simulation.scenario import CivilizationScenario


def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def apply_overrides(config: dict, args: argparse.Namespace) -> dict:
    if args.ticks is not None:
        config["endgames_max_steps"] = args.ticks
    if args.seed is not None:
        config["rng"] = args.seed if args.seed != 0 else None
    if args.utility is not None:
        config["population_utility_fn"] = args.utility
    if args.output is not None:
        config["output_dir"] = args.output
    return config


def run(config: dict, quiet: bool = False) -> CivilizationModel:
    ticks = config["endgames_max_steps"]
    model = CivilizationModel(CivilizationScenario(**config))

    start = time.time()
    for tick in range(ticks):
        model.step()

        if not quiet and (tick % 10 == 0 or tick == ticks - 1):
            pop = model.living_count()
            groups = model.group_count()
            elapsed = time.time() - start
            print(
                f"  tick {tick:>4d}/{ticks}  "
                f"pop={pop:>4d}  groups={groups:>3d}  "
                f"elapsed={elapsed:.1f}s",
                end="\r",
                flush=True,
            )

        if not model.running:
            if not quiet:
                print(f"\n  [!] Simulation finished: {model._endgame_condition_met}.")
            break

    if not quiet:
        print()  # newline after \r progress

    return model


def summarize(model: CivilizationModel) -> None:
    pop = model.living_count()
    groups = model.group_count()
    print(f"\n{'='*50}")
    print(f"  Final population : {pop}")
    print(f"  Final groups     : {groups}")

    if pop == 0:
        print("  Civilization collapsed.")
        return

    techs = ["taboo", "religion", "philosophy", "economy", "governance"]
    print(f"\n  Social technology adoption:")
    for tech in techs:
        pct = model.tech_adoption(tech) * 100
        print(f"    {tech:<14} {pct:5.1f}% of population")

    print(f"\n  Belief orientations:")
    print(f"    Attributors    {model.attributor_fraction()*100:5.1f}%")
    print(f"    Modelers       {model.modeler_fraction()*100:5.1f}%")
    indiff = (1 - model.attributor_fraction() - model.modeler_fraction()) * 100
    print(f"    Indifferent    {indiff:5.1f}%")

    print(f"\n  Avg traits (final population):")
    for trait in ["aggression", "empathy", "trust", "curiosity", "wonder", "social_desire"]:
        val = model.avg_trait(trait)
        bar = "█" * int(val * 20)
        print(f"    {trait:<20} {val:.3f}  {bar}")
    print(f"{'='*50}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Civilization emergence simulator")
    parser.add_argument("--config", default="config/default.yaml", help="Path to config YAML")
    parser.add_argument("--ticks", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None, help="RNG seed (0=random)")
    parser.add_argument("--utility", choices=["survival", "enlightenment"], default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--write-output", action="store_true")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    config = load_config(str(config_path))
    config = apply_overrides(config, args)

    if not args.quiet:
        print(f"civilization_sim")
        print(f"  config   : {config_path}")
        print(f"  ticks    : {config['endgames_max_steps']}")
        print(f"  pop      : {config['population_initial_size']}")
        print(f"  utility  : {config['population_utility_fn']}")
        print(f"  seed     : {config.get('rng', 'random')}")
        print()

    model = run(config, quiet=args.quiet)

    if not args.quiet:
        summarize(model)

    if args.write_output:
      output_dir = config["output_dir"]
      model_csv, agent_csv = export_csvs(model, output_dir)
      events_csv = export_events(model, output_dir)

      if not args.quiet:
          print(f"\n  Output written to: {output_dir}/")
          print(f"    {model_csv}")
          print(f"    {agent_csv}")
          print(f"    {events_csv}")


if __name__ == "__main__":
    main()
