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

	def setTile(self, tileset_name, tile_id, tile):
		# TODO: Add tileset, if it does not exist!
		for tileset_xml in self.xml.findall('tileset'):
			if tileset_xml.get('name') == tileset_name:
				# Remove possible old tile
				for tile_xml in tileset_xml.findall('tile'):
					if int(tile_xml.get('id')) == tile_id:
						tileset_xml.remove(tile_xml)
						break
				# Add new tile
				tile_xml_attribs = {'id': str(tile_id)}
				if tile.get('terrain'):
					tile_xml_attribs['terrain'] = tile['terrain']
				tile_xml = ElementTree.SubElement(tileset_xml, 'tile', attrib=tile_xml_attribs)
				# Add properties of tile
				if tile.get('properties') and len(tile['properties']) > 0:
					props_xml = ElementTree.SubElement(tile_xml, 'properties')
					for key, value in tile['properties'].items():
						ElementTree.SubElement(props_xml, 'property', attrib={
							'name': key,
							'value': value,
						})
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
	quit_and_save = False
	for tileset in tilesets:

		if quit_and_save:
			break

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

				# If there is only one variation of tile, then use it
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