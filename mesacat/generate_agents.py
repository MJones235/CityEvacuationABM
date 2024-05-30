from shapely.geometry import Polygon, Point
from geopandas import GeoDataFrame
import pointpats

def generate_agents(domain: Polygon, n: int):
	agents = GeoDataFrame(geometry=[Point(coords) for coords in pointpats.random.poisson(domain.iloc[0].geometry, size=n)], crs='EPSG:4326')
	return agents