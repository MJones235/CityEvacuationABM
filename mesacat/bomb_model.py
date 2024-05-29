from typing import Optional
from mesa import Model
from mesa.space import NetworkGrid
from mesa.time import RandomActivation
import osmnx
import pointpats.random
from shapely.geometry import Polygon, Point
from geopandas import GeoDataFrame, GeoSeries, sjoin
import matplotlib.pyplot as plt
from scipy.spatial import cKDTree
import numpy as np
from . import bomb_agent
import igraph
import pointpats

class BombEvacuationModel(Model):
	"""A Mesa ABM model to simulation evacuation during a bomb threat
	
	Args:
		domain: Bounding polygon used to select OSM data
		agents: Spatial table of agent starting locations
		hazard: Spatial table of bomb exclusion zones
	"""

	def __init__(
			self, 
			domain: Polygon, 
			hazard: GeoDataFrame):
		super().__init__()

		self.schedule = RandomActivation(self)
		
		# set evacuation zone
		self.hazard = hazard.to_crs(epsg=4326)

		# generate road network graph within domain area
		self.G = osmnx.graph_from_polygon(domain, simplify=False)
		self.G = self.G.to_undirected()
		self.nodes, self.edges = osmnx.convert.graph_to_gdfs(self.G)
		nodes_tree = cKDTree(np.transpose([self.nodes.geometry.x, self.nodes.geometry.y]))

		# place one agent in each building
		agents = GeoDataFrame(geometry=[Point(coords) for coords in pointpats.random.poisson(domain, size=300)], crs='EPSG:4326')

		agents_in_hazard_zone = sjoin(agents, self.hazard)
		agents_in_hazard_zone = agents_in_hazard_zone.loc[~agents_in_hazard_zone.index.duplicated(keep='first')]
		agents_outside_hazard_zone = agents[~agents.index.isin(agents_in_hazard_zone.index.values)]
		
		# set targets to be the points on the road network at the edge of the evacuation zone
		targets = self.edges.unary_union.intersection(self.hazard.iloc[0].geometry.boundary)
		s = GeoSeries(targets).explode(index_parts=True)
		self.targets = GeoDataFrame(geometry=s)
	
		# add each target as a node to the graph
		for (index, row) in self.targets.iterrows():
			# find the road that the target is on
			[start_node, end_node, _] = osmnx.distance.nearest_edges(self.G, row.geometry.x, row.geometry.y)
			# find the distance from the target to each end of the road
			d_start = self.calculate_distance(Point(self.G.nodes[start_node]['x'], self.G.nodes[start_node]['y']), Point(row.geometry.x, row.geometry.y))
			d_end = self.calculate_distance(Point(self.G.nodes[end_node]['x'], self.G.nodes[end_node]['y']), Point(row.geometry.x, row.geometry.y))
			
			id = "target" + str(index[1])
			edge_attrs = self.G[start_node][end_node]

			# remove the old road
			self.G.remove_edge(start_node, end_node)
			# add target node
			self.G.add_node(id, x=row.geometry.x, y=row.geometry.y, street_count=2)
			# add two new roads connecting the target to each end of the old road
			self.G.add_edge(start_node, id, **{**edge_attrs, 'length': d_start})
			self.G.add_edge(id, end_node, **{**edge_attrs, 'length': d_end})
			
		self.nodes, self.edges = osmnx.convert.graph_to_gdfs(self.G)
		
		self.target_nodes = self.nodes[self.nodes.index.str.contains('target', na=False)]

		self.grid = NetworkGrid(self.G)
		self.igraph = igraph.Graph.from_networkx(self.G)

		# create agents
		# find the nearest node to each agent
		_, node_idx = nodes_tree.query(
            np.transpose([agents_in_hazard_zone.geometry.x, agents_in_hazard_zone.geometry.y]))

		for i, idx in enumerate(node_idx):
			a = bomb_agent.BombEvacuationAgent(i, self)
			self.schedule.add(a)
			self.grid.place_agent(a, self.nodes.index[idx])
			a.update_route()
			a.update_location()

		# plot the results
		f, ax = osmnx.plot_graph(self.G, show=False, node_size=0)
		self.hazard.plot(ax=ax, color='red', alpha=0.2)
		self.targets.plot(ax=ax, markersize=4, color='yellow')
		agents_in_hazard_zone.plot(ax=ax, markersize=2, color='red')
		agents_outside_hazard_zone.plot(ax=ax, markersize=2, color='green')

		plt.show()


	def calculate_distance(self, point1, point2):
		df = GeoDataFrame({'geometry': [point1, point2]}, crs="EPSG:4326")
		df = df.geometry.to_crs("EPSG:27700")
		return osmnx.distance.euclidean(df.geometry.iloc[0].y, df.geometry.iloc[0].x, df.geometry.iloc[1].y, df.geometry.iloc[1].x)


	def run(self, steps: int):
		print('running model')

	