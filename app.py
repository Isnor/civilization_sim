"""
A Solara app to run and analyze CivilizationSimulation experiments.
"""
import pandas as pd
from pandas import DataFrame
import solara
from solara.lab import task
import solara.lab
import seaborn as sns
import matplotlib.pyplot as plt

from analysis.chart_helpers import (
    plot_belief_orientations_stacked,
    plot_tech_adoption,
    get_event_tick_series,
    plot_population_with_events,
    plot_trait_boxplot,
    plot_trait_distribution
)
from analysis.collectors import _MODEL_TRAIT_REPORTERS
from core.traits import TRAIT_NAMES
from simulation.scenario import CivilizationScenario
from simulation.model import CivilizationModel


@solara.component
def population_summary(m):
    """Summary of the civilization population in its current state
    """

    solara.Markdown(f"#Current Groups: {m.value.group_count()}")
    solara.Markdown(f"#Alive: {m.value.living_count()}")


@solara.component
def attribution_average_summary(m):
    """Summary of the civilization's "attribution" percentages.
    """
    attributor_fraction = 100 * m.attributor_fraction()
    modeler_fraction = 100 * m.modeler_fraction()
    indifferent_fraction = 100 - attributor_fraction - modeler_fraction

    # TODO: unfortunately this does not work; we will need to create solara reactive
    # variables for everything we want to chart from `model` because as it is, this
    # creates a new Figure every time the model gets updated, which is a lot. The
    # other charts work by capturing the result dataframes as reactive variables,
    # which do not change.
    fig, axs = plt.subplots(1, 1, figsize=(4, 4))
    axs.pie(
        x=[attributor_fraction, modeler_fraction, indifferent_fraction],
        labels=["attributors", "modelers", "indifferent"],
        autopct='%.0f%%',
    )
    fig.tight_layout()
    solara.FigureMatplotlib(fig)


@solara.component
def tuple_slider(label:str, value:tuple[float, float], on_change, **kwargs):
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
_scenario_defaults = {
    k: v for k, v in scenario.value.to_dict().items()
    if k not in ['rng', 'model', '_scenario_id']
}

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


#
@solara.component
def scenario_ui():
    """
    ScenarioUI creates rows of sliders and other input UI components to
    configure the Scenario for the model before it runs.
    """
    solara.Select(
        "Utility Function",
        values=["survival", "enlightenment"],
        on_value=lambda x: scenario_params.value.update({'population_utility_fn': x})
    )

    for p, p_args in scene_slider_args.items():
        param, set_param = solara.use_state(_scenario_defaults[p])  # noqa: SH103
        solara.SliderInt(p, value=param, on_value=set_param, **p_args)
        scenario_params.value[p] = param

    # sliders for traits
    for p in [k for k in _scenario_defaults.keys() if k.startswith('traits_')]:
        trait, set_trait = solara.use_state(_scenario_defaults[p])  # noqa: SH103
        scenario_params.value[p] = trait
        tuple_slider(f"{p} (avg, std_dev)", trait, set_trait, x_label='average', y_label='std_dev')


@solara.component
def create_trait_charts(data_model:DataFrame, data_agents: DataFrame):
    """Creates charts based on trait data of the model and agents"""
    fig, axs = plt.subplots(2, 1, figsize=(16, 16))
    axs = axs.flatten()

    ax = sns.lineplot(
        data=data_model[[f'avg_{r}' for r in _MODEL_TRAIT_REPORTERS]],
        ax=axs[0],
        linewidth=1.5,
        alpha=0.6
    )
    ax.set_xlabel('Tick')
    ax.set_ylabel('Average Trait Value')
    ax.set_title('Trait Evolution Over Time')
    ax.legend(loc='best', bbox_to_anchor=(1.05, 1), ncol=2)
    ax.grid(True, alpha=0.3)

    plot_trait_boxplot(axs[1], data_agents, TRAIT_NAMES)

    # these take a lot of CPU/memory
    # sns.kdeplot(data_agents, ax=axs[0], x="trust", y="empathy")
    # sns.kdeplot(data_agents, ax=axs[0], x="wonder", y="reverence")
    fig.tight_layout()
    solara.FigureMatplotlib(fig, dependencies=[data_agents, data_model])


@solara.component
def create_trait_histograms(data_agents: DataFrame):
    """Creates histograms based on trait data of the agents"""
    fig, axs = plt.subplots(4, 4, figsize=(16, 16))
    fig.suptitle('Trait Distributions - All Agents', fontsize=16, y=1.0)

    axs = axs.flatten()

    for i in TRAIT_NAMES:
        ax = axs[i]
        plot_trait_distribution(ax=ax, data_agents=data_agents, trait=i)

    fig.tight_layout()
    solara.FigureMatplotlib(fig)


@solara.component
def create_results_overview_charts(data_agents:DataFrame, data_model:DataFrame):
    """Create simple overview charts from agent and model data and display them in a
    solara.FigureMatplotlib.

    Creates a 4x2 subplot grid with the following charts:
    - Row 0: Population trends (left) + Belief orientation trends (right)
    - Row 1: Social technology adoption (left) + Event timeline (right)
    - Row 2: Trait evolution part 1 (left) + Trait evolution part 2 (right)
    """
    if data_agents is None or data_agents.empty:
        solara.Markdown("#No data to display yet")
        return

    # Get social tech columns and events from model
    tech_cols = [c for c in data_model.columns if c.startswith('tech_')]
    events = get_event_tick_series(model.value)

    # Create a 2x2 subplot grid
    charts, axes = plt.subplots(2, 2, figsize=(16, 14))
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
    charts.suptitle('Civilization Simulation Results', fontsize=16, y=1.0)

    plt.tight_layout()
    solara.FigureMatplotlib(charts, dependencies=[data_model, data_agents])


@task
def run_model():
    """Run the model in a coroutine until its end condition is reached
    """
    m = model.value
    m.run_model()
    run_history.value[hash(m.scenario)] = {
        'agents': m.datacollector.get_agent_vars_dataframe(),
        'model': m.datacollector.get_model_vars_dataframe(),
    }
    return m


@task
def stop_model():
    """Stop the running model"""
    model.value.running = False


def reset_model():
    """Resets the scenario and model variables based on the current state of the `scenario_params`
    map.
    """
    scenario.set(CivilizationScenario(**scenario_params.value))
    model.set(CivilizationModel(scenario=scenario.value))


@task
def build_scenario():
    """Build scenario from scenario_params"""
    # Only include known parameters
    param_dict = {k: v for k, v in scenario_params.value.items()
                  if k in _scenario_defaults}
    scenario.set(CivilizationScenario(**param_dict))


@solara.component
def Page():
    """
    Defines the page for the Solara app.
    """
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
        scenario_ui()

    with solara.Column():
        with solara.Row():
            with solara.lab.Tabs(color='primary', dark=True):
                with solara.lab.Tab("New Experiment", icon_name="mdi-beaker-outline"):
                    population_summary(model)
                    # attribution_average_summary(model.value)
                # with solara.lab.Tab("Results", icon_name="mdi-chart-bar"):


                for run_id, data in run_history.value.items():
                    with solara.lab.Tab(f"Run {run_id}", icon_name="mdi-chart-bar"):
                        with solara.lab.Tabs(vertical=True):
                            with solara.lab.Tab("Overview", icon_name="mdi-chart-bar-stacked"):
                                create_results_overview_charts(data['agents'], data['model'])
                            with solara.lab.Tab("Traits", icon_name="mdi-head-flash-outline"):
                                create_trait_charts(data["model"], data["agents"])
                                create_trait_histograms(data["agents"])

                with solara.lab.Tab("Config", icon_name="mdi-code-tags"):
                    solara.Markdown("**Scenario Parameters**")
                    solara.Markdown(f'#Simulation Steps: {scenario.value.endgames_max_steps}')
                    solara.Markdown(f'#Utility Function: {scenario.value.population_utility_fn}')
                    solara.Markdown(f'#Initial Population: {scenario.value.population_initial_size}')
                    solara.Markdown(f'#Max Population: {scenario.value.population_max_size}')
                    solara.Markdown('---')
                    solara.Markdown('**Trait Distributions**')
                    solara.Markdown(f'```{pd.DataFrame.from_dict(scenario_params.value, orient="index").to_string()}```')
