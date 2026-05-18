from matplotlib.figure import Figure
from pandas import DataFrame
import solara
from solara.lab import task
import solara.lab
import seaborn as sns
import matplotlib.pyplot as plt

from simulation.scenario import CivilizationScenario
from simulation.model import CivilizationModel
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
def TupleSlider(label:str, value:tuple[float, float], on_change, **kwargs):
    """Slider component for a 2-tuple of floats; displays two sliders side-by-side.
    `kwargs` are passed to `solara.SliderFloat`.
    """
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

# setup the model using a Scenario
scenario = solara.reactive(CivilizationScenario())
model = solara.reactive(CivilizationModel(scenario=scenario.value))

# dictionary of scenario attributes, for setting the initial state and holding the current
# state of the scenario parameters
_scenario_defaults = {k: v for k, v in scenario.value.to_dict().items() if k not in ['rng', 'model', '_scenario_id']}

# state of the scenario
scenario_params = solara.reactive(_scenario_defaults)

# storage of the dataframes from previous runs to display in the tabs of results
run_history = solara.reactive({})

# map of scenario attributes to solara slider arguments
scene_slider_args = {
    'population_initial_size': {
        'min':10,
        'max':250,
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

    # sliders for traits
    for p in [k for k in _scenario_defaults.keys() if k.startswith('traits_')]:
        trait, set_trait = solara.use_state(_scenario_defaults[p]) # noqa: SH103
        scenario_params.value[p] = trait
        TupleSlider(f"{p} (avg, std_dev)", trait, set_trait, x_label='average', y_label='std_dev')


@solara.component
def create_finished_civilization_charts(data_agents:DataFrame, data_model:DataFrame):
    """Create charts from agent and model data.

    Creates some subplots:
    - empathy distribution (every human over all time)
    - Social technology adoption rates
    - trait box plot
    """
    if data_agents is None or data_agents.empty:
        return solara.Markdown("#No data to display yet")

    # Get social tech columns from model (tech_taboo, tech_religion, etc.)
    tech_cols = [c for c in data_model.columns if c.startswith('tech_')]

    # Create the figure
    fig, axes = plt.subplots(3, 1, figsize=(14, 10))
    axes = axes.flatten()

    tech_subset = data_model[tech_cols]
    sns.lineplot(data=tech_subset, ax=axes[0])

    sns.histplot(data_agents['empathy'], bins=10, ax=axes[1], kde=True, edgecolor='black')
    axes[1].set_xlabel('Empathy')
    axes[1].set_ylabel('Count')
    axes[1].set_title('Empathy Distribution')
    axes[1].grid(True, alpha=0.3)

    # commenting for now, but this did work, we just need to pass grid.figure to solara.FigureMatplotlib
    # grid = sns.pairplot(data=data_model, vars=tech_cols, kind='kde')

    sns.boxplot(data=data_agents[[
        "curiosity",
        "pattern_recognition",
        "abstraction",
        "memory_narrative",
        "social_desire",
        "dominance",
        "empathy",
        "trust",
        "conformity",
        "risk_tolerance",
        "aggression",
        "industriousness",
        "patience",
        "wonder",
        "attribution_style",
        "reverence",
    ]], ax=axes[2])

    plt.tight_layout()
    return solara.FigureMatplotlib(fig, dependencies=[data_model, data_agents])


@task
def run_model():
    """Run the model in a coroutine until its end condition is reached
    """
    m = model.value
    m.run_model()
    run_history.value[hash(m.scenario)] = dict(
        agents=m.datacollector.get_agent_vars_dataframe(),
        model=m.datacollector.get_model_vars_dataframe(),
    )
    return m


@task
def stop_model():
    model.value.running = False


def reset_model():
    """Resets the scenario and model variables based on the current state of the `scenario_params` map.
    """
    scenario.set(CivilizationScenario(**scenario_params.value))
    model.set(CivilizationModel(scenario=scenario.value))


@solara.component
def Page():

    with solara.AppBar():
        solara.Button(
            "Init Model",
            on_click=reset_model,
            disabled=run_model.pending,
            icon_name="mdi-restart-alert" if not run_model.pending else "mdi-restart-off"
        )

        solara.Button(
            "Step",
            on_click=model.value.step,
            disabled=run_model.pending,
            icon_name="mdi-debug-step-over"
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
                            with solara.lab.Tab("Charts", icon_name="mdi-chart-scatter"):
                                create_finished_civilization_charts(data['agents'], data['model'])
            with solara.Card("Scenario"):
                solara.Markdown(f'```{pformat(scenario_params.value, indent=2, width=40, sort_dicts=True)}```')
        with solara.Row():
            solara.Markdown("#Spacing")