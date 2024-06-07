from __future__ import annotations
from . import model
from mesa import Agent
import numpy as np


class EvacuationAgent(Agent):
    """A person in the domain area at the time of the bomb threat

    Args:
        unique_id: an identifier for the agent
        evacuation_model: the parent EvacuationModel

    Attributes:
        pos(int): the ID of the most recent node that has been passed
        route (typing.List[int]): a list of node IDs that the agent is traversing
        route_index (int): the number of nodes that the agent has passed along the route
        distance_along_edge (float): the distance that the agent has travelled from the most recent node
        lat: current latitude
        lon: current longitude
    """

    def __init__(
        self,
        unique_id: int,
        evacuation_model: model.EvacuationModel,
        agent: dict,
    ):
        super().__init__(unique_id, evacuation_model)
        self.pos: int
        self.route = []
        self.route_index = 0
        self.distance_along_edge = 0
        self.lat = None
        self.lon = None
        self.evacuated = False
        self.stranded = False
        self.highway = None
        self.reroute_count = -1
        self.agent_type = agent["agent_type"]
        self.in_car = agent["in_car"]
        self.speed = 48 if self.in_car else agent["walking_speed"]

    def update_route(self):
        # indices of target nodes
        targets = [
            self.model.nodes.index.get_loc(node)
            for node in self.model.target_nodes.index
        ]
        # index of agent's last visited node
        source = self.model.nodes.index.get_loc(self.pos)
        # calculate minimum distance to each evacuation point
        target_distances = self.model.igraph.shortest_paths_dijkstra(
            source=[source], target=targets, weights="length"
        )[0]
        target = targets[int(np.argmin(target_distances))]
        path = self.model.igraph.get_shortest_paths(source, target, weights="length")[0]
        self.route = self.model.nodes.iloc[path].index
        self.route_index = 0

    def update_location(self):
        origin_node = self.model.nodes.loc[self.route[self.route_index]]
        destination_node = self.model.nodes.loc[self.route[self.route_index + 1]]
        edge_length = self.distance_along_edge + self.distance_to_next_node()

        if edge_length == 0:
            self.lat = origin_node.geometry.y
            self.lon = origin_node.geometry.x
        else:
            k = self.distance_along_edge / edge_length
            self.lat = (
                k * destination_node.geometry.y + (1 - k) * origin_node.geometry.y
            )
            self.lon = (
                k * destination_node.geometry.x + (1 - k) * origin_node.geometry.x
            )

    def distance_to_next_node(self):
        edge = self.model.G.get_edge_data(
            self.route[self.route_index], self.route[self.route_index + 1]
        )[0]
        return edge["length"] - self.distance_along_edge

    def step(self):
        """Moves the agent towards the target node by 10 seconds"""

        if self.evacuated:
            return

        distance_to_travel = (
            self.speed / 60 / 60 * 10 * 1000
        )  # metres travelled in ten seconds

        # if agent passes through one or more nodes during the step
        while distance_to_travel >= self.distance_to_next_node():
            all_agents = self.model.grid.get_all_cell_contents()

            agents_in_path = [
                agent
                for agent in all_agents
                if agent.unique_id != self.unique_id
                and agent.route[agent.route_index] == self.route[self.route_index]
                and agent.in_car == self.in_car
                and agent.distance_along_edge > self.distance_along_edge
                and agent.distance_along_edge - self.distance_along_edge
                < distance_to_travel
            ]

            if len(agents_in_path) == 0:
                distance_to_travel -= self.distance_to_next_node()
                self.route_index += 1
                self.distance_along_edge = 0
                self.model.grid.move_agent(self, self.route[self.route_index])

                # if target is reached
                if self.route_index == len(self.route) - 1:
                    self.lat = self.model.nodes.loc[self.pos].geometry.y
                    self.lon = self.model.nodes.loc[self.pos].geometry.x
                    self.evacuated = True
                    return
                else:
                    edge = self.model.G.get_edge_data(
                        self.route[self.route_index], self.route[self.route_index + 1]
                    )[0]
                    if "osmid" in edge.keys():
                        self.highway = edge["osmid"]

            else:
                nearest_agent_distance = sorted(
                    [agent.distance_along_edge for agent in agents_in_path]
                )[0]

                distance_to_travel = (
                    nearest_agent_distance - self.distance_along_edge - 1
                )
                if distance_to_travel < 0:
                    distance_to_travel = 0
                break

        self.distance_along_edge += distance_to_travel
        self.update_location()
