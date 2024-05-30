from typing import Optional
from mesa import Model
from mesa.space import NetworkGrid
from mesa.time import RandomActivation
from mesa.datacollection import DataCollector
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
import pandas as pd
from networkx import write_gml


class BombEvacuationModel(Model):
	"""A Mesa ABM model to simulation evacuation during a bomb threat
	
	Args:
		domain: Bounding polygon used to select OSM data
		agents: Spatial table of agent starting locations
		hazard: Spatial table of bomb exclusion zones
	"""

	def __init__(
			self, 
			output_path: str,
			domain: Polygon, 
			hazard: GeoDataFrame,
			agents: GeoDataFrame):
		super().__init__()

		self.output_path = output_path
		self.schedule = RandomActivation(self)
		
		# set evacuation zone
		self.hazard = hazard

		# generate road network graph within domain area
		self.G = osmnx.graph_from_polygon(domain, simplify=False)
		self.G = self.G.to_undirected()

		self.nodes, self.edges = osmnx.convert.graph_to_gdfs(self.G)

		nodes_tree = cKDTree(np.transpose([self.nodes.geometry.x, self.nodes.geometry.y]))


		agents_in_hazard_zone = sjoin(agents, self.hazard)
		agents_in_hazard_zone = agents_in_hazard_zone.loc[~agents_in_hazard_zone.index.duplicated(keep='first')]
		
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
			
			id = index[1]
			edge_attrs = self.G[start_node][end_node]

			# remove the old road
			self.G.remove_edge(start_node, end_node)
			# add target node
			self.G.add_node(id, x=row.geometry.x, y=row.geometry.y, street_count=2)
			# add two new roads connecting the target to each end of the old road
			self.G.add_edge(start_node, id, **{**edge_attrs, 'length': d_start})
			self.G.add_edge(id, end_node, **{**edge_attrs, 'length': d_end})
			
		self.nodes, self.edges = osmnx.convert.graph_to_gdfs(self.G)
		
		self.target_nodes = self.nodes[self.nodes.index < len(self.targets)]

		self.grid = NetworkGrid(self.G)
		self.igraph = igraph.Graph.from_networkx(self.G)

		# write output files
		output_gml = output_path + '.gml'
		write_gml(self.G, path=output_gml)

		output_gpkg = output_path + '.gpkg'
		self.hazard.to_file(output_gpkg, layer='hazard', driver='GPKG')
		agents_in_hazard_zone.to_file(output_gpkg, layer='agents', driver='GPKG')
		self.target_nodes.to_file(output_gpkg, layer='targets', driver='GPKG')
		self.nodes[['geometry']].to_file(output_gpkg, layer='nodes', driver='GPKG')
		self.edges[['geometry']].to_file(output_gpkg, layer='edges', driver='GPKG')

		# create agents
		# find the nearest node to each agent
		_, node_idx = nodes_tree.query(
            np.transpose([agents_in_hazard_zone.geometry.x, agents_in_hazard_zone.geometry.y]))

		for i, idx in enumerate(node_idx):
			agent = agents_in_hazard_zone.iloc[i]
			a = bomb_agent.BombEvacuationAgent(i, self, agent)
			self.schedule.add(a)
			self.grid.place_agent(a, self.nodes.index[idx])
			a.update_route()
			a.update_location()

		self.data_collector = DataCollector(
			model_reporters={
				'evacuated': evacuated,
				'stranded': stranded
			},
			agent_reporters={'position': 'pos',
                             'lat': 'lat',
                             'lon': 'lon',
                             'highway': 'highway',
							 'reroute_count': 'reroute_count',
                             'status': status}
		)



	def calculate_distance(self, point1, point2):
		df = GeoDataFrame({'geometry': [point1, point2]}, crs="EPSG:4326")
		df = df.geometry.to_crs("EPSG:27700")
		return osmnx.distance.euclidean(df.geometry.iloc[0].y, df.geometry.iloc[0].x, df.geometry.iloc[1].y, df.geometry.iloc[1].x)

	def step(self):
		self.schedule.step()
		self.data_collector.collect(self)

	def run(self, steps: int):
		self.data_collector.collect(self)
		for _ in range(steps):
			self.step()

		self.data_collector.get_agent_vars_dataframe().astype({'highway': pd.Int64Dtype()}).to_csv(
			self.output_path + '.agent.csv')
		self.data_collector.get_model_vars_dataframe().to_csv(self.output_path + '.model.csv')
		return self.data_collector.get_agent_vars_dataframe()


def evacuated(m):
    return len([a for a in m.schedule.agents if a.evacuated])

def stranded(m):
    return len([a for a in m.schedule.agents if a.stranded])

def status(a):
    return 1 if a.evacuated else 0
