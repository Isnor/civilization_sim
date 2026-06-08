from pandas import DataFrame
import solara
from solara.lab import task
import solara.lab
import seaborn as sns
import matplotlib.pyplot as plt

from analysis.chart_helpers import plot_belief_orientations_stacked, plot_tech_adoption, get_event_tick_series, plot_population_with_events, plot_trait_boxplot
from simulation.scenario import CivilizationScenario
from simulation.model import CivilizationModel


@solara.component
def population_summary(model):
    """Summary of the civilization population in its current state
    """

    solara.Markdown(f"#Current Groups: {model.value.group_count()}")
    solara.Markdown(f"#Alive: {model.value.living_count()}")


@solara.component
def attribution_average_summary(model):
    """Summary of the civilization's "attribution" percentages.
    """
    attributor_fraction = 100 * model.attributor_fraction()
    modeler_fraction = 100 * model.modeler_fraction()
    indifferent_fraction = 100 - attributor_fraction - modeler_fraction
    solara.Markdown(f"#Attributors: {attributor_fraction:.2f}%")
    solara.Markdown(f"#Modelers: {modeler_fraction:.2f}%")
    solara.Markdown(f"#Indifferent: {indifferent_fraction:.2f}%")
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
        param, set_param = solara.use_state(_scenario_defaults[p])  # noqa: SH103
        solara.SliderInt(p, value=param, on_value=set_param, **p_args)
        scenario_params.value[p] = param

    # sliders for traits
    for p in [k for k in _scenario_defaults.keys() if k.startswith('traits_')]:
        trait, set_trait = solara.use_state(_scenario_defaults[p])  # noqa: SH103
        scenario_params.value[p] = trait
        TupleSlider(f"{p} (avg, std_dev)", trait, set_trait, x_label='average', y_label='std_dev')


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
def create_finished_civilization_charts(data_agents:DataFrame, data_model:DataFrame):
    """Create comprehensive charts from agent and model data and display them in a solara.FigureMatplotlib.

    Creates a 4x2 subplot grid with the following charts:
    - Row 0: Population trends (left) + Belief orientation trends (right)
    - Row 1: Social technology adoption (left) + Event timeline (right)
    - Row 2: Trait evolution part 1 (left) + Trait evolution part 2 (right)
    - Row 3: Empathy histogram (left) + Trait box plot (right)
    """
    if data_agents is None or data_agents.empty:
        return solara.Markdown("#No data to display yet")

    # Get social tech columns and events from model
    tech_cols = [c for c in data_model.columns if c.startswith('tech_')]
    events = get_event_tick_series(model.value)

    # Get all trait columns from model (avg_* columns)
    trait_cols = [c for c in data_model.columns if c.startswith('avg_')]

    # Create a 2x2 subplot grid
    firstFewCharts, axes = plt.subplots(2, 2, figsize=(16, 14))
    axes = axes.flatten()

    # Row 0: Population trends (left) + Belief orientation trends (right)
    plot_population_with_events(axes[0], data_model, events)

    plot_belief_orientations_stacked(axes[1], data_model)
    # Row 1: Social technology adoption (left) + Event timeline (right)
    plot_tech_adoption(axes[2], data_model, tech_cols)

    # Event timeline - vertical markers for each event
    event_ticks = events['tick'].tolist() if len(events) > 0 else []
    colors = ['#e74c3c', '#3498db', '#27ae60', '#e67e22', '#9b59b6']

    for i, tick in enumerate(event_ticks):
        color = colors[i % len(colors)]
        # Add event marker
        axes[3].scatter(tick, 0.5, color=color, marker='o', s=60, zorder=3, alpha=0.8)
        # Add vertical line extending up from event
        axes[3].axvline(x=tick, color=color, linestyle=':', alpha=0.5, linewidth=1)

    axes[3].set_ylim(-0.1, 1.0)
    axes[3].set_yticks([])
    axes[3].set_xlabel('Tick')
    axes[3].set_title('Events Timeline')
    axes[3].grid(True, alpha=0.3)

    # Add overall figure title
    firstFewCharts.suptitle('Civilization Simulation Results', fontsize=16, y=1.0)

    solara.FigureMatplotlib(firstFewCharts, dependencies=[data_model, data_agents])

    secondFewCharts, secondChartAxes = plt.subplots(2, 1, figsize=(20, 10))
    secondChartAxes = secondChartAxes.flatten()

    ax = sns.lineplot(data=data_model[trait_cols], ax=secondChartAxes[0], linewidth=1.5, alpha=0.6)
    ax.set_xlabel('Tick')
    ax.set_ylabel('Trait Value')
    ax.set_title('Trait Evolution Over Time')
    ax.legend(loc='best', bbox_to_anchor=(1.05, 1), ncol=2)
    ax.grid(True, alpha=0.3)
    trait_cols_full = [
        "curiosity", "pattern_recognition", "abstraction", "memory_narrative",
        "social_desire", "dominance", "empathy", "trust", "conformity",
        "risk_tolerance", "aggression", "industriousness", "patience",
        "wonder", "attribution_style", "reverence"
    ]

    plot_trait_boxplot(secondChartAxes[1], data_agents, trait_cols_full)
    plt.xticks(rotation=90)

    plt.tight_layout()
    solara.FigureMatplotlib(secondFewCharts, dependencies=[data_model, data_agents])


@task
def build_scenario():
    """Build scenario from scenario_params"""
    # Only include known parameters
    param_dict = {k: v for k, v in scenario_params.value.items()
                  if k in _scenario_defaults}
    scenario.set(CivilizationScenario(**param_dict))


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
                    solara.Markdown(f"#Endgame Reached: {model.value._endgame_condition_met or 'False'}")

                for run_id, data in run_history.value.items():
                    with solara.lab.Tab(f"Run {run_id}", icon_name="mdi-beaker-outline"):
                        with solara.lab.Tabs(vertical=True):
                            with solara.lab.Tab("Overview", icon_name="mdi-chart-bar-stacked"):
                                create_finished_civilization_charts(data['agents'], data['model'])

                with solara.lab.Tab("Config", icon_name="mdi-code-tags"):
                    solara.Markdown(f"**Scenario Parameters**")
                    solara.Markdown(f'#Simulation Steps: {scenario.value.endgames_max_steps}')
                    solara.Markdown(f'#Utility Function: {scenario.value.population_utility_fn}')
                    solara.Markdown(f'#Initial Population: {scenario.value.population_initial_size}')
                    solara.Markdown(f'#Max Population: {scenario.value.population_max_size}')
                    solara.Markdown(f'#Seed: {scenario.value.rng}')
                    solara.Markdown(f'---')
                    solara.Markdown(f'**Trait Distributions**')
                    import pandas as pd
                    solara.Markdown(f'```{pd.DataFrame.from_dict(scenario_params.value, orient="index").to_string()}```')
        with solara.Row():
            solara.Markdown("#Spacing")
