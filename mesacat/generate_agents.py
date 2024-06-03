from shapely.geometry import Polygon
from geopandas import GeoDataFrame, GeoSeries
from pandas import read_csv
import os
import osmnx as ox
from random import randrange
import matplotlib.pyplot as plt
from datetime import time

from mesacat.generate_schedule import get_schedule
from mesacat.schedule_utils import position_at_time
from mesacat.types.agent_data import AgentData


def generate_agents(
    domain: Polygon, n: int, in_path: str, start_time: time
) -> GeoDataFrame:
    """Generates n agents within the domain area.

    Args:
        domain (Polygon): area within which the agents will be placed
        n (int): number of agents to be generated
        in_path (str): path to input data files
        start_time (time): time that the simulation will begin at
    """

    agent_types = get_agent_types(in_path)
    agent_types = add_walking_speed(in_path, agent_types)

    (residential_buildings, commercial_buildings, schools) = get_buildings(domain)

    agents_list = []

    for _, agent_type in agent_types.iterrows():
        count = round(n * agent_type["proportion"])
        agents_of_type = [
            get_agent_data(
                start_time,
                agent_type,
                residential_buildings,
                commercial_buildings,
                schools,
            )
            for _ in range(count)
        ]
        agents_list += agents_of_type

    agents = GeoDataFrame(data=agents_list, crs="EPSG:4326")

    return agents


def get_agent_types(in_path: str) -> GeoDataFrame:
    """
    Get the different types of agent and their proportion within the population (based on census data)

    Args:
        in_path (str): path to the input data
    """
    census_data_path = os.path.join(in_path, "age_data.csv")
    census_df = read_csv(census_data_path)
    total = census_df["Observation"].sum()
    census_df["proportion"] = census_df["Observation"] / total
    census_df = census_df[["Age (3 categories)", "proportion"]]
    census_df = census_df.rename(columns={"Age (3 categories)": "age"})
    return census_df


def add_walking_speed(in_path: str, census_df: GeoDataFrame) -> GeoDataFrame:
    """
    Add a column to the input dataframe containing walking speed for each type of agent

    Args:
        in_path (str): path to the input data
        (GeoDataFrame): dataframe containing types of agent
    """

    walking_speed_path = os.path.join(in_path, "walking_speed.csv")
    walking_speed_df = read_csv(walking_speed_path)
    census_df = census_df.join(walking_speed_df.set_index("id"))
    census_df["id"] = census_df.index
    return census_df


def get_buildings(domain: Polygon) -> tuple[GeoDataFrame, GeoDataFrame, GeoDataFrame]:
    """
    Get building footprint polygons for each type of building within the domain area

    Args:
        domain (Polygon): area of interest
    """
    residential_buildings = polygon(
        ox.features_from_polygon(domain, tags={"building": "residential"})
    )
    all_buildings = polygon(ox.features_from_polygon(domain, tags={"building": True}))
    non_residential_buildings = all_buildings.overlay(
        residential_buildings, how="difference"
    )
    schools = polygon(ox.features_from_polygon(domain, tags={"amenity": ["school"]}))
    return (residential_buildings, non_residential_buildings, schools)


def polygon(gdf: GeoDataFrame) -> GeoDataFrame:
    """
    Filter the GeoDataFrame to only contain polygons.  Lines and points will be removed.

    Args:
        gdf (GeoDataFrame): input data frame
    """
    return gdf[gdf.geometry.geom_type == "Polygon"].reset_index()


def get_agent_data(
    start_time: time,
    agent_type: GeoDataFrame,
    residential_buildings: GeoDataFrame,
    commercial_buildings: GeoDataFrame,
    schools: GeoDataFrame,
) -> AgentData:
    """
    Assign characteristics to each agent, including their home, work and school locations, their initial position and their walking speed

    Args:
        start_time (time): time that the simulation will begin at
        agent_type (GeoDataFrame): type of agent
        residential_buildings (GeoDataFrame): footprint of residential buildings in domain area
        commercial_buildings (GeoDataFrame): footprint of possible workplaces in the domain area
        schools (GeoDataFrame): footprint of schools in the domain area
    """

    home = random_building(residential_buildings)
    work = random_building(commercial_buildings)
    school = random_building(schools)

    schedule = get_schedule(agent_type["id"])

    return AgentData(
        agent_type["id"],
        agent_type["walking_speed"],
        home["osmid"],
        work["osmid"],
        school["osmid"],
        position_at_time(schedule, start_time, home, work, school),
    )


def random_building(gdf: GeoDataFrame) -> GeoSeries:
    """
    Return a random building from a GeoDataFrame

    Args:
        gdf (GeoDataFrame): input data frame
    """

    return gdf.iloc[randrange(len(gdf))]


def plot_agents(domain: Polygon, agents: GeoDataFrame) -> None:
    """
    Plot agents using matplotlib

    Args:
        domain (Polygon)
        agents (GeoDataFrame)
        residential_buildings (GeoDataFrame)
        commercial_buildings (GeoDataFrame)
        schools (GeoDataFrame)
    """

    (residential_buildings, commercial_buildings, schools) = get_buildings(domain)

    graph = ox.graph_from_polygon(domain, simplify=False)
    graph = graph.to_undirected()

    _, ax = ox.plot_graph(graph, show=False, node_size=0)
    residential_buildings.plot(ax=ax, color="green")
    commercial_buildings.plot(ax=ax, color="yellow")
    schools.plot(ax=ax, color="purple")
    agents[agents["agent_type"] == 0].plot(ax=ax, markersize=2, color="red")
    agents[agents["agent_type"] == 1].plot(ax=ax, markersize=2, color="blue")
    agents[agents["agent_type"] == 2].plot(ax=ax, markersize=2, color="orange")

    plt.show()
