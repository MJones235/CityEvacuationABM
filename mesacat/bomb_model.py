from mesa import Model
from mesa.space import NetworkGrid
from mesa.time import RandomActivation
from mesa.datacollection import DataCollector
import osmnx
from shapely.geometry import Polygon, Point
from geopandas import GeoDataFrame, GeoSeries, sjoin
from scipy.spatial import cKDTree
import numpy as np
from . import bomb_agent
import igraph
import pandas as pd
from networkx import write_gml


class BombEvacuationModel(Model):
    """A Mesa ABM model to simulation evacuation during a bomb threat

    Args:
        domain: Bounding polygon used
        agents: Spatial table of agent starting locations
        evacuation_zone: Spatial table of bomb exclusion zones
    """

    def __init__(
        self,
        output_path: str,
        domain: Polygon,
        evacuation_zone: GeoDataFrame,
        agents: GeoDataFrame,
    ):
        super().__init__()

        self.output_path = output_path

        self.schedule = RandomActivation(self)

        self.evacuation_zone = evacuation_zone

        # generate road network graph within domain area
        self.G = osmnx.graph_from_polygon(domain, simplify=False)
        self.G = self.G.to_undirected()
        self.nodes, self.edges = osmnx.convert.graph_to_gdfs(self.G)

        agents_in_evacuation_zone = self.get_agents_in_evacuation_zone(agents)

        self.targets = self.get_targets()

        self.add_targets_to_graph()

        self.add_agent_positions_to_graph(agents_in_evacuation_zone)

        self.nodes, self.edges = osmnx.convert.graph_to_gdfs(self.G)

        self.target_nodes = self.nodes[
            self.nodes.index.str.contains("target", na=False)
        ]

        self.grid = NetworkGrid(self.G)
        self.igraph = igraph.Graph.from_networkx(self.G)

        self.write_output_files(output_path, agents_in_evacuation_zone)

        for i, agent in agents_in_evacuation_zone.iterrows():
            id = "agent-start-pos{0}".format(i)
            a = bomb_agent.BombEvacuationAgent(i, self, agent)
            self.schedule.add(a)
            self.grid.place_agent(a, id)
            a.update_route()
            a.update_location()

        self.data_collector = DataCollector(
            model_reporters={"evacuated": evacuated, "stranded": stranded},
            agent_reporters={
                "position": "pos",
                "lat": "lat",
                "lon": "lon",
                "highway": "highway",
                "reroute_count": "reroute_count",
                "status": status,
            },
        )

    def calculate_distance(self, point1: Point, point2: Point):
        df = GeoDataFrame({"geometry": [point1, point2]}, crs="EPSG:4326")
        df = df.geometry.to_crs("EPSG:27700")
        return osmnx.distance.euclidean(
            df.geometry.iloc[0].y,
            df.geometry.iloc[0].x,
            df.geometry.iloc[1].y,
            df.geometry.iloc[1].x,
        )

    def get_agents_in_evacuation_zone(self, agents: GeoDataFrame) -> GeoDataFrame:
        """
        Returns a GeoDataFrame containing agents in the evacuation zone at the start of the simulation
        """
        agents_in_evacuation_zone = sjoin(agents, self.evacuation_zone)

        agents_in_evacuation_zone = agents_in_evacuation_zone.loc[
            ~agents_in_evacuation_zone.index.duplicated(keep="first")
        ]

        agents_in_evacuation_zone = agents_in_evacuation_zone.reset_index()

        assert (
            len(agents_in_evacuation_zone) > 0
        ), "There are no agents within the evacuation zone"

        return agents_in_evacuation_zone

    def get_targets(self) -> GeoDataFrame:
        """
        Returns a GeoDataFrame containing points on the road network at the edge of the evacuation zone
        """
        targets = self.edges.unary_union.intersection(
            self.evacuation_zone.iloc[0].geometry.boundary
        )
        s = GeoSeries(targets).explode(index_parts=True)
        return GeoDataFrame(geometry=s)

    def add_targets_to_graph(self) -> None:
        """
        Add each target as a node in the graph
        """
        for index, row in self.targets.iterrows():
            # find the road that the target is on
            [start_node, end_node, _] = osmnx.distance.nearest_edges(
                self.G, row.geometry.x, row.geometry.y
            )
            # find the distance from the target to each end of the road
            d_start = self.calculate_distance(
                Point(self.G.nodes[start_node]["x"], self.G.nodes[start_node]["y"]),
                Point(row.geometry.x, row.geometry.y),
            )
            d_end = self.calculate_distance(
                Point(self.G.nodes[end_node]["x"], self.G.nodes[end_node]["y"]),
                Point(row.geometry.x, row.geometry.y),
            )

            id = "target{0}".format(index[1])
            edge_attrs = self.G[start_node][end_node]

            # remove the old road
            self.G.remove_edge(start_node, end_node)
            # add target node
            self.G.add_node(id, x=row.geometry.x, y=row.geometry.y, street_count=2)
            # add two new roads connecting the target to each end of the old road
            self.G.add_edge(start_node, id, **{**edge_attrs, "length": d_start})
            self.G.add_edge(id, end_node, **{**edge_attrs, "length": d_end})

    def add_agent_positions_to_graph(self, agents_in_evacuation_zone: GeoDataFrame):
        nodes_tree = cKDTree(
            np.transpose([self.nodes.geometry.x, self.nodes.geometry.y])
        )

        # find the nearest node to each agent
        _, node_idx = nodes_tree.query(
            np.transpose(
                [
                    agents_in_evacuation_zone.geometry.x,
                    agents_in_evacuation_zone.geometry.y,
                ]
            )
        )

        for i, agent in agents_in_evacuation_zone.iterrows():
            nearest_node = self.nodes.iloc[node_idx[i]]

            id = "agent-start-pos{0}".format(i)

            d = self.calculate_distance(
                Point(nearest_node["x"], nearest_node["y"]),
                Point(agent.geometry.x, agent.geometry.y),
            )

            self.G.add_node(id, x=agent.geometry.x, y=agent.geometry.y, street_count=1)
            self.G.add_edge(id, self.nodes.index[node_idx[i]], **{"length": d})

    def write_output_files(
        self, output_path: str, agents_in_evacuation_zone: GeoDataFrame
    ) -> None:
        output_gml = output_path + ".gml"
        write_gml(self.G, path=output_gml)

        output_gpkg = output_path + ".gpkg"
        self.evacuation_zone.to_file(output_gpkg, layer="hazard", driver="GPKG")
        agents_in_evacuation_zone[
            ["agent_type", "walking_speed", "geometry", "home"]
        ].to_file(output_gpkg, layer="agents", driver="GPKG")
        self.target_nodes.to_file(output_gpkg, layer="targets", driver="GPKG")
        self.nodes[["geometry"]].to_file(output_gpkg, layer="nodes", driver="GPKG")
        self.edges[["geometry"]].to_file(output_gpkg, layer="edges", driver="GPKG")

    def step(self):
        self.schedule.step()
        self.data_collector.collect(self)

    def run(self, steps: int):
        self.data_collector.collect(self)
        for i in range(steps):
            print("Step {0}".format(i))
            self.step()

        self.data_collector.get_agent_vars_dataframe().astype(
            {"highway": pd.Int64Dtype()}
        ).to_csv(self.output_path + ".agent.csv")
        self.data_collector.get_model_vars_dataframe().to_csv(
            self.output_path + ".model.csv"
        )
        return self.data_collector.get_agent_vars_dataframe()


def evacuated(m):
    return len([a for a in m.schedule.agents if a.evacuated])


def stranded(m):
    return len([a for a in m.schedule.agents if a.stranded])


def status(a):
    return 1 if a.evacuated else 0
