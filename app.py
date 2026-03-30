from typing import Any, Dict
import solara

from mesa.visualization import (
    Slider,
    SolaraViz,
    make_plot_component,
)

from simulation.model import CivilizationModel
from simulation.scenario import CivilizationScenario


def get_group_count(model):
  return solara.Markdown(f"#Current Groups: {model.group_count()}")

def get_living(model):
  return solara.Markdown(f"#Currently alive: {model.living_count()}")

model = CivilizationModel()

def make_average_trait_plots(model:CivilizationModel)-> tuple[any, int]:
    """
    Add a basic plot for the average of each trait in the model over time.
    """
    return [make_plot_component(average_trait_reporter, page=0, backend='altair') for average_trait_reporter in model.datacollector.model_reporters]


def scenario_UI(scenario: CivilizationScenario)-> Dict[str, Any]:
    model_params_ui: Dict[str, Any] = {}
    for config, val in scenario.to_dict().items():
        if config != "rng" and isinstance(val, int):
            model_params_ui[config] = Slider(label=config, value=val, max=10000, min=1, step=10)

    return model_params_ui

if __name__ == '__main__':
    fucking_god_damnit = scenario_UI(model.scenario)
    page = SolaraViz(
        name='culture sim',
        model=model,
        components=[
            get_group_count,
            get_living,
            *make_average_trait_plots(model),
        ],
        model_params=fucking_god_damnit,
        # TODO: in the far future, it would be neat to run a bunch of tests and create "prefab" experiments
        # in the form of static CivilizationScenario instances that we switch on based on a drop-down
        # model_params={
        #     'population_initial_size': Slider("Initial Population", value=100, max=1000, min=10, step=10),
        #     'population_max_size': Slider("Max Population", value=1000, max=10000, min=100, step=10),
        # }
    )
    page
#   this needs to be run with `solara run app.py`