from typing import List

import pandas as pd


def coerceList(maybeList) -> List[str]:
    if type(maybeList) is str:
        return [maybeList]
    return maybeList

geojsons = {
    "Portugal": """{ "type": "Polygon","coordinates": [[[-10.27, 36.56], [-5.88, 36.52], [-5.86, 42.62], [-10.21, 42.62], [-10.27, 36.56]]]}""",
    "Ireland": """{ "type": "Polygon", "coordinates": [ [ [ -10.810546875, 51.72702815704774 ], [ -5.009765625, 51.72702815704774 ], [ -5.009765625, 55.92458580482951 ], [ -10.810546875, 55.92458580482951 ], [ -10.810546875, 51.72702815704774 ] ] ] }""",
    "Lithuania": """{ "type": "Polygon", "coordinates": [ [ [ 19.6435546875, 53.330872983017066 ], [ 27.685546874999996, 53.330872983017066 ], [ 27.685546874999996, 56.74067435475299 ], [ 19.6435546875, 56.74067435475299 ], [ 19.6435546875, 53.330872983017066 ] ] ] }""",
    "Finland": """{ "type": "Polygon", "coordinates": [ [ [ 16.787109375, 58.95000823335702 ], [ 33.75, 58.95000823335702 ], [ 33.75, 69.16255790810501 ], [ 16.787109375, 69.16255790810501 ], [ 16.787109375, 58.95000823335702 ] ] ] }""",
    "BeNeLux": """{ "type": "Polygon", "coordinates": [ [ [ 2.5927734375, 49.18170338770663 ], [ 7.163085937499999, 49.18170338770663 ], [ 7.163085937499999, 50.875311142200765 ], [ 2.5927734375, 50.875311142200765 ], [ 2.5927734375, 49.18170338770663 ] ] ] }""",
    "Serbia": """{ "type": "Polygon", "coordinates": [ [ [ 18.17138671875, 42.01665183556825 ], [ 23.97216796875, 42.01665183556825 ], [ 23.97216796875, 47.204642388766935 ], [ 18.17138671875, 47.204642388766935 ], [ 18.17138671875, 42.01665183556825 ] ] ] }""",
    "Switzerland": """{ "type": "Polygon", "coordinates": [ [ [ 7.492675781249999, 46.66451741754235 ], [ 9.2724609375, 46.66451741754235 ], [ 9.2724609375, 47.96050238891509 ], [ 7.492675781249999, 47.96050238891509 ], [ 7.492675781249999, 46.66451741754235 ] ] ] }""",
    "Austria": """{ "type": "Polygon", "coordinates": [ [ [ 11.66748046875, 45.5679096098613 ], [ 18.050537109375, 45.5679096098613 ], [ 18.050537109375, 49.95121990866204 ], [ 11.66748046875, 49.95121990866204 ], [ 11.66748046875, 45.5679096098613 ] ] ] }"""
}

countryOptions = [{'label': key, 'value': key} for key in geojsons.keys()]
#Define the tags as a tree like structure that we can transform later on
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

labelsTags= pd.DataFrame(columns=["label", "value", "color", "children"])
_temp = leveledTags.copy()
#Transforms the tree to a flat list via a depth-first search
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
    #Appends the parents name, if there are any
    label = current[0] + ("" if len(current) < 4 else " , part of {}".format(",".join(current[3])))
    labelsTags = labelsTags.append({"label": label ,
                                    "value": current[0],
                                    "color": [[0, 'rgb(255, 255, 255)'], [1, 'rgb({})'.format(current[1])]],
                                    "children": [childTuple[0] for childTuple in current[2]]}, ignore_index=True)




def powerset(s):
    x = len(s)
    masks = [1 << i for i in range(x)]
    for i in range(1 << x):
        yield [ss for mask, ss in zip(masks, s) if i & mask]
