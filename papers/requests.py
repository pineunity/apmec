import yaml

import os
from random import randint
import random
from numpy import random as random_choice

# it should return two template for the cooperation and separation approaches
base_path = os.path.dirname(os.path.abspath(__file__))


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


VNF1 = ['vnfd11', 'vnfd12', 'vnfd13']

VNF2 = ['vnfd21', 'vnfd22', 'vnfd23']


VNF3 = ['vnfd31', 'vnfd32', 'vnfd33']

VNF4 = ['vnfd41', 'vnfd42', 'vnfd43']

VNF5 = ['vnfd51', 'vnfd52', 'vnfd53']

VNF6 = ['vnfd61', 'vnfd62', 'vnfd63']

sys_Nmax = 6  # Number of NFs -- > Maximum of NFs
vm_capacity = 3
min_resue = 0.5  # Set the reuse factor of the NS
req_Nmax = 3
req_Nmax_ins = 3

# Set the number of NF instances for NFs
# NumNFinstances = constrained_sum_sample_pos(N,M)

# -------------------------------Requests------------------------------------------------

# Fixed with number of NF instance and change the length of SFCs

SAMPLE = {'VNF0': VNF1, 'VNF1': VNF2, 'VNF2': VNF3, 'VNF3': VNF4, 'VNF4':VNF5, 'VNF5': VNF6}

NSins_list = [1, 2, 3, 4, 5, 6]
sys_nf_list = range(0, sys_Nmax)
nf_set = dict()
for i in range(0, sys_Nmax):
    nf_set[i] = randint(1, vm_capacity)
lenSFC = randint(1, req_Nmax)
# Build the NS request
req_nf_list = random_choice.choice(sys_nf_list, lenSFC, replace=False)
req_sfc = dict()
for i in req_nf_list:
    nf_instances = randint(1, req_Nmax_ins)
    req_sfc.update({i: nf_instances})

# Transform the request to the TOSCA template

tosca_req_list = list()
for nf, nf_instance in req_sfc.items():
    index = 'VNF' + str(nf)
    VNF = SAMPLE[index]
    sample = VNF[nf_instance-1]
    vnf_name = "VNF" + str(nf+1)
    sample_dict = dict()
    sample_dict['name'] = vnf_name
    sample_dict['vnfd_template'] = sample
    tosca_req_list.append(sample_dict)

req_path = base_path + '/' + 'requests.txt'
with open(req_path, 'a') as f:
        f.write("%s\n" % tosca_req_list)

coop_import_requirements(sample='coop-mesd.yaml', req_list=tosca_req_list)
sepa_import_requirements(sample='sepa-nsd.yaml', req_list=tosca_req_list)



