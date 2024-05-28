from mesa import Model
from shapely.geometry import Polygon
import osmnx

class BombEvacuationModel(Model):
	"""A Mesa ABM model to simulation evacuation during a bomb threat
	
	Args:
		domain: Bounding polygon used to select OSM data
	"""

	def __init__(self, domain: Polygon):
		super().__init__()
		
		self.G = osmnx.graph_from_polygon(domain, simplify=False)
		self.G = self.G.to_undirected()

		osmnx.plot_graph(self.G)

	def run(self, steps: int):
		print('running model')