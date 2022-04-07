#!/usr/bin/env python3

import yaml
import json
import hashlib
from argparse import ArgumentParser

class ThreagileModel():
  def __init__(self, modelfile, debug=False):
    self.debug_flag = debug
    with open(modelfile) as f:
      self.model = yaml.safe_load(f)
      self.data_assets = {}
      for name in self.model['data_assets']:
        id = self.model['data_assets'][name]['id']
        self.data_assets[id] = {}
        self.data_assets[id]['name'] = name
        self.data_assets[id]['cia'] = self._getCIAFlag(self.model['data_assets'][name])

      self.bound_root = {}
      self._initTechAssetTree()

  def debug(self, msg):
    if self.debug_flag:
      print(msg)

  def _getCIAFlag(self, data_asset):
    c = 'c' if data_asset['confidentiality'] in ['confidential', 'strictly-confidential'] else '-'
    i = 'i' if data_asset['integrity'] in ['critical', 'mission-critical'] else '-'
    a = 'a' if data_asset['availability'] in ['critical', 'mission-critical'] else '-'      
    return c+i+a

  def _getNZFlag(self, link):
    n = 'n' if link['authentication'] != 'none' else '-'
    z = 'z' if link['authorization'] != 'none' else '-'
    return n+z

  def _getFlagsEachDataAsset(self, tech_id):
    flagset = {}
    if self.model['technical_assets'][tech_id]['data_assets_processed'] != None:
      for data_id in self.model['technical_assets'][tech_id]['data_assets_processed']:
        if not data_id in flagset:
          flagset[data_id] = {'s':'-', 'r':'-', 'p':'-', 'h':'-'}
        flagset[data_id]['p'] = 'p'

    if self.model['technical_assets'][tech_id]['data_assets_stored'] != None:
      for data_id in self.model['technical_assets'][tech_id]['data_assets_stored']:
        if not data_id in flagset:
          flagset[data_id] = {'s':'-', 'r':'-', 'p':'-', 'h':'-'}
        flagset[data_id]['h'] = 'h'

    links = self.model['technical_assets'][tech_id]['communication_links']
    if links != None:
      for link_name in links:
        if links[link_name]['data_assets_received'] != None:
          for data_id in links[link_name]['data_assets_received']:
            if not data_id in flagset:
              flagset[data_id] = {'s':'-', 'r':'-', 'p':'-', 'h':'-'}
            flagset[data_id]['r'] = 'r'
        if links[link_name]['data_assets_sent'] != None:
          for data_id in links[link_name]['data_assets_sent']:
            if not data_id in flagset:
              flagset[data_id] = {'s':'-', 'r':'-', 'p':'-', 'h':'-'}
            flagset[data_id]['s'] = 's'

    flagset_ret = {}
    for data_id in flagset:
      flagset_ret[data_id] = flagset[data_id]['s']+flagset[data_id]['r']+flagset[data_id]['p']+flagset[data_id]['h']

    return flagset_ret

  def _getStyle(self, name):
    styleset = ['solid', 'dashed', 'bold']
    style = styleset[int('0x' + hashlib.md5((name+'style').encode("utf-8")).hexdigest(), 16) % len(styleset)]
    return style

  def _getColor(self, name):
    colorset = ['black', 'red', 'blue']
    color = colorset[int('0x' + hashlib.md5((name+'color').encode("utf-8")).hexdigest(), 16) % len(colorset)]
    return color

  def _craftAssetTree(self, root):
    if root != {}:
      for bound_id in dict(root['bounds']):
        if root['name'] != 'root' and bound_id in self.bound_root['bounds']:
          root['bounds'][bound_id] = self.bound_root['bounds'].pop(bound_id)
        else:
          if bound_id in root['bounds']:
            root['bounds'][bound_id] = self._craftAssetTree(root['bounds'][bound_id])
    return root

  def _initTechAssetTree(self):
    self.bound_root['name'] = 'root'
    self.bound_root['tech_assets'] = []
    self.bound_root['registered'] = []
    self.bound_root['bounds'] = {}

    for name in self.model['trust_boundaries']:
      id = self.model['trust_boundaries'][name]['id']
      assets = self.model['trust_boundaries'][name]['technical_assets_inside']
      self.bound_root['registered'].extend(assets)
      if 'trust_boundaries_nested' in self.model['trust_boundaries'][name]:
        bounds = self.model['trust_boundaries'][name]['trust_boundaries_nested']
      else:
        bounds = []
      self.bound_root['bounds'][id] = {}
      self.bound_root['bounds'][id]['name'] = name
      self.bound_root['bounds'][id]['tech_assets'] = assets
      self.bound_root['bounds'][id]['bounds'] = {}
      if bounds != None:
        for b in bounds:
          self.bound_root['bounds'][id]['bounds'][b] = {}

    for name in self.model['technical_assets']:
      if not self.model['technical_assets'][name]['id'] in self.bound_root['registered']:
        self.bound_root['tech_assets'].append(self.model['technical_assets'][name]['id'])

    self.bound_root = self._craftAssetTree(self.bound_root)
    self.debug(json.dumps(self.bound_root, indent=2))

  def getTechAssetNameById(self, id):
    for name in self.model['technical_assets']:
      if self.model['technical_assets'][name]['id'] == id:
        return name
    return None

  def _writeTechAssets(self, bound_root, f):
    if bound_root != {}:
      for tech_id in bound_root['tech_assets']:
        tech_name = self.getTechAssetNameById(tech_id)
        style = 'filled' if self.model['technical_assets'][tech_name]['out_of_scope'] == True else 'solid'
        print('node [style=' + style + ']', file=f)
        print(tech_id.replace('-','_'), end='', file=f)
        print('[label = <{<b>' + tech_name + '</b>', end='', file=f)
        flagset = self._getFlagsEachDataAsset(tech_name)
        for data_id in flagset:
          print(' | ' + self.data_assets[data_id]['name'], end='', file=f)
          print(' ' + self.data_assets[data_id]['cia'], end='', file=f)
          print(' ' + flagset[data_id], end='', file=f)
        print('}>]', file=f)

      for bound_id in dict(bound_root['bounds']):
        print('subgraph cluster_' + bound_id.replace('-','_') + ' {', file=f)
        print('label="' + bound_root['bounds'][bound_id]['name'] + '"', file=f)
        self._writeTechAssets(bound_root['bounds'][bound_id], f)
        print('}', file=f)

  def _writeLinks(self, f):
    for tech_name in self.model['technical_assets']:
      links = self.model['technical_assets'][tech_name]['communication_links']
      if links != None:
        for link_name in links:
          print(self.model['technical_assets'][tech_name]['id'].replace('-','_'), end='', file=f)
          print(' -> ', end='', file=f)
          print(links[link_name]['target'].replace('-','_'), end='', file=f)
          print('[label=<' + links[link_name]['protocol'].replace('-','_'), end='', file=f)
          print(' ' + self._getNZFlag(links[link_name]), end='', file=f)
          print('>style=' + self._getStyle(links[link_name]['target']), end='', file=f)
          print(',color=' + self._getColor(links[link_name]['target']) + ']', file=f)

  def writeDot(self, dotfile):
    with open(dotfile, 'w') as f:
      print('digraph test_diagram {', file=f)
      print('label="' + self.model['title'] + '"', file=f)
      print('node [shape=record]', file=f)

      print('usage_guide1[label = <{<b>Asset Guide</b>', end='', file=f)
      print(' | Confidentiality c-- | Integrity -i- | Availability --a', end='', file=f)
      print(' | Sent Asset s--- | Received Asset -r-- | Processed Asset --p- | Stored Asset ---h}>]', file=f)
      print('usage_guide3[label = <{<b>Flow Guide</b> | Authentication n- | Authorization -z}>]', file=f)

      self._writeTechAssets(self.bound_root, f)
      self._writeLinks(f)

      print('}', file=f)

def getArgs():
  usage = '''
model2dot.py -yaml threagile-model.yaml -out data-flow-diagram.dot [-verbose]
'''
  argparser = ArgumentParser(usage=usage)
  argparser.add_argument('-yaml', nargs='?', type=str, dest='yaml', help='yaml file')
  argparser.add_argument('-out', nargs='?', type=str, dest='out', help='output file')
  argparser.add_argument('-verbose', action='store_true', dest='verbose', help='verbose mode')
  return argparser.parse_args()

def main():
  args = getArgs()

  if args.yaml and args.out:
    tm = ThreagileModel(args.yaml, debug=args.verbose)
    tm.writeDot(args.out)

if __name__ == '__main__':
  main()
