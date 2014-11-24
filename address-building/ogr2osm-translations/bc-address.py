#################################
#
# Baltimore city address translation
# 17 Nov 2014
# by @talllguy
# parts adapted from @pnorman's surreyroad.py translation
# https://github.com/pnorman/ogr2osm-translations/blob/master/surreyroad.py
#
#################################

def translateType(stType):
    suffixlookup = {}

    # street names see gist:
    # https://gist.github.com/talllguy/c0f853c04e76ac7178f0

    suffixlookup.update({'AL':'Alley'})
    suffixlookup.update({'ALY':'Alley'})
    suffixlookup.update({'AVE':'Avenue'})
    suffixlookup.update({'BLVD':'Boulevard'})
    suffixlookup.update({'CIR':'Circle'})
    suffixlookup.update({'CT':'Court'})
    suffixlookup.update({'DR':'Drive'})
    suffixlookup.update({'DWY':'Driveway'})
    suffixlookup.update({'GARTH':'Garth'})
    suffixlookup.update({'GLN':'Glen'})
    suffixlookup.update({'GRDNS':'Gardens'})
    suffixlookup.update({'HWY':'Highway'})
    suffixlookup.update({'LANE':'Lane'})
    suffixlookup.update({'LN':'Lane'})
    suffixlookup.update({'LNDG':'Landing'})
    suffixlookup.update({'MALL':'Mall'})
    suffixlookup.update({'MEWS':'Mews'})
    suffixlookup.update({'PASS':'Pass'})
    suffixlookup.update({'PATH':'Path'})
    suffixlookup.update({'PIKE':'Pike'})
    suffixlookup.update({'PL':'Place'})
    suffixlookup.update({'PLZ':'Plaza'})
    suffixlookup.update({'PT':'Point'})
    suffixlookup.update({'RD':'Road'})
    suffixlookup.update({'ROAD':'Road'})
    suffixlookup.update({'RUN':'Run'})
    suffixlookup.update({'SQ':'Square'})
    suffixlookup.update({'ST':'Street'})
    suffixlookup.update({'TER':'Terrace'})
    suffixlookup.update({'TERR':'Terrace'})
    suffixlookup.update({'WALK':'Walk'})
    suffixlookup.update({'WAY':'Way'})
    suffixlookup.update({'XING':'Crossing'})

    stTypeExpanded = ''
    stTypeExpanded = suffixlookup.get(stType)

    return stTypeExpanded

def caseStreetName(stName):

    address = stName
    stNameCased = ' '.join([word.capitalize() for word in address.split()])

    return stNameCased

def translateDirection(dirAbbr):
    suffixlookup = {}

    # Directions

    suffixlookup.update({'E':'East'})
    suffixlookup.update({'S':'South'})
    suffixlookup.update({'N':'North'})
    suffixlookup.update({'W':'West'})

    dirExpanded = ''
    dirExpanded = suffixlookup.get(dirAbbr)

    return dirExpanded


def filterTags(attrs):
    if not attrs: return

    tags = {}

    #automagically convert names
    x = ''
    y = ''

    if attrs['ST_NAME']:
        tags.update({'addr:street':' '.join([x for x in (
            translateDirection(attrs['ST_DIR']),
            caseStreetName(attrs['ST_NAME']),
            translateType(attrs['ST_TYPE'])
            ) if x])
        })
        tags.update({'addr:city':'Baltimore'})
        tags.update({'addr:state':'MD'})
        tags.update({'addr:country':'US'})

    if attrs['ADDR_NUMBE'] != '0':
       tags.update({'addr:housenumber':' '.join([y for y in (
            attrs['ADDR_NUMBE'],
            attrs['ADDR_FRAC']) if y])
            })

    if attrs['ZIP_CODE']:
        tags.update({'addr:postcode':attrs['ZIP_CODE']})

    return tags
