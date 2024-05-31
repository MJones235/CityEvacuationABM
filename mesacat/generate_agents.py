from networkx import DiGraph
from shapely.geometry import Polygon, Point
from shapely import buffer
from geopandas import GeoDataFrame
from pandas import read_csv
import os
import osmnx as ox
from random import randrange
import matplotlib.pyplot as plt
from datetime import time, timedelta, datetime, date
import networkx as nx
import random
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
		agents_in_category = [get_agent_data(i, start_time, category, residential_buildings, commercial_buildings, schools) for i in range(n_category)]
		agents_list += agents_in_category
	
	agents = GeoDataFrame(data=agents_list, crs='EPSG:4326')
	
	plot(domain, agents, residential_buildings, commercial_buildings, schools)
	
	return agents

def get_agent_data(i: int, start_time: time, category: dict, residential_buildings: GeoDataFrame, commercial_buildings: GeoDataFrame, schools: GeoDataFrame):
	home = residential_buildings.iloc[randrange(len(residential_buildings))]
	work = commercial_buildings.iloc[randrange(len(commercial_buildings))]
	school = schools.iloc[randrange(len(schools))]

	return {
		'demographic': category['id'], 
		'walking_speed': category['walking_speed'],
		'home': home['osmid'],
		'work': work['osmid'],
		'school': school['osmid'],
		'geometry': get_agent_start_position(category['id'], start_time, home, work, school)
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
	schools.plot(ax=ax, color='purple')
	agents[agents['demographic'] == 0].plot(ax=ax, markersize=2, color='red')
	agents[agents['demographic'] == 1].plot(ax=ax, markersize=2, color='blue')
	agents[agents['demographic'] == 2].plot(ax=ax, markersize=2, color='orange')

	plt.show()


def generate_child_schedule():
	G = nx.DiGraph()
	G.add_nodes_from([
		('home', {'leave_at': time(hour=8), 'variation': timedelta(minutes=15)}),
		('school', {'leave_at': time(hour=15, minute=15), 'variation': timedelta(minutes=15)}),
		('supermarket', {'duration': timedelta(minutes=45), 'variation': timedelta(minutes=15)}),
		('recreation', {'duration': timedelta(hours=2), 'variation': timedelta(hours=1)}),
		('home 2', {'leave_at': time(hour=19), 'variation': timedelta(hours=1)}),
	])
	G.add_edges_from([
		('home', 'school', {'p': 1}),
		('school', 'home 2', {'p': 0.5}),
		('school', 'supermarket', {'p': 0.25}),
		('school', 'recreation', {'p': 0.25}),
		('supermarket', 'home 2', {'p': 1}),
		('recreation', 'home 2', {'p': 1})
	])

	# plot_graph(G)

	return G


def generate_working_adult_schedule():
	G = nx.DiGraph()
	G.add_nodes_from([
		('home', {'leave_at': time(hour=8), 'variation': timedelta(minutes=15)}),
		('school', {'duration': timedelta(minutes=10), 'variation': timedelta(minutes=5)}),
		('shop', {'duration': timedelta(hours=2), 'variation': timedelta(hours=1)}),
		('work', {'leave_at': time(hour=17, minute=15), 'variation': timedelta(minutes=15)}),
		('school 2', {'duration': timedelta(minutes=5), 'variation': timedelta(minutes=1)}),
		('supermarket', {'duration': timedelta(minutes=45), 'variation': timedelta(minutes=15)}),
		('home 2', {'leave_at': time(hour=19), 'variation': timedelta(hours=1)}),
		('recreation', {'duration': timedelta(hours=1), 'variation': timedelta(minutes=30)}),
		('home 3', {'leave_at': time(hour=23), 'variation': timedelta(hours=1)}),
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
		('home 2', 'home 3', {'p': 0.9}),
		('recreation', 'home 3', {'p': 1})
	])

	# plot_graph(G)

	return G

def generate_retired_adult_schedule():
	G = nx.DiGraph()
	G.add_nodes_from([
		('home', {'leave_at': time(hour=10), 'variation': timedelta(hours=1)}),
		('shop', {'duration': timedelta(hours=2), 'variation': timedelta(hours=1)}),
		('supermarket', {'duration': timedelta(minutes=45), 'variation': timedelta(minutes=15)}),
		('recreation', {'duration': timedelta(hours=1), 'variation': timedelta(minutes=30)}),
		('home 2', {'duration': timedelta(hours=2), 'variation': timedelta(hours=1)}),
		('home 3', {'leave_at': time(hour=19), 'variation': timedelta(hours=1)}),
	])
	G.add_edges_from([
		('home', 'supermarket', {'p': 0.5}),
		('home', 'shop', {'p': 0.5}),
		('supermarket', 'home 2', {'p': 1}),
		('shop', 'home 2', {'p': 1}),
		('home 2', 'recreation', {'p': 0.5}),
		('home 2', 'home 3', {'p': 0.5}),
		('recreation', 'home 3', {'p': 1})
	])

	# plot_graph(G)

	return G 

def get_schedule(category_id: int):
	match category_id:
		case 0:
			return generate_child_schedule()
		case 1:
			return generate_working_adult_schedule()
		case 2:
			return generate_retired_adult_schedule()
		case _:
			return generate_working_adult_schedule()

def get_agent_start_position(category_id: int, start_time: time, home:object, work: object, school: object):
	G = get_schedule(category_id)
	start_node = [n for n, d in G.in_degree() if d==0][0]
	
	current_node = start_node
	arrival_time = time(hour=0)

	while arrival_time < start_time:
		node = G.nodes[current_node]
		time_delta = timedelta(seconds=np.random.normal(0, node['variation'].total_seconds()))
		leave_time: time

		if 'leave_at' in node:
			leave_time = (datetime.combine(date.today(), node['leave_at']) + time_delta).time()
		elif 'duration' in node:
			stay_duration = node['duration'] + time_delta
			if stay_duration < timedelta(seconds=0):
				stay_duration = timedelta(seconds=0)
			leave_time = (datetime.combine(date.today(), arrival_time) + stay_duration).time()
		else:
			break

		if leave_time > start_time:
			break
		
		options = [n for n in G.out_edges(current_node, data='p')]

		if (len(options) == 0):
			break
		
		next_node_name = random.choices([item[1] for item in options], weights=[item[2] for item in options])[0]
		current_node = next_node_name
		# assume no travel time (i.e they teleport to their next location)
		arrival_time = leave_time
	
	current_location = get_node_location(current_node, home, work, school)
	return current_location

def get_node_location(node: str, home:object, work: object, school: object):
	if 'home' in node:
		return get_random_point_in_polygon(home.geometry)
	elif 'work' in node:
		return get_random_point_in_polygon(work.geometry)
	elif 'school' in node:
		return get_random_point_in_polygon(school.geometry)
	else: return Point(0, 0)

def get_random_point_in_polygon(geometry: Polygon):
	return Point(pointpats.random.poisson(buffer(geometry=geometry, distance=0.000001), size=1))

def plot_graph(G: DiGraph):
	pos = nx.spring_layout(G)
	nx.draw(G, pos, with_labels=True)
	nx.draw_networkx_edge_labels(G, pos)
	plt.show()