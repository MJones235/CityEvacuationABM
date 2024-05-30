from shapely.geometry import Polygon, Point
from geopandas import GeoDataFrame
import pointpats
from pandas import read_csv
import os
import osmnx as ox

def generate_agents(domain: Polygon, n: int, in_path: str):
	census_data_path = os.path.join(in_path, 'census.csv')
	census_df = read_csv(census_data_path)
	total = census_df['Observation'].sum()
	census_df['p'] = census_df['Observation'] / total

	demography = get_agent_demography(in_path)

	agents_list = []

	for (_, category) in demography.iterrows():
		n_category = round(n * category['proportion'])
		agents_in_category = [{'demographic': category['id'], 'walking_speed': category['walking_speed']} for _ in range(n_category)]
		agents_list += agents_in_category

	agents = GeoDataFrame(data=agents_list, geometry=[Point(coords) for coords in pointpats.random.poisson(domain, size=len(agents_list))], crs='EPSG:4326')
	return agents

def get_agent_demography(in_path: str):
	census_data_path = os.path.join(in_path, 'census.csv')
	census_df = read_csv(census_data_path)
	total = census_df['Observation'].sum()
	census_df['proportion'] = census_df['Observation'] / total
	census_df = census_df[['Age (3 categories)', 'Sex (2 categories)', 'Hours worked (3 categories)', 'proportion']]
	census_df = census_df.rename(columns={'Age (3 categories)': 'age', 'Sex (2 categories)': 'sex', 'Hours worked (3 categories)': 'employment'})
	census_df['employment'] = census_df['employment'].map({'Does not apply': 'Unemployed', 'Part-time: 30 hours or less worked': 'Part-time', 'Full-time: 31 or more hours worked': 'Full-time'})
	
	walking_speed_path = os.path.join(in_path, 'walking_speed.csv')
	walking_speed_df = read_csv(walking_speed_path)
	census_df = census_df.join(walking_speed_df.set_index('id'))
	census_df['id'] = census_df.index
	return census_df

def get_buildings(domain: Polygon):
	residential_buildings = ox.features_from_polygon(domain, tags={'building': 'residential'})
	commercial_buildings = ox.features_from_polygon(domain, tags={'building': ['commercial', 'industrial', 'office', 'retail', 'supermarket', 'warehouse']})
	schools = ox.features_from_polygon(domain, tags={'amenity': ['school']})
	return (residential_buildings, commercial_buildings, schools)
