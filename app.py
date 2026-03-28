import solara
from mesa.visualization import (
	 Slider,
	 SolaraViz,
	 SpaceRenderer,
	 make_plot_component,
)
from mesa.visualization.components import AgentPortrayalStyle
import yaml
from core.agent import Player
from simulation.model import CivilizationModel

def load_config(path: str) -> dict:
	 with open(path) as f:
		  return yaml.safe_load(f)

# write a function for AgentPortrayalStyle, or use a different method
# def agent_portrayal(agent):
#   pass

# write a function to display information from a model of our type (solara.Markdown to display utility function, for example)
def get_group_count(model):
  return solara.Markdown(f"Current # Groups: {model.group_count()}")

def get_living(model):
  return solara.Markdown(f"Currently alive: {model.living_count()}")

config = load_config("./config/default.yaml")
model = CivilizationModel(config)
# renderer = SpaceRenderer(model, backend='altair').agent_mesh # TODO: add agent_portrayal and layer function here, setup structure
# renderer.render()

def make_average_trait_plots(model:CivilizationModel)-> tuple[any, int]:
	return [make_plot_component(average_trait_reporter, page=0, backend='altair') for average_trait_reporter in model.datacollector.model_reporters]

if __name__ == '__main__':
	page = SolaraViz(
		name='culture sim',
		model=model,
		# renderer=renderer,
		components=[
			get_group_count,
			get_living,
			*make_average_trait_plots(model),
			# make_plot_component("avg_trust", page=1, backend='altair'),
			# make_plot_component("avg_empathy", page=1, backend='altair'),

		],
		model_params={
			'config':config,
		},
	)
# main part is:
#   model_params = create model params dict using sliders and whatnot
#   model = create a model using params
#   renderer = create a SpaceRenderer using the model
#   renderer.render()
#   create the page
#   if __name__ == "__main__":
#     page = SolaraViz(
#         model,
#         renderer,
#         components=[
#             StatePlot,
#             display_model_info,
#         ],
#         model_params=model_params,
#         name="Virus Model",
#     )
#     page  # noqa
#   this needs to be run with `solara run app.py`