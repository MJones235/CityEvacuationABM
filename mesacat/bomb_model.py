from typing import Optional
from mesa import Model
import osmnx.distance
from shapely.geometry import Polygon, Point
import osmnx
from geopandas import GeoDataFrame, GeoSeries, sjoin
import matplotlib.pyplot as plt
from scipy.spatial import cKDTree
import numpy as np

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
			targets: GeoDataFrame,
			hazard: GeoDataFrame,
			agents: Optional[GeoDataFrame] = None):
		super().__init__()
		
		self.targets = targets.to_crs(epsg=4326)
		self.hazard = hazard.to_crs(epsg=4326)

		self.G = osmnx.graph_from_polygon(domain, simplify=False)
		self.G = self.G.to_undirected()

		self.nodes, self.edges = osmnx.convert.graph_to_gdfs(self.G)
		nodes_tree = cKDTree(np.transpose([self.nodes.geometry.x, self.nodes.geometry.y]))

		if agents is None:
			buildings = osmnx.features_from_polygon(domain, tags={'building': True}).to_crs(epsg = 27700)
			# place one agent in each building
			agents = GeoDataFrame(geometry=buildings.centroid).to_crs(epsg=4326)

		agents_in_hazard_zone = sjoin(agents, self.hazard)
		agents_in_hazard_zone = agents_in_hazard_zone.loc[~agents_in_hazard_zone.index.duplicated(keep='first')]
		agents_outside_hazard_zone = agents[~agents.index.isin(agents_in_hazard_zone.index.values)]
		
		# find the nearest node to each agent
		_, node_idx = nodes_tree.query(
            np.transpose([agents_in_hazard_zone.geometry.x, agents_in_hazard_zone.geometry.y]))

		targets = self.edges.unary_union.intersection(self.hazard.iloc[0].geometry.boundary)
		s = GeoSeries(targets)
		s = s.explode()
		self.targets = GeoDataFrame(geometry=s)

		# find the nearest node to each target location
		_, target_node_idx = nodes_tree.query(
			np.transpose([self.targets.geometry.x, self.targets.geometry.y]))

	
		for (index, row) in self.targets.iterrows():
			[start_node, end_node, _] = osmnx.distance.nearest_edges(self.G, row.geometry.x, row.geometry.y)
			id = "target" + str(index[1])
			edge_attrs = self.G[start_node][end_node]
			coordinate_dict = {'name': ['start', 'end'],
					'geometry': [Point(self.G.nodes[start_node]['x'], self.G.nodes[start_node]['y']), Point(self.G.nodes[end_node]['x'], self.G.nodes[end_node]['y'])]}
			df = GeoDataFrame(coordinate_dict, crs="EPSG:4326")
			df = df.geometry.to_crs("EPSG:27700")
			d = osmnx.distance.euclidean(df.geometry.iloc[0].y, df.geometry.iloc[0].x, df.geometry.iloc[1].y, df.geometry.iloc[1].x)
			print(d, edge_attrs[0]['length'])
			self.G.remove_edge(start_node, end_node)
			self.G.add_node(id, x=row.geometry.x, y=row.geometry.y, street_count=2)
			#self.G.add_edge(start_node, id, **{**edge_attrs, 'length': osmnx.distance.euclidean(f, id)})
			
			"""
			if not self.G.has_node(row.osm_id):
				self.G.add_edge(nearest_node, row.osm_id, length=0)
				self.G.nodes[row.osm_id]['osm_id'] = row.osm_id
				self.G.nodes[row.osm_id]['x'] = row.geometry.x
				self.G.nodes[row.osm_id]['y'] = row.geometry.y
        	"""

		self.nodes, self.edges = osmnx.convert.graph_to_gdfs(self.G)

		
		f, ax = osmnx.plot_graph(self.G, show=False)
		self.hazard.plot(ax=ax, color='red', alpha=0.2)
		self.targets.plot(ax=ax, markersize=4, color='yellow')
		agents_in_hazard_zone.plot(ax=ax, markersize=2, color='red')
		agents_outside_hazard_zone.plot(ax=ax, markersize=2, color='green')

		plt.show()


	def run(self, steps: int):
		print('running model')