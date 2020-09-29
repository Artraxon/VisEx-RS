from typing import List

# Used to imports the outlines of the copernicus products into the database to speed up calculations significantly.
# Has to be run manually
import pyodata
import requests
import psycopg2
import sys
import logging
import fiona
from pyodata.v2.service import GetEntitySetFilter as esf
from urllib.request import urlopen
import xml.etree.ElementTree as ET
from http.client import HTTPConnection
#HTTPConnection.debuglevel = 1
import database as db

requests_log = logging.getLogger("urllib3")

#Set up db connection
conn = psycopg2.connect(dbname=db.dbname, user=db.user, port=db.port, host=db.host, password=db.password)
cur: psycopg2._psycopg.cursor = conn.cursor()

#Get all product names
cur.execute("SELECT part_of FROM patches GROUP BY part_of")
snapshots = cur.fetchall()
snapshots: List[str] = [x[0] for x in snapshots]
foundGeoms = {}
noGeoms = []

#Setup connection to copernicus
SERVICE_URL = "https://scihub.copernicus.eu/dhus/odata/v1"
session = requests.session()
session.auth = ("artrax", "oypfN6y7eh6fU6OeoeEWH8ZMtvYQtk")
#Setup the XML namespaces
ns = {"def": "http://www.w3.org/2005/Atom", "d":"http://schemas.microsoft.com/ado/2007/08/dataservices" ,"m":"http://schemas.microsoft.com/ado/2007/08/dataservices/metadata", "base":"https://scihub.copernicus.eu/dhus/odata/v1/"}


def req(snapshotName: str)-> str:
    #Define Request Body
    payload =  {"$filter": "Name eq '" + snapshotName + "'", "$select": "ContentGeometry"}
    r = session.get(SERVICE_URL + "/Products",  params=payload)
    root = ET.fromstring(r.text)
    #Retrieve the XML element at the specified path
    foundGeometry = root.findall("def:entry/m:properties/d:ContentGeometry", ns)
    if len(foundGeometry) > 0:
        geomText: str = foundGeometry[0].text
        #geomText = geomText.replace("\n", "")
        foundGeoms[snapshotName] = geomText
        return geomText
    else:
        noGeoms.append(snapshotName)

#Iterate over found product names and make a request for each one
with open("snapshots.csv", mode="w") as f:
    for snapshot in snapshots:
        snapshot = snapshot
        geom = req(snapshot)
        if geom != None:
            f.write("{snapshot},\"{geom}\"\n".format(snapshot=snapshot, geom=geom.replace("\n", "")))

cur = conn.cursor()
#Insert the result into the database
cur.executemany("""INSERT INTO public."importedSnapshots" VALUES (%s, st_geomfromgml(%s))""", foundGeoms.items())
conn.commit()
cur.close()
conn.close()

print("found geoms for the following snapshots:\n ".join([x+ "\n" for x, y in foundGeoms.items()]))
print("found no geoms for the following snapshots:\n " + "\n".join([x+ "\n" for x in noGeoms]))

print("For {notFound} snapshots out of {total} was no geometry data available".format(notFound = len(noGeoms), total = len(snapshots)))


