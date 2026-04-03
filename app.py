import time
from typing import Any
import solara

from simulation.scenario import CivilizationScenario
from simulation.model import CivilizationModel
import seaborn as sns
from pprint import pformat
import solara


@solara.component
def population_summary(model):
  """Summary of the civilization population in its current state
  """

  return solara.Markdown(f"#Current Groups: {model.group_count()}\n#Alive: {model.living_count()}")


@solara.component
def attribution_average_summary(model):
    """Summary of the civilization's "attribution" percentages.
    """
    attributor_fraction = 100 * model.attributor_fraction()
    modeler_fraction = 100 * model.modeler_fraction()
    indifferent_fraction = 100 - attributor_fraction - modeler_fraction
    solara.Markdown(f"#Attributors: {attributor_fraction:.2f}%\n#Modelers: {modeler_fraction:.2f}%\n#Indifferent: {indifferent_fraction:.2f}%"),
    return


# @solara.component
# def make_average_trait_plots(model:CivilizationModel)-> tuple[any, int]:
#     """
#     Add a basic plot for the average of each trait in the model over time.
#     """
#     ignore_traits = ["avg_attribution_style", "groups"]
#     return [make_plot_component(average_trait_reporter, page=0, backend='altair')
#         for average_trait_reporter in model.datacollector.model_reporters if average_trait_reporter not in ignore_traits]


@solara.component
def TupleSlider(label, value, on_change, **kwargs):
    x, y = value

    def set_x(new_x):
        on_change((new_x, y))

    def set_y(new_y):
        on_change((x, new_y))

    with solara.Column():
        solara.Markdown(f"**{label}**")

        with solara.Row():
            solara.SliderFloat(
                label=kwargs.get("x_label", "x"),
                value=x,
                min=kwargs.get("x_min", 0.0),
                max=kwargs.get("x_max", 1.0),
                step=kwargs.get("x_step", 0.01),
                on_value=set_x,
            )
            solara.SliderFloat(
                label=kwargs.get("y_label", "y"),
                value=y,
                min=kwargs.get("y_min", 0.0),
                max=kwargs.get("y_max", 1.0),
                step=kwargs.get("y_step", 0.01),
                on_value=set_y,
            )


scenario = solara.reactive(CivilizationScenario())
model = solara.reactive(CivilizationModel(scenario=scenario.value))
_scenario_defaults = scenario.value.to_dict()
scenario_params = solara.reactive(_scenario_defaults)

# we're going to try to make a component for the scenario controls
@solara.component
def ScenarioUI():
    for p in ["population_initial_size", "population_max_size", "resources_initial"]:
        param, set_param = solara.use_state(_scenario_defaults[p]) # noqa: SH103
        # int_sliders[p] = (param, set_param)
        solara.SliderInt(p, value=param, on_value=set_param)
        scenario_params.value[p] = param

    for p in [k for k in _scenario_defaults.keys() if k.startswith('traits_')]:
        aggression, set_aggression = solara.use_state(_scenario_defaults[p]) # noqa: SH103
        scenario_params.value[p] = aggression
        TupleSlider(f"{p} (avg, std_dev)", aggression, set_aggression, x_label='average', y_label='std_dev')


@solara.component
def Page():
    steps, set_steps = solara.use_state(0)

    def reset_model():
        set_steps(0)
        scenario.set(CivilizationScenario(**scenario_params.value))
        model.set(CivilizationModel(scenario=scenario.value))

    with solara.Sidebar():

        solara.Button(
            "Step",
            on_click=lambda: (
                model.value.step(),
                set_steps(model.value.steps + 1),
            ),
        )

        solara.Button("Reset", on_click=reset_model)

        ScenarioUI()
        # running model in background slightly more difficult than it seems
        # solara.Button(
        #     "Step 100",
        #     on_click=lambda: (
        #         [model.value.step() and time.sleep(1) for i in range(0, 100)]
        #     ),
        # )
    with solara.Column():
        with solara.Row():
            solara.Markdown(f"#Steps: {steps}")
            population_summary(model.value)
            attribution_average_summary(model.value)
            with solara.Card("config"):
                solara.Markdown(pformat(scenario_params.value, indent=2, width=40, sort_dicts=True))
        with solara.Row():
            solara.CrossFilterDataFrame(model.value.datacollector.get_model_vars_dataframe())
        with solara.Row():
            agent_data = model.value.datacollector.get_agent_vars_dataframe()
            f = sns.relplot(
                data=agent_data,
                x="age",
                y="empathy",
            )
            solara.FigureMatplotlib(f, dependencies=agent_data)
            solara.DataFrame(agent_data)
        with solara.Row():
            solara.Markdown("#Spacing")