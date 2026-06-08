from pandas import DataFrame
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

