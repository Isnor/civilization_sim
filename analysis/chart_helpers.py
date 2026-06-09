from pandas import DataFrame
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np


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


# Helper function: Plot histogram of a trait
def plot_trait_distribution(ax, trait, data_agents):
    """Plot distribution of a trait across all agents."""
    sns.histplot(data_agents[trait], bins=7, ax=ax, kde=True, edgecolor='black', alpha=0.8)
    ax.set_xlabel(trait)
    ax.set_ylabel('value')
    ax.set_title(f'{trait} Distribution')
    ax.grid(True, alpha=0.3)


# Helper function: Plot trait box plot
def plot_trait_boxplot(ax, data_agents, trait_cols):
    """Box plot for all 16 traits."""
    sns.boxenplot(data=data_agents[trait_cols], ax=ax, orient='v')
    ax.set_title('Trait Distribution (All Agents)')
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=90)


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
def get_event_tick_series(model_or_path):
    """Get a DataFrame of ticks where events occurred.

    Args:
        model_or_path: Either a model object with event_log, or a path to events.csv
    """
    # Check if it's a string (path to file)
    if isinstance(model_or_path, str):
        # Try to load events from file
        try:
            df = pd.read_csv(model_or_path)
            return df if not df.empty else pd.DataFrame(columns=['tick', 'type', 'magnitude'])
        except FileNotFoundError:
            return pd.DataFrame(columns=['tick', 'type', 'magnitude'])

    # It's a model object - check for event_log
    if not hasattr(model_or_path, 'event_log') or not model_or_path.event_log:
        return pd.DataFrame(columns=['tick', 'type', 'magnitude'])

    # Create DataFrame from event log
    # The event log is a list of tuples/dicts, convert to DataFrame
    events = []
    for event in model_or_path.event_log:
        # Handle different event log formats
        if isinstance(event, dict):
            events.append({
                'tick': event.get('tick', 0),
                'type': event.get('type', 'unknown'),
                'magnitude': event.get('magnitude', 0)
            })
        else:
            events.append({
                'tick': getattr(event, 'tick', 0),
                'type': getattr(event, 'type', 'unknown'),
                'magnitude': getattr(event, 'magnitude', 0)
            })

    return pd.DataFrame(events) if events else pd.DataFrame(columns=['tick', 'type', 'magnitude'])


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


# Helper function: RelPlot for trait evolution over time
def plot_trait_relplot(ax, data_model: DataFrame, trait_cols: list[str],
                       x_col: str = 'step', y_col_prefix: str = 'avg_',
                       hue_order: list[str] | None = None,
                       height: float = 3.0, aspect: float = 1.0) -> plt.Figure:
    """
    Create line plots for multiple traits over time on provided axes.

    Args:
        ax: Matplotlib axes object
        data_model: Model-level DataFrame with trait columns (avg_traitname)
        trait_cols: List of trait column names (e.g., ['avg_curiosity', 'avg_empathy'])
        x_col: Column name for x-axis (default: 'step')
        y_col_prefix: Prefix to strip from column names for legend (default: 'avg_')
        hue_order: Optional order for legend (None for auto)
        height: Height of plot (default: 3.0)
        aspect: Aspect ratio (default: 1.0)

    Returns:
        None (modifies axes in-place)
    """
    # Extract clean trait names from column names
    trait_names = [c.replace(y_col_prefix, '') for c in trait_cols]

    # Plot each trait as a separate line
    for trait_name, col in sorted(zip(trait_names, trait_cols), key=lambda x: x[0]):
        ax.plot(data_model.index, data_model[col], label=trait_name,
                linewidth=1.5, alpha=0.7)

    # Clean up legends and styling
    ax.grid(True, alpha=0.3)
    ax.set_xlabel('Tick')
    ax.set_ylabel('Trait Value')
    ax.legend(loc='best')
    ax.tick_params(axis='x', rotation=45)
    ax.set_title('Trait Evolution Over Time')


# Helper function: PairPlot for trait correlations
def plot_trait_pairplot(ax, data_agents: DataFrame, trait_cols: list[str],
                        hue_col: str | None = None,
                        height: float = 3.0,
                        figsize: tuple[int, int] = (5, 5)):
    """
    Create a pairplot showing pairwise relationships between traits.

    Args:
        ax: Matplotlib axes object or None to create new figure
        data_agents: Agent-level DataFrame with trait columns
        trait_cols: List of trait column names
        hue_col: Optional column to use for hue (e.g., 'metagame')
        height: Height of each facet (default: 3.0)

    Returns:
        matplotlib Figure containing the pairplot
    """
    # Only use hue_col if it exists in the data
    cols = trait_cols
    use_hue = False
    if hue_col and hue_col in data_agents.columns:
        cols = [hue_col] + trait_cols
        use_hue = True

    # Check if ax is provided - if not, create new figure
    if ax is None:
        # Check if hue_col is valid before passing to pairplot
        if use_hue:
            g = sns.pairplot(
                data_agents[cols],
                hue=hue_col,
                height=height,
            )
        else:
            g = sns.pairplot(
                data_agents[trait_cols],
                height=height,
            )

        # Clean up histograms on diagonal
        for ax in g.axes.flatten():
            if isinstance(ax, plt.Axes):
                ax.grid(True, alpha=0.3)

        # Add title
        g.figure.suptitle('Trait Correlations', fontsize=12, y=1.02)
        plt.tight_layout()
        return g.figure

    # If ax is provided, we need to plot individual subplots manually
    # This is more complex with pairplot, so let's create the figure ourselves
    cols_list = cols  # Use the columns list with or without hue
    n_cols = len(cols_list)
    fig, axes = plt.subplots(
        n_cols, n_cols,
        figsize=(n_cols * 2.5, n_cols * 2.5),
        gridspec_kw={'width_ratios': [1] * n_cols}
    )
    axes = axes.flatten()

    # Set up pairplot manually
    for i, col1 in enumerate(cols_list):
        for j, col2 in enumerate(cols_list):
            ax_ij = axes[i * n_cols + j]
            if i == j:
                # Histogram on diagonal
                sns.histplot(
                    data_agents[col1],
                    bins=15,
                    ax=ax_ij,
                    kde=True,
                    edgecolor='black',
                    alpha=0.8
                )
                ax_ij.set_xlabel(col1)
                ax_ij.grid(True, alpha=0.3)
            else:
                # Scatter plot off-diagonal - only use hue if column exists
                scatter_kwargs = {'x': col2, 'y': col1, 'ax': ax_ij, 'alpha': 0.6}
                if use_hue:
                    scatter_kwargs['hue'] = hue_col
                sns.scatterplot(data=data_agents[[col2, col1]], **scatter_kwargs)
                ax_ij.set_xlabel(col2)
                ax_ij.set_ylabel(col1)
                ax_ij.grid(True, alpha=0.3)

    # Clean up empty subplots
    for ax in axes.flat:
        if ax.get_visible():
            ax.grid(True, alpha=0.3)

    fig.suptitle('Trait Correlations', fontsize=12, y=1.02)
    plt.tight_layout()


