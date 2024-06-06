from datetime import time, date, timedelta, datetime
import matplotlib.pyplot as plt
import numpy as np
import random
from shapely import Point, Polygon, buffer
import pointpats
import networkx as nx
from geopandas import GeoSeries, GeoDataFrame
from igraph import Graph
from scipy.spatial import cKDTree

from mesacat.generate_schedule import get_schedule


def plot_graph(G: nx.DiGraph) -> None:
    """
    plot schedule graph
    """
    pos = nx.spring_layout(G)
    nx.draw(G, pos, with_labels=True)
    nx.draw_networkx_edge_labels(G, pos)
    plt.show()


def position_at_time(
    agent_type: int,
    t: time,
    igraph: Graph,
    nodes: GeoDataFrame,
    nodes_tree: cKDTree,
    walking_speed: float,
    home: GeoSeries,
    work: GeoSeries,
    school: GeoSeries,
    supermarket: GeoSeries,
    shop: GeoSeries,
    recreation: GeoSeries,
) -> tuple[Point, str | None, bool]:
    """
    Determine the location of an agent at a given time, based off their daily schedule

    Args:
        agent_type (int): agent type identifier
        t (time): time of day
        home (GeoSeries): agent's home location
        work (GeoSeries): agent's work location
        school (GeoSeries): agent's (or their child's) school location
        supermarket (GeoSeries): agent's assigned supermarket
        shop (GeoSeries): agent's assigned shop
        recreation (GeoSeries): location of agent's assigned recreational activity
    """

    schedule = get_schedule(agent_type)
    # assume that the agent will always be in the same location at the start of the day (most likely at home)
    # this is the start node and it has zero incoming edges
    current_node = [n for n, d in schedule.in_degree() if d == 0][0]
    date_today = date.today()
    target_time = datetime.combine(date_today, t)
    arrival_time = datetime.combine(date_today, time(hour=0))

    # traverse the agent's schedule until time t is reached
    while arrival_time < target_time:
        # current node in the schedule graph
        node = schedule.nodes[current_node]
        # apply random variation to the time that the agent will leave their current location
        time_delta = timedelta(
            seconds=np.random.normal(0, node["variation"].total_seconds())
        )

        # time the agent will leave their current location
        leave_time: datetime
        if "leave_at" in node:
            leave_time = datetime.combine(date_today, node["leave_at"]) + time_delta
        elif "duration" in node:
            leave_time = arrival_time + abs(node["duration"] + time_delta)
        else:
            break

        # the agent will be at their current location when the target time is reached
        if leave_time > target_time:
            break

        next_location_options = [n for n in schedule.out_edges(current_node, data="p")]

        # the agent will remain at their current location for the remainder of the day
        if len(next_location_options) == 0:
            break

        # select the agent's next destination, based on the assigned probabilities
        next_node_name = random.choices(
            [item[1] for item in next_location_options],
            weights=[item[2] for item in next_location_options],
        )[0]

        # teleport the agent to their next destination (travel time is not accounted for)
        origin = point_from_node_name(
            current_node, home, work, school, supermarket, shop, recreation
        )
        destination = point_from_node_name(
            next_node_name, home, work, school, supermarket, shop, recreation
        )

        _, [origin_idx, destination_idx] = nodes_tree.query(
            [[origin.x, origin.y], [destination.x, destination.y]]
        )

        path = igraph.get_shortest_paths(origin_idx, destination_idx, weights="length")[
            0
        ]

        total_distance = igraph.shortest_paths(
            origin_idx, destination_idx, weights="length"
        )[0][0]

        car_speed = 48  # kph
        walking_speed = walking_speed

        in_car = total_distance > 500

        speed = car_speed if in_car else walking_speed

        total_travel_time = (total_distance / 1000) / speed

        arrival_time_at_next_node = leave_time + timedelta(hours=total_travel_time)

        # agent will arrive at their next destination
        if arrival_time_at_next_node < target_time:
            current_node = next_node_name
            arrival_time = arrival_time_at_next_node

        else:
            i = 0
            t = leave_time
            while t < target_time:
                distance_to_next_node = igraph.shortest_paths(
                    path[i], path[i + 1], weights="length"
                )[0][0]
                time_to_next_node = (distance_to_next_node / 1000) / speed

                t += timedelta(hours=time_to_next_node)
                i += 1

            node = nodes.iloc[path[i - 2]]
            return (Point(node.x, node.y), nodes.iloc[path[i]].name, in_car)

    current_location = point_from_node_name(
        current_node, home, work, school, supermarket, shop, recreation
    )

    return (current_location, None, False)


def point_from_node_name(
    node: str,
    home: GeoSeries,
    work: GeoSeries,
    school: GeoSeries,
    supermarket: GeoSeries,
    shop: GeoSeries,
    recreation: GeoSeries,
):
    """
    Return the geopgraphic location of the agent based on the name of the node they are at
    """
    if "home" in node:
        return random_point_in_polygon(home.geometry)
    elif "work" in node:
        return random_point_in_polygon(work.geometry)
    elif "school" in node:
        return random_point_in_polygon(school.geometry)
    elif "supermarket" in node:
        return random_point_in_polygon(supermarket.geometry)
    elif "shop" in node:
        return random_point_in_polygon(shop.geometry)
    elif "recreation" in node:
        return random_point_in_polygon(recreation.geometry)
    else:
        ValueError("Unknown location: {0}".format(node))


def index_from_node_name(
    node: str,
    nodes: GeoDataFrame,
    home: GeoSeries,
    work: GeoSeries,
    school: GeoSeries,
    supermarket: GeoSeries,
    shop: GeoSeries,
    recreation: GeoSeries,
):

    if "home" in node:
        return nodes.index.get_loc(home.osmid)
    elif "work" in node:
        return nodes.index.get_loc(work.osmid)
    elif "school" in node:
        return nodes.index.get_loc(school.osmid)
    elif "supermarket" in node:
        return nodes.index.get_loc(supermarket.osmid)
    elif "shop" in node:
        return nodes.index.get_loc(shop.osmid)
    elif "recreation" in node:
        return nodes.index.get_loc(recreation.osmid)
    else:
        ValueError("Unknown OSMID: {0}".format(node))


def random_point_in_polygon(geometry: Polygon):
    """
    Generate a random point within a polygon
    """

    # A buffer is added because the method hangs if the polygon is too small
    return Point(
        pointpats.random.poisson(buffer(geometry=geometry, distance=0.000001), size=1)
    )
