from pandas import DataFrame
import solara
from solara.lab import task
import solara.lab
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np

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
        param, set_param = solara.use_state(_scenario_defaults[p]) # noqa: SH103
        solara.SliderInt(p, value=param, on_value=set_param, **p_args)
        scenario_params.value[p] = param

    # sliders for traits
    for p in [k for k in _scenario_defaults.keys() if k.startswith('traits_')]:
        trait, set_trait = solara.use_state(_scenario_defaults[p]) # noqa: SH103
        scenario_params.value[p] = trait
        TupleSlider(f"{p} (avg, std_dev)", trait, set_trait, x_label='average', y_label='std_dev')


# Helper function: Rolling mean with confidence band
def plot_rolling_mean_with_ci(ax, data, value_col, window=14, alpha=0.1):
    """Plot rolling mean and confidence band for a time series."""
    rolling_mean = data[value_col].rolling(window=window, min_periods=1, center=False).mean()
    rolling_std = data[value_col].rolling(window=window, min_periods=1, center=False).std()

    # Plot rolling mean as dashed line
    ax.plot(data.index, rolling_mean, color='gray', linestyle='--', alpha=0.7,
            label=f'{window}-day rolling mean')

    # Plot confidence band
    ax.fill_between(data.index,
                    rolling_mean - rolling_std,
                    rolling_mean + rolling_std,
                    alpha=alpha, color='steelblue')

    # Keep original data as faint line
    ax.plot(data.index, data[value_col], color='steelblue', alpha=0.3)

# Helper function: Plot trait evolution with rolling mean
def plot_trait_evolution(ax, data_model, trait_name):
    """Plot a single trait with rolling mean and confidence band."""
    trait_col = f"avg_{trait_name}"
    if trait_col not in data_model.columns:
        ax.axis('off')
        ax.set_title(trait_name)
        return

    plot_rolling_mean_with_ci(ax, data_model, trait_col, window=14, alpha=0.1)


# Helper function: Plot stacked area for belief orientations
def plot_belief_orientations_stacked(ax, data_model):
    """Stacked area chart for attributor/modeler/indifferent fractions."""
    attributors = data_model['attributors']
    modelers = data_model['modelers']
    indifferent = 1 - attributors - modelers

    ax.stackplot(
        data_model.index,
        attributors*100,
        modelers*100,
        indifferent*100,
        labels=['Attributor', 'Modeler', 'Indifferent'],
        colors=['#3498db', '#9b59b6', '#95a5a6'],
        alpha=0.8
    )

    ax.set_xlabel('Tick')
    ax.set_ylabel('Percentage (%)')
    ax.set_title('Belief Orientation Distribution Over Time')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)


# Helper function: Plot social technology adoption
def plot_tech_adoption(ax, data_model, tech_cols):
    """Plot social technology adoption rates over time."""

    for tech in tech_cols:
        # Handle boolean values (0/1) properly
        ax.plot(data_model.index, data_model[tech],
                label=tech.replace('tech_', ''), linewidth=2.5)

    ax.set_xlabel('Tick')
    ax.set_ylabel('Adoption Rate')
    ax.set_title('Social Technology Adoption Over Time')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)


# Helper function: Plot empathy histogram
def plot_empathy_distribution(ax, data_agents):
    """Plot empathy distribution across all agents."""
    sns.histplot(data_agents['empathy'], bins=15, ax=ax, kde=True, edgecolor='black', alpha=0.8)
    ax.set_xlabel('Empathy')
    ax.set_ylabel('Count')
    ax.set_title('Empathy Distribution (All Agents)')
    ax.grid(True, alpha=0.3)


# Helper function: Plot trait box plot
def plot_trait_boxplot(ax, data_agents, trait_cols):
    """Box plot for all 16 traits."""
    sns.boxenplot(data=data_agents[trait_cols], ax=ax, orient='v')
    ax.set_title('Trait Distribution (All Agents)')
    ax.grid(True, alpha=0.3)


# Helper function: Annotate events on chart
def annotate_events(ax, events: DataFrame, y_max=1.0):
    """Add vertical lines for Unknown Player events."""
    color_map = {
        "drought": "#e74c3c",       # red
        "flood": "#3498db",         # blue
        "windfall": "#27ae60",      # green
        "disease": "#e67e22",       # orange
        "discovery": "#9b59b6",     # purple
        "war": "#c0392b",           # dark red
        "plague": "#d35400",        # burnt orange
        "migration": "#8e44ad",     # dark purple
    }

    for event in events.itertuples():
        tick = event[1] # 'tick'
        event_type = event[2] # 'type'
        color = color_map.get(event_type, "gray")

        # Add vertical line
        ax.axvline(x=tick, color=color, linestyle='--', alpha=0.7, linewidth=1.5)

        # Optionally add text label at top
        ax.text(tick, y_max + 0.02, f'{event_type}',
                color=color, fontsize=8, ha='center', fontweight='bold')


# Helper function: Create event markers DataFrame
def get_event_tick_series(model):
    """Get a DataFrame of ticks where events occurred."""
    if not model.event_log:
        return DataFrame(columns=['tick'])

    return DataFrame(model.event_log).copy()


# Helper function: Plot population with event markers
def plot_population_with_events(ax, data_model, events):
    """Plot population with event markers."""
    ax.plot(data_model.index, data_model['population'], color='steelblue', linewidth=2)
    ax.plot(data_model.index, data_model['groups'], color='darkorange',
            linestyle='--', linewidth=2, label='Groups')

    ax.set_xlabel('Tick')
    ax.set_ylabel('Count')
    ax.set_title('Population and Groups Over Time')
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)

    # Annotate events
    if len(events) > 0:
        annotate_events(ax, events, y_max=1.0)


# Helper function: Plot correlation heatmap
def plot_trait_correlation_heatmap(ax, data_model, trait_cols):
    """Show Pearson correlation matrix at endgame (last tick)."""
    if len(data_model) < 2:
        ax.text(0.5, 0.5, 'Not enough data for correlation',
                ha='center', va='center', transform=ax.transAxes)
        return

    # Get endgame snapshot
    endgame_data = data_model[trait_cols].iloc[-1:].copy()

    # Compute correlation
    corr = endgame_data.corr()

    # Create masked array for diagonal (hide self-correlation)
    mask = np.zeros_like(corr.values, dtype=bool)
    np.fill_diagonal(mask, True)

    sns.heatmap(
        corr,
        mask=mask,
        annot=True,
        fmt='.2f',
        cmap='RdYlBu_r',
        cbar_kws={'shrink': 0.7},
        ax=ax,
        square=True
    )

    ax.set_title('Trait Correlations at Endgame')
    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)


# Helper function: Plot empathy distribution
def plot_empathy_density(ax, data_agents):
    """Density plot for empathy distribution."""
    sns.kdeplot(data_agents['empathy'], ax=ax, shade=True, alpha=0.7, label='Empathy')
    ax.set_xlabel('Empathy')
    ax.set_ylabel('Density')
    ax.set_title('Empathy Density')
    ax.grid(True, alpha=0.3)


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
    """Create comprehensive charts from agent and model data.

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
                    solara.Markdown(f"#Endgame Reached: {model.value._endgame_condition_met or "False"}")

                for run_id, data in run_history.value.items():
                    with solara.lab.Tab(f"Run {run_id}", icon_name="mdi-chart-line"):
                        with solara.lab.Tabs(vertical=True):
                            with solara.lab.Tab("Charts", icon_name="mdi-chart-scatter"):
                                create_finished_civilization_charts(data['agents'], data['model'])
                            with solara.lab.Tab("Model", icon_name="mdi-account"):
                                solara.DataFrame(data['model'])

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
