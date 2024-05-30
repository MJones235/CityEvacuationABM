from shapely.geometry import Polygon, Point
from geopandas import GeoDataFrame
from pandas import read_csv
import os
import osmnx as ox
from random import randrange
import matplotlib.pyplot as plt
from datetime import time

def generate_agents(domain: Polygon, n: int, in_path: str, start_time: time):
	census_data_path = os.path.join(in_path, 'census.csv')
	census_df = read_csv(census_data_path)
	total = census_df['Observation'].sum()
	census_df['p'] = census_df['Observation'] / total

	demography = get_agent_demography(in_path)

	(residential_buildings, commercial_buildings, schools) = get_buildings(domain)

	agents_list = []

	for (_, category) in demography.iterrows():
		n_category = round(n * category['proportion'])
		agents_in_category = [get_agent_data(category, residential_buildings, commercial_buildings) for _ in range(n_category)]
		
		agents_list += agents_in_category

	agents = GeoDataFrame(data=agents_list, crs='EPSG:4326')
	
	plot(domain, agents, residential_buildings, commercial_buildings)
	
	return agents

def get_agent_data(category: dict, residential_buildings: GeoDataFrame, commercial_buildings: GeoDataFrame):
	home_index = randrange(len(residential_buildings))
	work_index = randrange(len(commercial_buildings))

	return {
		'demographic': category['id'], 
		'walking_speed': category['walking_speed'],
		'home': residential_buildings.iloc[home_index]['osmid'],
		'work': commercial_buildings.iloc[work_index]['osmid'],
		'geometry': commercial_buildings.iloc[work_index].geometry.centroid
	}

def get_agent_demography(in_path: str):
	census_data_path = os.path.join(in_path, 'census.csv')
	census_df = read_csv(census_data_path)
	total = census_df['Observation'].sum()
	census_df['proportion'] = census_df['Observation'] / total
	census_df = census_df[['Age (3 categories)', 'Sex (2 categories)', 'Hours worked (3 categories)', 'proportion']]
	census_df = census_df.rename(columns={'Age (3 categories)': 'age', 'Sex (2 categories)': 'sex', 'Hours worked (3 categories)': 'employment'})
	census_df['employment'] = census_df['employment'].map({'Does not apply': 'Unemployed', 'Part-time: 30 hours or less worked': 'Part-time', 'Full-time: 31 or more hours worked': 'Full-time'})
	
	walking_speed_path = os.path.join(in_path, 'walking_speed.csv')
	walking_speed_df = read_csv(walking_speed_path)
	census_df = census_df.join(walking_speed_df.set_index('id'))
	census_df['id'] = census_df.index
	return census_df

def get_buildings(domain: Polygon):
	residential_buildings = polygon(ox.features_from_polygon(domain, tags={'building': 'residential'}))
	all_buildings = polygon(ox.features_from_polygon(domain, tags={'building': True}))
	non_residential_buildings = all_buildings.overlay(residential_buildings, how='difference')
	schools = polygon(ox.features_from_polygon(domain, tags={'amenity': ['school']}))
	return (residential_buildings, non_residential_buildings, schools)

def polygon(gdf: GeoDataFrame):
	return gdf[gdf.geometry.geom_type == 'Polygon'].reset_index()


def plot(domain: Polygon, agents: GeoDataFrame, residential_buildings: GeoDataFrame, commercial_buildings: GeoDataFrame):
	graph = ox.graph_from_polygon(domain, simplify=False)
	graph = graph.to_undirected()

	f, ax = ox.plot_graph(graph, show=False, node_size=0)
	residential_buildings.plot(ax=ax, color='green')
	commercial_buildings.plot(ax=ax, color='yellow')
	agents.plot(ax=ax, color='red', markersize=2)

	plt.show()
	