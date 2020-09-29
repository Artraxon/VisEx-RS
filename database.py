from typing import List, Tuple

import psycopg2
import datetime
import geojson as gj
import pandas as pd
import sqlalchemy
from util import geojsons
import numpy as np
import os

dbname = ""
user = ""
port = 5435
host = ""
password = ""

for k,v in os.environ.items():
    if k.startswith("GUNICORN_"):
        key = k.split('_', 1)[1].lower()
        locals()[key] = v
    if k.startswith("VISEX_"):
        key = k.split('V', 1)[1].lower()
        if key == "db":
            dbname = v
        elif key == "user":
            user = v
        elif key == "port":
            port = int(v)
        elif key == "host":
            host = v
        elif key == "password":
            password = v

conn = psycopg2.connect(dbname=dbname, user=user, port=port, host=host,
                        password=password)

engine = sqlalchemy.create_engine("postgresql://{user}:{password}@{host}:{port}/{dbname}"
                                  .format(user=user, password=password, host=host, port=port, dbname=dbname))

totalArea = """{"type": "Polygon", "coordinates": [[[-11, 34], [35, 34], [35, 70], [-11, 70], [-11, 34]]]}"""


def get_developement_trace(boundary: str, label: str):
    df = pd.read_sql_query("SELECT timestmp as attimestamp, covered as sum FROM agg_over_time(%s, %s)",
                           params=[boundary, label], con=engine)
    df['sum'] = df['sum'] / (1000 * 1000)
    return df


def get_timestamps_in_area(boundary: str) -> List[datetime.datetime]:
    cur = conn.cursor()
    cur.execute("SELECT * FROM a_find_geohash_times(%s)", (boundary,))
    aggs = cur.fetchall()
    X = [x[0] for x in aggs]
    cur.close()
    return X


def density_grid(label: str, boundary: str, timestamp: datetime.datetime) -> pd.DataFrame:
    df = pd.read_sql_query("SELECT * FROM a_geohash_density_wrapped(%s, %s, %s, %s)",
                           params=[boundary, label, 5, int(timestamp.timestamp())], con=engine)
    df = df.loc[lambda f: f['amount'] > 0, :]
    df = df.apply(map_to_feature, axis=1)
    return df


def outline_grid(boundary: str) -> Tuple[gj.FeatureCollection, gj.Point]:
    df = pd.read_sql_query("""
    SELECT st_asgeojson(sub.unioned) as unioned, st_asgeojson(st_centroid(sub.unioned)) as center 
    FROM (SELECT st_union(tile_sources.area) as unioned 
          FROM tile_sources WHERE st_intersects(tile_sources.area, st_geomfromgeojson(%s))
    GROUP BY TRUE) as sub
    """, params=[boundary], con=engine)
    feature = gj.Feature(geometry=gj.loads(df.iloc[0].iloc[0]))
    center = gj.loads(df.iloc[0].iloc[1])
    return gj.FeatureCollection([feature]), center


def over_time_selected(hashes: List[str], label: str) -> pd.DataFrame:
    df = pd.read_sql_query("""
    SELECT timestmp as atTimestamp, SUM(covered) as sum
    FROM hashlabels 
    WHERE substring(geohash, 1, %s) = ANY(%s) AND label = %s GROUP BY timestmp;
    """, params=[
        len(hashes[0]),
        '{' + ','.join(["\"{}\"".format(hash) for hash in hashes]) + '}',
        label
    ], con=engine)
    #m^2 --> km^2
    df['sum'] = df['sum'] / (1000 * 1000)
    return df


def map_to_feature(row: pd.Series) -> pd.Series:
    return pd.Series({'geohash': row.geohash,
                      'feature': gj.Feature(geometry=gj.loads(row.geom), properties={'geohash': row.geohash}),
                      'covered': np.clip(round((row.amount / row.total) * 100, 1), 0, 100)})


def findPatches(tile_source: str, labels: List[str], matchAny: bool = True) -> pd.DataFrame:
    if labels == []:
        params = [tile_source]
    else:
        params = [tile_source, labels]
    df = pd.read_sql_query("""
    SELECT *
    FROM (SELECT patch_name, st_asgeojson(area) as area, acquisition, array_agg(label) as agged
    FROM patches JOIN labels USING(area, acquisition)
    WHERE part_of = %s
    GROUP BY area, acquisition, patch_name) as sub
    """ + ( "" if labels == [] else (""" WHERE sub.agged && %s;""" if matchAny else """ WHERE sub.agged @> %s""")),
                           params=params, con=engine)

    df = df.apply(lambda row: pd.Series({'patch_name': row.patch_name,
                                    'feature': gj.Feature(geometry=gj.loads(row.area), properties={'patch_name': row.patch_name}),
                                    'acquisition': row.acquisition,
                                    'labels': row.agged}),
                  axis=1)
    df['val'] = 1
    return df


def findTileSources(startDate: datetime.date, endDate: datetime.date, country: str) -> pd.DataFrame:
    return pd.read_sql_query("""
    SELECT tile_source FROM tile_sources WHERE %s <= acquisition AND %s >= acquisition AND st_intersects(area, st_geomfromgeojson(%s)) ORDER BY tile_source;
    """, params=[startDate, endDate, totalArea if country == None else geojsons[country]], con=engine)


def outlinePatches(tileSources: List[str]) -> Tuple[gj.FeatureCollection, gj.Point]:
    tranformedArray = "{\"" + '\",\"'.join(tileSources) + "\"}"
    df = pd.read_sql_query("""
    SELECT st_asgeojson(sub.unioned) as unioned, st_asgeojson(st_centroid(sub.unioned)) as center
    FROM (SELECT st_union(area) unioned FROM tile_sources WHERE tile_source = ANY(%s) GROUP BY TRUE) as sub;
    """, params=[[tileSources],], con=engine)
    feature = gj.Feature(geometry=gj.loads(df.iloc[0].iloc[0]))
    center = gj.loads(df.iloc[0].iloc[1])
    return gj.FeatureCollection([feature]), center

