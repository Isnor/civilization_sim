import solara
from solara.lab import task
import solara.lab
from simulation.scenario import CivilizationScenario
from simulation.model import CivilizationModel
# import seaborn as sns
from pprint import pformat


@solara.component
def population_summary(model):
  """Summary of the civilization population in its current state
  """

  return solara.Markdown(f"#Current Groups: {model.value.group_count()}\n#Alive: {model.value.living_count()}")


@solara.component
def attribution_average_summary(model):
    """Summary of the civilization's "attribution" percentages.
    """
    attributor_fraction = 100 * model.attributor_fraction()
    modeler_fraction = 100 * model.modeler_fraction()
    indifferent_fraction = 100 - attributor_fraction - modeler_fraction
    solara.Markdown(f"#Attributors: {attributor_fraction:.2f}%\n#Modelers: {modeler_fraction:.2f}%\n#Indifferent: {indifferent_fraction:.2f}%"),
    return


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
_scenario_defaults = {k: v for k, v in scenario.value.to_dict().items() if k not in ['rng', 'model', '_scenario_id']}
scenario_params = solara.reactive(_scenario_defaults)
run_history = solara.reactive({})

# map of scenario attributes to solara slider arguments
scene_slider_args = {
    'population_initial_size': {
        'min':10,
        'max':100,
        'step':10
    },
    'population_max_size': {
        'min':10,
        'max':10000,
        'step':10
    },
}

# we're going to try to make a component for the scenario controls
@solara.component
def ScenarioUI():

    for p, p_args in scene_slider_args.items():
        param, set_param = solara.use_state(_scenario_defaults[p]) # noqa: SH103
        solara.SliderInt(p, value=param, on_value=set_param, **p_args)
        scenario_params.value[p] = param

    for p in [k for k in _scenario_defaults.keys() if k.startswith('traits_')]:
        aggression, set_aggression = solara.use_state(_scenario_defaults[p]) # noqa: SH103
        scenario_params.value[p] = aggression
        TupleSlider(f"{p} (avg, std_dev)", aggression, set_aggression, x_label='average', y_label='std_dev')


@task
def run_model():
    m = model.value
    m.run_model()
    print(f'houston, we have finished a run {m._scenario._scenario_id}')
    run_history.value[m.scenario._scenario_id] = dict(
        agents=m.datacollector.get_agent_vars_dataframe(),
        model=m.datacollector.get_model_vars_dataframe(),
    )
    return m


def stop_model():
    model.value.running = False


@solara.component
def Page():

    def reset_model():
        scenario.set(CivilizationScenario(**scenario_params.value))
        model.set(CivilizationModel(scenario=scenario.value))

    with solara.AppBar():
        solara.Button(
            "Init Model",
            on_click=reset_model,
            disabled=run_model.pending,
            icon_name="mdi-restart-alert" if not run_model.pending else "mdi-restart-off"
        )

        solara.Button(
            "Run Model",
            on_click=run_model,
            disabled=run_model.pending,
            icon_name="mdi-play"
        )

        solara.Button(
            "Stop Model",
            on_click=stop_model,
            disabled=not run_model.pending,
            icon_name="mdi-stop"
        )

    with solara.Row():
            solara.ProgressLinear(run_model.progress if run_model.pending else False)

    with solara.Sidebar():
        solara.Markdown("#Scenario Parameters")
        ScenarioUI()

    with solara.Column():
        with solara.Row():
            with solara.lab.Tabs(color='primary', dark=True):
                with solara.lab.Tab("Results", icon_name="mdi-chart-bar"):
                    solara.Markdown(f"#Steps: {model.value.steps}")
                    population_summary(model)
                    attribution_average_summary(model.value)
                    solara.Markdown(f"#Endgame Reached: {model.value._endgame_condition_met or "False"}")

                for run_id, data in run_history.value.items():
                    with solara.lab.Tab(f"Run {run_id}", icon_name="mdi-chart-line"):
                        with solara.lab.Tabs(vertical=True):
                            with solara.lab.Tab("Model", icon_name="mdi-account"):
                                solara.DataFrame(data['model'])
                            with solara.lab.Tab("Agents", icon_name="mdi-access-point"):
                                solara.DataFrame(data['agents'])
            with solara.Card("config"):
                solara.Markdown(f'```{pformat(scenario_params.value, indent=2, width=40, sort_dicts=True)}```')
        with solara.Row():
            solara.Markdown("#Spacing")