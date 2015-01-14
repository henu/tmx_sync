#!/usr/bin/python
import sys
import json
import os.path
from xml.etree import ElementTree

class TmxFile:

	def __init__(self, path):
		self.path = path
		self.xml = ElementTree.parse(path)

	def getTilesetsWithoutTiles(self):
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

				props_xml = tile_xml.find('properties')
				props = {}
				if props_xml is not None:
					for prop_xml in props_xml.findall('property'):
						props[prop_xml.get('name')] = prop_xml.get('value')

				return {
					'terrain': tile_xml.get('terrain'),
					'properties': props,
				}

		raise RuntimeError('Tileset "' + tileset_name + '" does not exist in ' + self.path)

		tileset = self.xml.findall('tileset').get(tile_idx, None)


def main():

	# File names that should be synced
	tmxfiles_paths = sys.argv[1:]

	# Open all files
	tmxfiles = [TmxFile(path) for path in tmxfiles_paths]

	# Make sure all TMX files have same Tilesets, but do not check tiles yet
	tilesets = []
	for tmxfile in tmxfiles:
		for tmxfile_tileset in tmxfile.getTilesetsWithoutTiles():
			if tmxfile_tileset not in tilesets:
				tilesets.append(tmxfile_tileset)
	# TODO: Make sure tilesets are the same!

	# Now go tiles through from all tilesets, and ensure they are the same
	for tileset in tilesets:

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
				for conflict_idx in range(len(tiles)):
					print str(conflict_idx + 1) + ') ' + json.dumps(tiles[conflict_idx]) + ' used by: ' + ', '.join([os.path.basename(user) for user in tiles_users[conflict_idx]])
					# TODO: Solve conflict

			# If some of maps is missing the tile
			if total_users != len(tmxfiles):
				missing = []
				for tmxfile in tmxfiles:
					if tile_id not in tmxfile.getTileIds(tileset['name']):
						missing.append(os.path.basename(tmxfile.path))
				print 'Tile ' + tileset['name'] + '/' + str(tile_id) + ' is missing from ' + ', '.join(missing) + '!'
				# TODO: Add missing tiles

	# TODO: Sync terraintypes!

if __name__ == '__main__':
	main()