from typing import Optional
from mesa import Model
from shapely.geometry import Polygon
import osmnx
from geopandas import GeoDataFrame
import matplotlib.pyplot as plt

class BombEvacuationModel(Model):
	"""A Mesa ABM model to simulation evacuation during a bomb threat
	
	Args:
		domain: Bounding polygon used to select OSM data
		agents: Spatial table of agent starting locations
	"""

	def __init__(
			self, 
			domain: Polygon, 
			agents: Optional[GeoDataFrame] = None):
		super().__init__()
		
		self.G = osmnx.graph_from_polygon(domain, simplify=False)
		self.G = self.G.to_undirected()

		if agents is None:
			features = osmnx.features_from_polygon(domain, tags={'building': True})
			features.to_crs(epsg = 27700, inplace=True)
			agents = GeoDataFrame(geometry=features.centroid)
			agents.to_crs(epsg=4326, inplace=True)

		f, ax = osmnx.plot_graph(self.G, show=False, node_size=0)
		agents.plot(ax=ax, markersize=2, color='red')

		plt.show()


	def run(self, steps: int):
		print('running model')