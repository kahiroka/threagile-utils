#!/usr/bin/env python3

import sys
import yaml
import datetime
import json
from argparse import ArgumentParser

class SchemaUtils():
  def __init__(self, debug=False):
    self.debug_flag = debug
    self.add_sample = False
    self.add_item = False

  def debug(self, d, msg):
    if self.debug_flag:
      print('  '*d + msg)

  def addSample(self, flag):
    self.add_sample = flag

  def genValue(self, schema):
    if 'enum' in schema:
      return schema['enum'][0]
    elif 'format' in schema and schema['format'] == 'date':
      return '1970-01-01'
    elif 'format' in schema and schema['format'] == 'date-time':
      return '1970-01-01T00:00:00Z'
    elif 'format' in schema and schema['format'] == 'uri':
      return 'http://example.com/'
    elif schema['type'] == 'string':
      return 'string'
    elif type(schema['type']) == list and 'string' in schema['type']:
      return 'string'
    elif schema['type'] == 'boolean':
      return False
    elif type(schema['type']) == list and 'boolean' in schema['type']:
      return False
    else:
      return None
 
  def complement(self, schema, target=None, d=0):
    self.debug(d, str(schema.keys()))
    t = target if target != None else {}

    if 'required' in schema:
      self.debug(d, '[required]')
      for sk in schema['required']:
        self.debug(d, sk)
        if not sk in t:
          t[sk] = None
        t[sk] = self.complement(schema['properties'][sk], t[sk], d=d+1)
      return t

    elif 'additionalProperties' in schema and type(schema['additionalProperties']) != bool:
      self.debug(d, '[additional properties]')
      if target == None and self.add_sample:
        self.debug(d, '->add a sample')
        t['Sample'] = self.complement(schema['additionalProperties'], d=d+1)
        return t
      else:
        for tk in t:
          self.debug(d, tk)
          t[tk] =  self.complement(schema['additionalProperties'], t[tk], d=d+1)
        return t

    elif self.add_item and 'items' in schema:
      self.debug(d, '[items]')
      return t if target != None else [self.complement(schema['items'], d=d+1)]

    else:
      self.debug(d, '->add a value')
      return t if target != None else self.genValue(schema)

def getArgs():
  usage = '''
schemautils.py -schema schema.json -json minimum.json -out complemented.json [-addsample]
schemautils.py -schema schema.json -yaml minimum.yaml -out complemented.yaml [-addsample]
'''
  argparser = ArgumentParser(usage=usage)
  argparser.add_argument('-schema', nargs='?', type=str, dest='schema', help='schema json file')
  argparser.add_argument('-yaml', nargs='?', type=str, dest='yaml', help='yaml file')
  argparser.add_argument('-json', nargs='?', type=str, dest='json', help='json file')
  argparser.add_argument('-out', nargs='?', type=str, dest='out', help='output file')
  argparser.add_argument('-verbose', action='store_true', dest='verbose', help='verbose mode')
  argparser.add_argument('-addsample', action='store_true', dest='addsample', help='add sample')
  return argparser.parse_args()

def main():
  args = getArgs()

  if args.schema and args.yaml and args.out:
    with open(args.schema) as y:
      schema = json.load(y)
    with open(args.yaml) as y:
      target = yaml.safe_load(y)
    su = SchemaUtils(debug=args.verbose)
    su.addSample(args.addsample)
    target = su.complement(schema, target)
    with open(args.out, 'w') as f:
      yaml.dump(target, f, default_flow_style=False, allow_unicode=True)

  elif args.schema and args.json and args.out:
    with open(args.schema) as y:
      print(args.schema, file=sys.stderr)
      schema = json.load(y)
    with open(args.json) as y:
      target = json.load(y)
    su = SchemaUtils(debug=True)
    su.addSample(args.addsample)
    target = su.complement(schema, target)
    with open(args.out, 'w') as f:
      json.dump(target, f, indent=2)

if __name__ == '__main__':
  main()
