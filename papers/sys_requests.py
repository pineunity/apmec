import yaml

import os
from random import randint
from numpy import random as random_choice
import sys
import ast

# it should return two template for the cooperation and separation approaches
base_path = os.path.dirname(os.path.abspath(__file__))

line_index = sys.argv[1]


def coop_import_requirements(sample, req_list):
    path = base_path + '/' + sample
    with open(path, 'r') as f:
      sample_dict = yaml.safe_load(f.read())

    sample_dict['imports']['nsds']['nsd_templates']['requirements'] = req_list

    with open(path, 'w') as f:
        yaml.safe_dump(sample_dict, f)


def sepa_import_requirements(sample, req_list):
    base_path = os.path.dirname(os.path.abspath(__file__))
    path = base_path + '/' + sample
    with open(path, 'r') as f:
      sample_dict = yaml.safe_load(f.read())

    sample_dict['topology_template'] = dict()
    sample_dict['topology_template']['node_templates'] = dict()
    sample_dict['imports'] = list()
    # req_list is list odf vnfdson edge2
    for sepa_sample in req_list:
        vnfd_sample = sepa_sample['vnfd_template'] + '-' + 'edge2'
        sample_dict['imports'].append(vnfd_sample)
        node_dict = dict()
        node_dict[sepa_sample['name']] = dict()
        node_dict[sepa_sample['name']]['type'] = 'tosca.nodes.nfv.' + sepa_sample['name']
        sample_dict['topology_template']['node_templates'].update(node_dict)

    with open(path, 'w') as f:
        yaml.safe_dump(sample_dict, f)


req_path = base_path + '/' + 'requests.txt'
with open(req_path, 'r') as f:
        lines = f.readlines()
        target_line = lines[int(line_index)]
        tosca_req_list = ast.literal_eval(target_line)

coop_import_requirements(sample='coop-mesd.yaml', req_list=tosca_req_list)
sepa_import_requirements(sample='sepa-nsd.yaml', req_list=tosca_req_list)



