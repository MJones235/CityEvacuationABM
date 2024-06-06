import sys

sys.path.append("..")

from mesacat.generate_agents import (
    generate_agents,
    plot_agents,
)
from unittest import TestCase
import os
import geopandas as gpd
import osmnx as ox
from datetime import time

outputs = os.path.join(os.path.dirname(__file__), "outputs", "agent_initial_positions")
population_data = os.path.join(os.path.dirname(__file__), "population_data")
sample_data = os.path.join(os.path.dirname(__file__), "sample_data")
domain_file = os.path.join(sample_data, "newcastle-small.gpkg")


class TestGenerateAgents(TestCase):

    def test_generate_agents(self):
        domain = gpd.read_file(domain_file).geometry[0]
        domain, _ = ox.projection.project_geometry(domain, "EPSG:3857", to_latlong=True)
        """
        start_times = [
            time(hour=7, minute=15),
            time(hour=8, minute=15),
            time(hour=9, minute=15),
            time(hour=10, minute=15),
            time(hour=11, minute=15),
            time(hour=12, minute=15),
            time(hour=13, minute=15),
            time(hour=14, minute=15),
            time(hour=15, minute=15),
            time(hour=16, minute=15),
            time(hour=17, minute=15),
            time(hour=18, minute=15),
            time(hour=19, minute=15),
            time(hour=20, minute=15),
        ]
        for start_time in start_times:
            agents = generate_agents(domain, 5000, population_data, start_time)
            plot_agents(domain, agents, start_time, outputs)
        """
        start_time = time(hour=8, minute=20)
        agents = generate_agents(domain, 5000, population_data, start_time)
        plot_agents(domain, agents, start_time, outputs)


if __name__ == "__main__":
    TestGenerateAgents().test_generate_agents()
