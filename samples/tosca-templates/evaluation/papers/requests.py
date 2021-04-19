import yaml

import os
from random import randint
import random
from numpy import random as random_choice
import time
from collections import OrderedDict
import sys
import openstack
import uuid

import apmec_sap
import apmec_jvp
import apmec_baseline

first_arg = sys.argv[1]

# it should return two template for the cooperation and separation approaches

def coop_import_requirements(sample, req_list):
    base_path = os.path.dirname(os.path.abspath(__file__))
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

# Randomize the properties of VNF between m1.tiny, m1.small, m1.medium, m1.large among 10 VNFs

sys_Nmax = 10  # Number of NFs -- > Maximum of NFs
vm_max_capacity = 10  # valiadate how many instances for m1.large
req_Nmax = 3
req_Nmax_ins = 1

# Set the number of NF instances for NFs
# NumNFinstances = constrained_sum_sample_pos(N,M)

# -------------------------------Requests------------------------------------------------

# Fixed with number of NF instance and change the length of SFCs

SAMPLE = {'VNF0': 'vnfd11', 'VNF1': 'vnfd21', 'VNF2': 'vnfd31', 'VNF3': 'vnfd41', 'VNF4':'vnfd51', 'VNF5': 'vnfd61', 'VNF6': 'vnfd71', 'VNF7': 'vnfd81', 'VNF8': 'vnfd91', 'VNF9': 'vnfd101'}

VM_CAP = OrderedDict()

for index, vnf_name in enumerate(SAMPLE.keys()):
    VM_CAP[vnf_name] = random.randint(1, vm_max_capacity)

# NSins_list = [1, 2, 3, 4, 5, 6]
sys_nf_list = range(0, sys_Nmax)

#nf_set = dict()
#for i in range(0, sys_Nmax):
#    nf_set[i] = randint(1, vm_capacity)

lenSFC = randint(1, req_Nmax)
# Build the NS request
req_nf_list = random_choice.choice(sys_nf_list, lenSFC, replace=False)
# Transform the request to the TOSCA template

tosca_req_list = list()
for nf in req_nf_list:
    index = 'VNF' + str(nf)
    sample = SAMPLE[index]
    #vnf_name = "VNF" + str(nf+1)
    sample_dict = dict()
    sample_dict['name'] = index
    sample_dict['vnfd_template'] = sample
    tosca_req_list.append(sample_dict)

# req dict: VNF1: vnfd11, ..., VNF10: vnfd101
# coop_import_requirements(sample='test_simple_mesd.yaml', req_list=tosca_req_list)
# sepa_import_requirements(sample='sepa-nsd.yaml', req_list=tosca_req_list)

def update_vnf_list():
    vnf_list = openstack.nfins_tracking()


VM_CAP = 10
comp_node_list = ['edge1', 'edge2', 'edge3', 'edge4', 'edge5', 'edge6', 'edge7', 'edge8', 'edge9', 'edge10']
# Run algorithm here to store network function and instances
def initiate_graph():
    graph = OrderedDict()
    for node in comp_node_list:
        graph[node] = OrderedDict()
        graph[node]['cap'] = VM_CAP
        graph[node]['instances'] = OrderedDict()
    return graph


if 'sap' in first_arg:
    graph = initiate_graph()
 
    cont = True
    vm_count = 0
    req_count = 0
    while cont:
        mes_id = uuid.uuid4()
        sys_vnf_dict = OrderedDict()   # store mes_id and ordered vnf list
        sap_system_dict = OrderedDict()
        # update vnf_list
        vnf_list = openstack.nfins_tracking()
    
        sap = apmec_sap.SAP(tosca_req_list, graph, sap_system_dict, VM_CAP)
        new_vnf_list, reused_vnf_list = sap.execute()
        coop_import_requirements(sample='test_simple_mesd.yaml', req_list=new_vnf_list)
        mes_name = 'mes-' + uuid.uuid4()
        openstack.mes_create(mes_name)
        # sleep here until mes is active
        # update graph only if mes is active
        # if mes is active, increase req_count and update vm_count
    
    









































