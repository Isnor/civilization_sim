from typing import Any, Dict
import solara

from mesa.visualization import (
    Slider,
    SolaraViz,
    make_plot_component,
)

from simulation.model import CivilizationModel
from simulation.scenario import CivilizationScenario


def population_summary(model):
  """Summary of the civilization population in its current state
  """

  return solara.Markdown(f"#Current Groups: {model.group_count()}\n#Alive: {model.living_count()}")

def attribution_average_summary(model):
    """Summary of the civilization's "attribution" percentages.
    """
    attributor_fraction = 100 * model.attributor_fraction()
    modeler_fraction = 100 * model.modeler_fraction()
    indifferent_fraction = 100 - attributor_fraction - modeler_fraction
    solara.Markdown(f"#Attributors: {attributor_fraction:.2f}%\n#Modelers: {modeler_fraction:.2f}%\n#Indifferent: {indifferent_fraction:.2f}%"),
    return

def make_average_trait_plots(model:CivilizationModel)-> tuple[any, int]:
    """
    Add a basic plot for the average of each trait in the model over time.
    """
    ignore_traits = ["avg_attribution_style", "groups"]
    return [make_plot_component(average_trait_reporter, page=0, backend='altair')
        for average_trait_reporter in model.datacollector.model_reporters if average_trait_reporter not in ignore_traits]

def scenario_UI(scenario: CivilizationScenario)-> Dict[str, Any]:
    model_params_ui: Dict[str, Any] = {}
    attrs_to_ignore = ["rng", "_scenario_id"]
    for config, val in scenario.to_dict().items():
        if config not in attrs_to_ignore and (isinstance(val, (int, float))):
            model_params_ui[config] = Slider(label=config, value=val, max=30*val, min=0, step=val/10)

    return model_params_ui


if __name__ == '__main__':
    model = CivilizationModel()
    scenario_params = scenario_UI(model.scenario)
    page = SolaraViz(
        name='culture sim',
        model=model,
        components=[
            population_summary,
            attribution_average_summary,
            *make_average_trait_plots(model),
        ],
        model_params=scenario_params,
        # TODO: in the far future, it would be neat to run a bunch of tests and create "prefab" experiments
        # in the form of static CivilizationScenario instances that we switch on based on a drop-down
    )
    page