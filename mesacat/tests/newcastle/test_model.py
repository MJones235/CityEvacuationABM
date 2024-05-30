import sys

import osmnx.convert
import osmnx.projection 
sys.path.append('..')

from unittest import TestCase
import geopandas as gpd
import os
import osmnx
from mesacat.bomb_model import BombEvacuationModel
from mesacat.utils import create_movie
from mesacat.generate_agents import generate_agents

sample_data = os.path.join(os.path.dirname(__file__), 'sample_data')
domain_file = os.path.join(sample_data, 'newcastle-small.gpkg')

outputs = os.path.join(os.path.dirname(__file__), 'outputs')
if not os.path.exists(outputs):
	os.mkdir(outputs)

class TestEvacuationModel(TestCase):
	def test_model_run(self):
		test_model_path = os.path.join(sample_data, 'test-model')
		geopackage = test_model_path + '.gpkg'
		hazard = gpd.read_file(geopackage, layer='hazards').to_crs(epsg=4326)
		domain = gpd.read_file(domain_file).geometry[0]
		domain, _ = osmnx.projection.project_geometry(domain, 'EPSG:3857', to_latlong=True)
		agents = generate_agents(hazard, 5000)
		BombEvacuationModel(os.path.join(outputs, 'test-model'), domain, hazard, agents).run(50)

if __name__ == '__main__':
    TestEvacuationModel().test_model_run()
    create_movie(os.path.join(outputs, 'test-model'), os.path.join(outputs, 'test-model.mp4'))
