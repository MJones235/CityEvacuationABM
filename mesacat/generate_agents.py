from typing import Optional
from shapely.geometry import Polygon, Point
from geopandas import GeoDataFrame
from pandas import read_csv
import os
import osmnx as ox
from random import randrange
import matplotlib.pyplot as plt
from datetime import time, timedelta, datetime, date
import networkx as nx
import random
from dataclasses import dataclass
import numpy as np
import pointpats

def generate_agents(domain: Polygon, n: int, in_path: str, start_time: time):
	census_data_path = os.path.join(in_path, 'age_data.csv')
	census_df = read_csv(census_data_path)
	total = census_df['Observation'].sum()
	census_df['p'] = census_df['Observation'] / total

	demography = get_agent_demography(in_path)

	(residential_buildings, commercial_buildings, schools) = get_buildings(domain)

	agents_list = []

	for (_, category) in demography.iterrows():
		n_category = round(n * category['proportion'])
		agents_in_category = [get_agent_data(start_time, category, residential_buildings, commercial_buildings, schools) for _ in range(n_category)]
		
		agents_list += agents_in_category

	agents = GeoDataFrame(data=agents_list, crs='EPSG:4326')
	
	plot(domain, agents, residential_buildings, commercial_buildings, schools)
	
	return agents

def get_agent_data(start_time: time, category: dict, residential_buildings: GeoDataFrame, commercial_buildings: GeoDataFrame, schools: GeoDataFrame):
	home = residential_buildings.iloc[randrange(len(residential_buildings))]
	work = commercial_buildings.iloc[randrange(len(commercial_buildings))]
	school = schools.iloc[randrange(len(schools))]

	return {
		'demographic': category['id'], 
		'walking_speed': category['walking_speed'],
		'home': home['osmid'],
		'work': work['osmid'],
		'school': school['osmid'],
		'geometry': get_agent_start_position(start_time, home, work, school)
	}



def get_agent_demography(in_path: str):
	census_data_path = os.path.join(in_path, 'age_data.csv')
	census_df = read_csv(census_data_path)
	total = census_df['Observation'].sum()
	census_df['proportion'] = census_df['Observation'] / total
	census_df = census_df[['Age (3 categories)', 'proportion']]
	census_df = census_df.rename(columns={'Age (3 categories)': 'age'})
	#census_df = census_df[['Age (3 categories)', 'Sex (2 categories)', 'Hours worked (3 categories)', 'proportion']]
	#census_df = census_df.rename(columns={'Age (3 categories)': 'age', 'Sex (2 categories)': 'sex', 'Hours worked (3 categories)': 'employment'})
	#census_df['employment'] = census_df['employment'].map({'Does not apply': 'Unemployed', 'Part-time: 30 hours or less worked': 'Part-time', 'Full-time: 31 or more hours worked': 'Full-time'})
	
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


def plot(domain: Polygon, agents: GeoDataFrame, residential_buildings: GeoDataFrame, commercial_buildings: GeoDataFrame, schools: GeoDataFrame):
	graph = ox.graph_from_polygon(domain, simplify=False)
	graph = graph.to_undirected()

	f, ax = ox.plot_graph(graph, show=False, node_size=0)
	residential_buildings.plot(ax=ax, color='green')
	commercial_buildings.plot(ax=ax, color='yellow')
	schools.plot(ax=ax, color='pink')
	agents.plot(ax=ax, color='red', markersize=2)

	plt.show()




def generate_schedule_graph():
	G = nx.DiGraph()
	G.add_nodes_from([
		('home', {'leave_at': time(hour=8), 'variation': timedelta(minutes=15)}),
		('school', {'duration': timedelta(minutes=10), 'variation': timedelta(minutes=5)}),
		('shop', {'duration': timedelta(hours=2), 'variation': timedelta(hours=1)}),
		('work', {'leave_at': time(hour=17, minute=15), 'variation': timedelta(minutes=15)}),
		('school 2', {'duration': timedelta(minutes=5), 'variation': timedelta(minutes=1)}),
		('supermarket', {'duration': timedelta(minutes=45), 'variation': timedelta(minutes=15)}),
		('home 2', {'leave_at': time(hour=19), 'variation': timedelta(hours=1)}),
		('recreation', {'duration': timedelta(hours=1), 'variation': timedelta(minutes=30)})
	])
	G.add_edges_from([
		('home', 'school', {'p': 1}),
		('school', 'shop', {'p': 0.1}),
		('school', 'work', {'p': 0.9}),
		('shop', 'work', {'p': 1}),
		('work', 'supermarket', {'p': 0.15}),
		('work', 'school 2', {'p': 0.6}),
		('work', 'home 2', {'p': 0.25}),
		('supermarket', 'home 2', {'p': 1}),
		('school 2', 'supermarket', {'p': 0.5}),
		('school 2', 'home 2', {'p': 0.5}),
		('home 2', 'recreation', {'p': 0.1}),
		('home 2', 'home 2', {'p': 0.9}),
		('recreation', 'home 2', {'p': 1})
	])

	"""
	pos = nx.spring_layout(G)

	nx.draw(G, pos, with_labels=True)
	nx.draw_networkx_edge_labels(G, pos)
	plt.show()
	"""

	return G

def get_agent_start_position(start_time: time, home:object, work: object, school: object):
	G = generate_schedule_graph()
	start_node = [n for n, d in G.in_degree() if d==0][0]
	
	current_node = start_node
	arrival_time = time(hour=0)

	while arrival_time < start_time:
		node = G.nodes[current_node]

		time_delta = timedelta(seconds=np.random.normal(0, node['variation'].total_seconds()))
		leave_time: time

		if 'leave_at' in node:
			leave_time = (datetime.combine(date.today(), node['leave_at']) + time_delta).time()
		else:
			stay_duration = node['duration'] + time_delta
			if stay_duration < timedelta(seconds=0):
				stay_duration = timedelta(seconds=0)
			leave_time = (datetime.combine(date.today(), arrival_time) + stay_duration).time()


		if leave_time > start_time:
			break
		
		options = [n for n in G.out_edges(current_node, data='p')]
		
		next_node_name = random.choices([item[1] for item in options], weights=[item[2] for item in options])[0]
		current_node = next_node_name
		# assume no travel time (i.e they teleport to their next location)
		arrival_time = leave_time
		#next_node = G.nodes[next_node_name]
	
	current_location = get_node_location(current_node, home, work, school)
	return current_location

def get_node_location(node: str, home:object, work: object, school: object):
	if 'home' in node:
		return Point(pointpats.random.poisson(home.geometry, size=1))
	if 'work' in node:
		return Point(pointpats.random.poisson(work.geometry, size=1))
	if 'school' in node:
		return Point(pointpats.random.poisson(school.geometry, size=1))
	else: return Point(0, 0)

