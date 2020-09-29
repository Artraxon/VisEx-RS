import psycopg2
import pandas as pd
import database as db

# Imports the Grouped Tags into the database, has to be run manually
conn = psycopg2.connect(dbname=db.dbname, user=db.user, port=db.port, host=db.host, password=db.password)


leveledTags = [["Artificial Surfaces", "0, 0, 0",
                [["Urban Fabric", "63, 51, 24",
                  [["Continuous urban fabric", "", []],
                   ["Discontinuous urban fabric", "", []]
                   ]],
                 ["Industrial, commercial and transport units", "0, 0, 0",
                  [["Industrial or commercial units", "", []],
                   ["Road and rail networks and associated land", "", []],
                   ["Port areas", "", []],
                   ["Airports", "", []]
                   ]],
                 ["Mine, dump and construction sites", "149, 79, 0",
                  [["Mineral extraction sites", "", []],
                   ["Dump sites", "", []],
                   ["Construction sites", "", []]
                   ]],
                 ["Artificial, non-agricultural vegetated areas", "82, 141, 75",
                  [["Green urban areas", "", []],
                   ["Sport and leisure facilities", "", []]
                   ]]
                 ]],
               ["Agricultural areas", "255, 232, 0",
                [["Arable land", "255, 232, 0",
                  [["Non-irrigated arable land", "", []],
                   ["Permanently irrigated land", "", []],
                   ["Rice fields", "", []]
                   ]],
                 ["Permanent crops", "240, 0, 48",
                  [["Vineyards", "", []],
                   ["Fruit trees and berry plantations", "", []],
                   ["Olive groves", "", []]
                   ]],
                 ["Pastures", "22, 212, 31",
                  [["Pastures", "", []]
                   ]],
                 ["Heterogeneous agricultural areas", "212, 183, 22",
                  [["Annual crops associated with permanent crops", "", []],
                   ["Complex cultivation patterns", "", []],
                   ["Land principally occupied by agriculture, with significant areas of natural vegetation", "", []],
                   ["Agro-forestry areas", "", []]
                   ]]]],
               ["Forest and semi natural areas", "5, 143, 49",
                [["Forest", "", [
                    ["Broad-leaved forest", "", []],
                    ["Coniferous forest", "", []],
                    ["Mixed forest", "", []]
                ]],
                 ["Shrub and/or herbaceous vegetation associations", "", [
                     ["Natural grassland", "", []],
                     ["Moors and heathland", "", []],
                     ["Sclerophyllous vegetation", "", []],
                     ["Transitional woodland/scrub", "", []]
                 ]],
                 ["Open spaces with little or no vegetation", "", [
                     ["Beaches, dunes, sands", "", []],
                     ["Bare rock", "", []],
                     ["Sparsely vegetated areas", "", []],
                     ["Burnt areas", "", []],
                     ["Glaciers and perpetual snow", "", []]
                 ]]
                 ]],
               ["Wetlands", "5, 129, 143",
                [["Inland wetlands", "", [
                    ["Inland marshes", "", []],
                    ["Peatbogs", "", []]
                ]],
                 ["Coastal wetlands", "", [
                     ["Salt marshes", "", []],
                     ["Salines", "", []],
                     ["Intertidal flats", "", []]
                 ]]
                 ]],
               ["Water bodies", "0, 155, 245",
                [["Inland waters", "", [
                    ["Water courses", "", []],
                    ["Water bodies", "", []]
                ]],
                 ["Marine waters", "", [
                     ["Coastal lagoons", "", []],
                     ["Estuaries", "", []],
                     ["Sea and ocean", "", []]
                 ]] ]]]

cur: psycopg2._psycopg.cursor = conn.cursor()
labelsTags= pd.DataFrame(columns=["label", "value", "color", "children"])
_temp = leveledTags.copy()
while len(_temp) > 0:
    current = _temp.pop()
    for child in current[2]:
        #If no color is set for child, inherit color of parent tag
        if child[1] == "":
            child[1] = current[1]
        #Save reference to parent tag
        child.append([current[0]])
        _temp.append(child)
        #And to all parents of the current tag
        if len(current) == 4:
            for parent in current[3]:
                child[3].append(parent)
    label = current[0] + ("" if len(current) < 4 else " , part of {}".format(",".join(current[3])))
    if len(current) == 4:
        cur.execute("INSERT INTO label_hierarchy VALUES(%s, %s)", (current[3], current[0]))
    labelsTags = labelsTags.append({"label": label ,
                                    "value": current[0],
                                    "color": [[0, 'rgb(255, 255, 255)'], [1, 'rgb({})'.format(current[1])]],
                                    "children": [childTuple[0] for childTuple in current[2]]}, ignore_index=True)


conn.commit()
cur.close()
conn.close()