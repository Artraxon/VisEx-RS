import geohash
import psycopg2
import geojson
from geojson import MultiLineString

from shapely import geometry
import database as db
# Generates the geohashes for the database, has to be run manually
GEOHASH_PRECISION = 5

def is_geohash_in_bounding_box(current_geohash, bbox_coordinates):
    """Checks if the box of a geohash is inside the bounding box

    :param current_geohash: a geohash
    :param bbox_coordinates: bounding box coordinates
    :return: true if the the center of the geohash is in the bounding box
    """

    coordinates = geohash.decode(current_geohash)
    geohash_in_bounding_box = (bbox_coordinates[0] < coordinates[0] < bbox_coordinates[2]) and (
            bbox_coordinates[1] < coordinates[1] < bbox_coordinates[3])
    return geohash_in_bounding_box


def compute_geohash_tiles(bbox_coordinates):
    """Computes all geohash tile in the given bounding box

    :param bbox_coordinates: the bounding box coordinates of the geohashes
    :return: a list of geohashes
    """

    checked_geohashes = set()
    geohash_stack = set()
    geohashes = []
    # get center of bounding box, assuming the earth is flat ;)
    center_latitude = (bbox_coordinates[0] + bbox_coordinates[2]) / 2
    center_longitude = (bbox_coordinates[1] + bbox_coordinates[3]) / 2

    center_geohash = geohash.encode(center_latitude, center_longitude, precision=GEOHASH_PRECISION)
    geohashes.append(center_geohash)
    geohash_stack.add(center_geohash)
    checked_geohashes.add(center_geohash)
    while len(geohash_stack) > 0:
        current_geohash = geohash_stack.pop()
        neighbors = geohash.neighbors(current_geohash)
        for neighbor in neighbors:
            if neighbor not in checked_geohashes and is_geohash_in_bounding_box(neighbor, bbox_coordinates):
                geohashes.append(neighbor)
                geohash_stack.add(neighbor)
                checked_geohashes.add(neighbor)
    return geohashes

# bbox = [#[41, 11, 50, 24],
#     [53, 18, 57, 28],
#     [52, 1, 46, 10],
#     [51, -10, 56, -4]
# ]

bbox = [#[41, 11, 50, 24],
    [46, 1, 52, 10]
]

conn = psycopg2.connect(dbname=db.dbname, user=db.user, port=db.port, host=db.host, password=db.password)
for box in bbox:
    cur = conn.cursor()
    tiles = compute_geohash_tiles(box)
    print("Generated {amount} tiles".format(amount = len(tiles)))
    for i, hash in enumerate(tiles):
        print("Inserting {i} hash".format(i=i))
        cur.execute("""INSERT INTO public."hashtiles" VALUES (%s, st_setsrid(st_geomfromgeohash(%s), 4326))""", (hash,hash))

    conn.commit()
    cur.close()

conn.close()



