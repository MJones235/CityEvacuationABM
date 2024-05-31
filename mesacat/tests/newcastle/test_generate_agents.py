import sys
sys.path.append('..')

from mesacat.generate_agents import generate_agents, get_agent_demography, get_buildings, get_agent_start_position, generate_child_schedule, generate_working_adult_schedule, generate_retired_adult_schedule
from unittest import TestCase
import os
import geopandas as gpd
import osmnx as ox
from datetime import time
import matplotlib.pyplot as plt

population_data = os.path.join(os.path.dirname(__file__), 'population_data')
sample_data = os.path.join(os.path.dirname(__file__), 'sample_data')
domain_file = os.path.join(sample_data, 'newcastle-small.gpkg')

class TestGenerateAgents(TestCase):

	def test_generate_agents(self):
		domain = gpd.read_file(domain_file).geometry[0]
		domain, _ = ox.projection.project_geometry(domain, 'EPSG:3857', to_latlong=True)
		generate_agents(domain, 5000, population_data, time(hour=9, minute=15))

	def test_generate_categories(self):
		get_agent_demography(population_data)

	def test_get_buildings(self):
		domain = gpd.read_file(domain_file).geometry[0]
		domain, _ = ox.projection.project_geometry(domain, 'EPSG:3857', to_latlong=True)
		# domain = ox.geocode_to_gdf("Newcastle-upon-Tyne, UK").iloc[0].geometry
		get_buildings(domain)

	def test_generate_schedule(self):
		get_agent_start_position()

	def test_generate_schedule(self):
		generate_child_schedule()
	
		
if __name__ == '__main__':
	TestGenerateAgents().test_generate_agents()

