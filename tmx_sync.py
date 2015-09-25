#!/usr/bin/python
import sys
import json
import os.path
from xml.etree import ElementTree


class TmxFile:

    def __init__(self, path):
        self.path = path
        self.xml = ElementTree.parse(path)
        self.changed = False

    def save(self):
        if self.changed:
            self.xml.write(self.path)

    def getTilesets(self):
        tilesets = []
        for tileset_xml in self.xml.findall('tileset'):
            tilesets.append({
                'name': tileset_xml.get('name'),
                'tilewidth': int(tileset_xml.get('tilewidth')),
                'tileheight': int(tileset_xml.get('tileheight')),
                'firstgid': int(tileset_xml.get('firstgid')),
                'image': tileset_xml.find('image').get('source'),
                'image_width': tileset_xml.find('image').get('width'),
                'image_height': tileset_xml.find('image').get('height'),
            })
        return tilesets

    def getTileIds(self, tileset_name):
        for tileset_xml in self.xml.findall('tileset'):
            if tileset_xml.get('name') == tileset_name:
                return [int(tile_xml.get('id')) for tile_xml in tileset_xml.findall('tile')]
        return []

    def setTile(self, tileset_name, tile_id, tile):
        # TODO: Add tileset, if it does not exist!
        for tileset_xml in self.xml.findall('tileset'):
            if tileset_xml.get('name') == tileset_name:
                # Remove possible old tile
                old_tile = None
                for tile_xml in tileset_xml.findall('tile'):
                    if int(tile_xml.get('id')) == tile_id:
                        old_tile = self.getTile(tileset_name, tile_id)
                        tileset_xml.remove(tile_xml)
                        break
                # Add new tile
                tile_xml_attribs = {'id': str(tile_id)}
                new_tile_has_non_default_values = False
                if tile.get('terrain'):
                    tile_xml_attribs['terrain'] = tile['terrain']
                    new_tile_has_non_default_values = True
                if tile.get('probability') and float(tile['probability']) < 1.0:
                    tile_xml_attribs['probability'] = tile['probability']
                    new_tile_has_non_default_values = True
                if tile.get('properties') and len(tile['properties']) > 0:
                    new_tile_has_non_default_values = True
                # Add tile only if it has non default values
                if new_tile_has_non_default_values:
                    tile_xml = ElementTree.SubElement(tileset_xml, 'tile', attrib=tile_xml_attribs)
                    # Add properties of tile
                    if tile.get('properties') and len(tile['properties']) > 0:
                        props_xml = ElementTree.SubElement(tile_xml, 'properties')
                        for key, value in tile['properties'].items():
                            ElementTree.SubElement(props_xml, 'property', attrib={
                                'name': key,
                                'value': value,
                            })
                # Check if tile was changed
                if not old_tile and new_tile_has_non_default_values:
                    self.changed = True
                elif old_tile is not None:
                    if old_tile.get('terrain') != tile.get('terrain'):
                        self.changed = True
                    elif float(old_tile.get('probability', 1)) != float(tile.get('probability', 1)):
                        self.changed = True
                    elif old_tile.get('properties', {}) != tile.get('properties', {}):
                        self.changed = True
                    elif not new_tile_has_non_default_values:
                        self.changed = True
                break

    def getTile(self, tileset_name, tile_id):
        for tileset_xml in self.xml.findall('tileset'):
            if tileset_xml.get('name') == tileset_name:
                tiles_xml = tileset_xml.findall('tile')
                tile_xml = None
                for tile_idx in range(len(tiles_xml)):
                    if int(tiles_xml[tile_idx].get('id')) == tile_id:
                        tile_xml = tiles_xml[tile_idx]
                        break
                if tile_xml is None:
                    return None

                result = {}

                props_xml = tile_xml.find('properties')
                if props_xml is not None:
                    props = {}
                    for prop_xml in props_xml.findall('property'):
                        props[prop_xml.get('name')] = prop_xml.get('value')
                    result['properties'] = props

                if tile_xml.get('terrain'):
                    result['terrain'] = tile_xml.get('terrain')

                if tile_xml.get('probability'):
                    result['probability'] = tile_xml.get('probability')

                return result

        raise RuntimeError('Tileset "' + tileset_name + '" does not exist in ' + self.path)

        tileset = self.xml.findall('tileset').get(tile_idx, None)

    def getTerrains(self, tileset_name):
        for tileset_xml in self.xml.findall('tileset'):
            if tileset_xml.get('name') == tileset_name:
                result = []
                terraintypes_xml = tileset_xml.find('terraintypes')
                if terraintypes_xml is not None:
                    for terraintype_xml in terraintypes_xml.findall('terrain'):
                        result.append(terraintype_xml.get('name'))
                return result
        raise RuntimeError('Tileset "' + tileset_name + '" does not exist in ' + self.path)

    def setTerrains(self, tileset_name, terrains):
        # If terrains does not differ, then do nothing
        if terrains == self.getTerrains(tileset_name):
            return

        for tileset_xml in self.xml.findall('tileset'):
            if tileset_xml.get('name') == tileset_name:
                terraintypes_xml = tileset_xml.find('terraintypes')
                if terraintypes_xml is not None:
                    # If old node can be found, then empty it, so it can be used again
                    for terraintype_xml in terraintypes_xml.findall('terrain'):
                        terraintypes_xml.remove(terraintype_xml)
                else:
                    # Old node was not found, so we need to create a new
                    # one. Tiled does not like if it's done to the end.
                    # TODO: Code this!
                    pass

                # Add terrains
                for terrain in terrains:
                    ElementTree.SubElement(terraintypes_xml, 'terrain', attrib={
                        'name': terrain,
                        'tile': '-1',
                    })
                self.changed = True
                return
        raise RuntimeError('Tileset "' + tileset_name + '" does not exist in ' + self.path)


def main():

    # File names that should be synced
    tmxfiles_paths = sys.argv[1:]

    # Open all files
    tmxfiles = [TmxFile(path) for path in tmxfiles_paths]

    # Make sure all TMX files have same Tilesets, but do not check tiles yet
    tilesets = []
    for tmxfile in tmxfiles:
        for tmxfile_tileset in tmxfile.getTilesets():
            if tmxfile_tileset not in tilesets:
                tilesets.append(tmxfile_tileset)
    # TODO: Make sure tilesets are the same!

    # Now go all tilesets through and sync them
    quit_and_save = False
    for tileset in tilesets:

        if quit_and_save:
            break

        # Gather all terrains
        all_terrains = []
        terrain_conflicts_found = False
        for tmxfile in tmxfiles:
            terrains = tmxfile.getTerrains(tileset['name'])
            for terrain_id in range(len(terrains)):
                terrain = terrains[terrain_id]
                if terrain_id == len(all_terrains):
                    # A new terrain
                    all_terrains.append(terrain)
                elif all_terrains[terrain_id] != terrain:
                    # Conflict
                    print 'ERROR: Terrains at #' + str(terrain_id) + ' conflict! ' + all_terrains[terrain_id] + ' vs. ' + terrain
                    # TODO: Instead of error, ask user what to do!
                    terrain_conflicts_found = True
        if terrain_conflicts_found:
            raise RuntimeError('Conflicts with terrains found!')
        # Synchronize terrains
        for tmxfile in tmxfiles:
            tmxfile.setTerrains(tileset['name'], all_terrains)

        # Get all tile IDs from this tileset from every TMX file
        tile_ids_set = set()
        for tmxfile in tmxfiles:
            tile_ids_set |= set(tmxfile.getTileIds(tileset['name']))

        # Go all tiles through
        for tile_id in tile_ids_set:
            # Get all different instances of this tile
            tiles = []
            tiles_users = []
            total_users = 0
            for tmxfile in tmxfiles:
                tile = tmxfile.getTile(tileset['name'], tile_id)
                if tile:
                    if tile not in tiles:
                        tiles.append(tile)
                        tiles_users.append([tmxfile.path])
                    else:
                        tiles_users[tiles.index(tile)].append(tmxfile.path)
                    total_users += 1

            # If there is conflict
            if len(tiles) > 1:
                print 'There is a conflict in tile ' + tileset['name'] + '/' + str(tile_id) + '!'
                print
                print 'Select which tile to use:'
                for option in range(len(tiles)):
                    print str(option + 1) + ') ' + json.dumps(tiles[option]) + ' used by: ' + ', '.join([os.path.basename(user) for user in tiles_users[option]])
                print 'c) clear this tile from all maps'
                print 's) skip this tile'
                print 'q) save and quit'
                choice_str = raw_input('')
                if choice_str == 'c':
                    for tmxfile2 in tmxfiles:
                        tmxfile2.setTile(tileset['name'], tile_id, {})
                    print
                    continue
                if choice_str == 'q':
                    quit_and_save = True
                    break
                try:
                    choice = int(choice_str) - 1
                except:
                    choice = -1
                if choice >= 0 and choice < len(tiles):
                    for tmxfile2 in tmxfiles:
                        if tmxfile2.path not in tiles_users[choice]:
                            tmxfile2.setTile(tileset['name'], tile_id, tiles[choice])
                    print
                    continue
                print

            # If some of maps is missing the tile
            if total_users != len(tmxfiles):
                missing = []
                for tmxfile in tmxfiles:
                    if tile_id not in tmxfile.getTileIds(tileset['name']):
                        missing.append(tmxfile)
                print 'Tile ' + tileset['name'] + '/' + str(tile_id) + ' is missing from ' + ', '.join([os.path.basename(tmxfile2.path) for tmxfile2 in missing]) + '!'

                print
                print 'Select which tile to use:'
                for option in range(len(tiles)):
                    print str(option + 1) + ') ' + json.dumps(tiles[option]) + ' used by: ' + ', '.join([os.path.basename(user) for user in tiles_users[option]])
                print 'c) clear this tile from all maps'
                print 's) skip this tile'
                print 'q) save and quit'
                choice_str = raw_input('')
                if choice_str == 'c':
                    for tmxfile2 in tmxfiles:
                        tmxfile2.setTile(tileset['name'], tile_id, {})
                if choice_str == 'q':
                    quit_and_save = True
                    break
                try:
                    choice = int(choice_str) - 1
                except:
                    choice = -1
                if choice >= 0 and choice < len(tiles):
                    for tmxfile2 in missing:
                        tmxfile2.setTile(tileset['name'], tile_id, tiles[choice])
                print

                # TODO: Add missing tiles

    # TODO: Sync terraintypes!

    # Finally save TmxFiles
    for tmxfile in tmxfiles:
        tmxfile.save()

if __name__ == '__main__':
    main()
