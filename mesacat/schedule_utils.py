from datetime import time, date, timedelta, datetime
import matplotlib.pyplot as plt
import numpy as np
import random
from shapely import Point, Polygon, buffer
import pointpats
import networkx as nx
from geopandas import GeoSeries


def plot_graph(G: nx.DiGraph) -> None:
    """
    plot schedule graph
    """
    pos = nx.spring_layout(G)
    nx.draw(G, pos, with_labels=True)
    nx.draw_networkx_edge_labels(G, pos)
    plt.show()


def position_at_time(
    schedule: nx.DiGraph, t: time, home: GeoSeries, work: GeoSeries, school: GeoSeries
) -> Point:
    """
    Determine the location of an agent at a given time, based off their daily schedule

    Args:
        schedule (DiGraph): graph representing the agent's daily schedule
        t (time): time of day
        home (GeoSeries): agent's home location
        work (GeoSeries): agent's work location
        school (GeoSeries): agent's (or their child's) school location
    """

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
        current_node = next_node_name
        arrival_time = leave_time

    current_location = point_from_node_name(current_node, home, work, school)
    return current_location


def point_from_node_name(node: str, home: object, work: object, school: object):
    """
    Return the geopgraphic location of the agent based on the name of the node they are at
    """
    if "home" in node:
        return random_point_in_polygon(home.geometry)
    elif "work" in node:
        return random_point_in_polygon(work.geometry)
    elif "school" in node:
        return random_point_in_polygon(school.geometry)
    else:
        return Point(0, 0)


def random_point_in_polygon(geometry: Polygon):
    """
    Generate a random point within a polygon
    """

    # A buffer is added because the method hangs if the polygon is too small
    return Point(
        pointpats.random.poisson(buffer(geometry=geometry, distance=0.000001), size=1)
    )
