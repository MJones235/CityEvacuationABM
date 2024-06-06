from shapely.geometry import Polygon, Point
from geopandas import GeoDataFrame, GeoSeries
from pandas import read_csv
import os
import osmnx as ox
import matplotlib.pyplot as plt
from datetime import time
import random
import igraph
from scipy.spatial import cKDTree
import numpy as np

from mesacat.schedule_utils import position_at_time


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

    G = ox.graph_from_polygon(domain, simplify=False)
    G = G.to_undirected()
    iGraph = igraph.Graph.from_networkx(G)
    nodes, _ = ox.convert.graph_to_gdfs(G)
    nodes_tree = cKDTree(np.transpose([nodes.geometry.x, nodes.geometry.y]))

    agent_types = get_agent_types(in_path)
    agent_types = add_walking_speed(in_path, agent_types)

    agents_list = []

    for _, agent_type in agent_types.iterrows():
        count = round(n * agent_type["proportion"])  # number of agents of this type
        agents_of_type = [
            {
                "agent_type": agent_type["id"],
                "walking_speed": agent_type["walking_speed"],
                "geometry": Point(0, 0),
            }
            for _ in range(count)
        ]
        agents_list += agents_of_type

    agents = GeoDataFrame(data=agents_list, crs="EPSG:4326")

    (
        residential_buildings,
        work_buildings,
        schools,
        supermarkets,
        shops,
        recreation_buildings,
    ) = get_buildings(domain)

    agents["home"] = random_buildings(residential_buildings, k=len(agents))
    agents["work"] = random_buildings(work_buildings, k=len(agents))
    agents["school"] = random_buildings(schools, k=len(agents))
    agents["supermarket"] = random_buildings(supermarkets, k=len(agents))
    agents["shop"] = random_buildings(shops, k=len(agents))
    agents["recreation"] = random_buildings(recreation_buildings, k=len(agents))

    agents["geometry"] = agents.apply(
        lambda row: position_at_time(
            row["agent_type"],
            start_time,
            iGraph,
            nodes,
            nodes_tree,
            row["walking_speed"],
            row["home"],
            row["work"],
            row["school"],
            row["supermarket"],
            row["shop"],
            row["recreation"],
        ),
        axis=1,
    )

    locations = ["home", "work", "school", "supermarket", "shop", "recreation"]

    for location in locations:
        agents[location] = agents[location].apply(lambda loc: loc["osmid"])

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


def get_buildings(
    domain: Polygon,
) -> tuple[
    GeoDataFrame, GeoDataFrame, GeoDataFrame, GeoDataFrame, GeoDataFrame, GeoDataFrame
]:
    """
    Get building footprint polygons for each type of building within the domain area

    Args:
        domain (Polygon): area of interest
    """
    residential_buildings = polygon(
        ox.features_from_polygon(
            domain,
            tags={
                "building": [
                    "apartments",
                    "bungalow",
                    "detached",
                    "dormitory",
                    "hotel",
                    "house",
                    "residential",
                    "semidetached_house",
                    "terrace",
                ]
            },
        )
    )

    all_buildings = polygon(ox.features_from_polygon(domain, tags={"building": True}))
    non_residential_buildings = all_buildings.overlay(
        residential_buildings, how="difference"
    )

    schools = polygon(
        ox.features_from_polygon(
            domain, tags={"amenity": ["college", "kindergarten", "school"]}
        )
    )

    supermarkets = polygon(
        ox.features_from_polygon(
            domain, tags={"building": "supermarket", "shop": ["convenience"]}
        )
    )

    shops = polygon(ox.features_from_polygon(domain, tags={"building": "retail"}))

    recreation_buildings = polygon(
        ox.features_from_polygon(
            domain,
            tags={"leisure": True, "amenity": ["bar", "cafe", "pub", "restaurant"]},
        )
    )

    return (
        residential_buildings,
        non_residential_buildings,
        schools,
        supermarkets,
        shops,
        recreation_buildings,
    )


def polygon(gdf: GeoDataFrame) -> GeoDataFrame:
    """
    Filter the GeoDataFrame to only contain polygons.  Lines and points will be removed.

    Args:
        gdf (GeoDataFrame): input data frame
    """
    return gdf[gdf.geometry.geom_type == "Polygon"].reset_index()


def random_buildings(gdf: GeoDataFrame, k=1) -> GeoSeries:
    """
    Return a random building from a GeoDataFrame

    Args:
        gdf (GeoDataFrame): input data frame
    """

    return random.choices(
        [building[1] for building in gdf.iterrows()],
        weights=[building[1].geometry.area for building in gdf.iterrows()],
        k=k,
    )


def plot_agents(
    domain: Polygon, agents: GeoDataFrame, start_time: time, out_path: str
) -> None:
    """
    Plot agents using matplotlib

    Args:
        domain (Polygon)
        agents (GeoDataFrame)
        residential_buildings (GeoDataFrame)
        commercial_buildings (GeoDataFrame)
        schools (GeoDataFrame)
    """

    (
        residential_buildings,
        work_buildings,
        schools,
        supermarkets,
        shops,
        recreation_buildings,
    ) = get_buildings(domain)

    graph = ox.graph_from_polygon(domain, simplify=False)
    graph = graph.to_undirected()

    _, ax = ox.plot_graph(graph, show=False, node_size=0)
    residential_buildings.plot(ax=ax, color="green")
    work_buildings.plot(ax=ax, color="yellow")
    schools.plot(ax=ax, color="purple")
    supermarkets.plot(ax=ax, color="white")
    shops.plot(ax=ax, color="silver")
    recreation_buildings.plot(ax=ax, color="lightsalmon")
    agents[agents["agent_type"] == 0].plot(
        ax=ax, markersize=2, color="red", label="Children"
    )
    agents[agents["agent_type"] == 1].plot(
        ax=ax, markersize=2, color="blue", label="Working adults"
    )
    agents[agents["agent_type"] == 2].plot(
        ax=ax, markersize=2, color="orange", label="Retired adults"
    )

    plt.title("Agent positions at {0}".format(start_time))

    plt.legend(
        title="Agents",
        title_fontproperties={"weight": "bold"},
        bbox_to_anchor=(1.05, 1),
    )

    building_legend = [
        {"label": "Residential", "color": "green"},
        {"label": "Non-residential", "color": "yellow"},
        {"label": "Schools", "color": "purple"},
        {"label": "Supermarkets", "color": "white"},
        {"label": "Shops", "color": "silver"},
        {"label": "Recreational", "color": "lightsalmon"},
    ]

    for i, item in enumerate(building_legend):
        plt.figtext(
            0.92,
            0.05 * (i + 6),
            item["label"],
            ha="left",
            fontsize=12,
            bbox={"facecolor": item["color"], "alpha": 0.5, "pad": 5},
        )

    plt.savefig(
        os.path.join(out_path, "{0}.png".format(start_time)), bbox_inches="tight"
    )
