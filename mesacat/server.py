from mesa.experimental import JupyterViz
import os
import sys
import datetime
import geopandas as gpd
import osmnx
import solara

sys.path.append("..")

from mesacat.model import EvacuationModel

newcastle_test_data = os.path.join(os.path.dirname(__file__), "tests", "newcastle")

sample_data = os.path.join(newcastle_test_data, "sample_data")


def get_domain():
    domain_file = os.path.join(sample_data, "newcastle-small.gpkg")
    domain = gpd.read_file(domain_file).geometry[0]
    domain, _ = osmnx.projection.project_geometry(domain, "EPSG:3857", to_latlong=True)
    return domain


model_params = {
    "output_path": None,
    "domain": get_domain(),
    "evacuation_zone": gpd.read_file(
        os.path.join(sample_data, "test-model") + ".gpkg", layer="hazards"
    ).to_crs(epsg=4326),
    "population_data_path": os.path.join(newcastle_test_data, "population_data"),
    "start_time": datetime.time(hour=8, minute=30),
}


def agent_portrayal(agent):
    return {"edge_color": "black", "node_size": 0, "node_color": "#00b4d9"}


def draw_network(model):
    f, ax = osmnx.plot_graph(
        model.G,
        dpi=200,
        node_size=0,
        edge_color="green",
        edge_linewidth=0.5,
    )

    solara.FigureMatplotlib(f)


page = JupyterViz(
    EvacuationModel,
    model_params,
    measures=[draw_network],
    agent_portrayal=agent_portrayal,
)

page
