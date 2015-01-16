#################################
#
# Baltimore city street centerline translation
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
    import re

    # capitalize each word that is separated by a space
    address = stName
    stNameCased = ' '.join([word.capitalize() for word in address.split()])

    # special names that need to be replaced
    rep = {"O'donnell": "O'Donnell", "Mcallister": "McAllister",
        "Mccabe": "McCabe", "Mcclean": "McClean",
        "Mccollough": "McCollough", "Mccomas": "McComas",
        "Mcculloh": "McCulloh", "Mccurley": "McCurley",
        "Mcdonogh": "McDonogh", "Mcelderry": "McElderry",
        "Mchenry": "McHenry", "Mckay": "McKay",
        "Mckean": "McKean", "Mckendree": "McKendree",
        "Mckewin": "McKewin", "Mcmechen": "McMechen",
        "Mcphail": "McPhail", "Mcteague": "McTeague",
        "St.": "Saint", "St Paul": "Saint Paul",
        "St Matthews": "Saint Matthews"}

    # replace any of the rep names above
    # code source from http://stackoverflow.com/a/6117124/2105596
    rep = dict((re.escape(k), v) for k, v in rep.iteritems())
    pattern = re.compile("|".join(rep.keys()))
    stNameCased = pattern.sub(lambda m: rep[re.escape(m.group(0))], stNameCased)

    return stNameCased

def translateDirection(dirAbbr):
    suffixlookup = {}

    # Directionals that need to be expanded. The code replaces the
    # item before the colon with the one after.

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

    # clear vars
    x = ''
    y = ''

    # tags for all roads
    tags.update({'addr:city':'Baltimore'})
    tags.update({'addr:state':'MD'})
    tags.update({'addr:country':'US'})
    tags.update({'addr:block':attrs['BLOCK_NUM']})

    # street name translations
    tags.update({'name':' '.join([x for x in (
        translateDirection(attrs['DIRPRE']),
        caseStreetName(attrs['FEANME']),
        translateType(attrs['FEATYPE']),
        translateDirection(attrs['DIRSUF'])
        ) if x])
    })

    # convert names if there is a name
    if 'SUBTYPE' in attrs:
        # classifications
        if attrs['SUBTYPE'] == "STRALY": #alley
            tags.update({'highway':'service'})
            tags.update({'service':'alley'})
        elif attrs['SUBTYPE'] == "STREX": # expressway
            if attrs['SHA_CLASS'] == "FWY":
                tags.update({'highway':'trunk'})
            elif attrs['SHA_CLASS'] == "INT":
                tags.update({'highway':'motorway'})
            elif attrs['SHA_CLASS'] == "PART":
                tags.update({'highway':'primary'})
        elif attrs['SUBTYPE'] == "STRFIC": # not sure what 'fic' is, but these are mostly ped streets
            tags.update({'highway':'pedestrian'})
        elif attrs['SUBTYPE'] == "STRNDR": # 'ndr' is probably non-drivable
            tags.update({'highway':'path'})
        elif attrs['SUBTYPE'] == "STRPRD": # regular roads
            if attrs['SHA_CLASS'] == "LOC":
                tags.update({'highway':'unclassified'})
            elif attrs['SHA_CLASS'] == "MART":
                tags.update({'highway':'secondary'})
            elif attrs['SHA_CLASS'] == "PART":
                tags.update({'highway':'primary'})
            elif attrs['SHA_CLASS'] == "COLL":
                tags.update({'highway':'tertiary'})
            else:
                tags.update({'highway':'residential'})
        elif attrs['SUBTYPE'] == "STRR": # ramps
            if attrs['SHA_CLASS'] == "FWY":
                tags.update({'highway':'trunk_link'})
            if attrs['SHA_CLASS'] == "LOC":
                tags.update({'highway':'tertiary_link'})
            if attrs['SHA_CLASS'] == "MART":
                tags.update({'highway':'secondary_link'})
            if attrs['SHA_CLASS'] == "PART":
                tags.update({'highway':'primary_link'})
            if attrs['SHA_CLASS'] == "INT":
                tags.update({'highway':'motorway_link'})
            else:
                tags.update({'highway':'road_link'}) # not a real link type
        elif attrs['SUBTYPE'] == "STRURB": # seems to be tracks
            tags.update({'highway':'track'})
        else:
            tags.update({'highway':'road'})

    return tags
