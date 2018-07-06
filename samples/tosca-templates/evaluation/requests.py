import yaml

import os


def import_requirements(sample, req_dict):
    base_path = os.path.dirname(os.path.abspath(__file__))
    path = base_path + '/' + sample
    with open(path, 'r') as f:
      sample_dict = yaml.safe_load(f.read())

    sample_dict['imports']['nsds']['nsd_templates']['requirements'] = req_dict

    with open(path, 'w') as f:
        yaml.safe_dump(sample_dict, f)


req_dict = {'VNF1':2}
import_requirements(sample='test_simple_mesd.yaml', req_dict=req_dict)

VNF1 = {
    'sample-tosca-vnfd1-1ins.yaml',
    'sample-tosca-vnfd1-2ins.yaml',
    'sample-tosca-vnfd1-3ins.yaml',
}

VNF2 = {
    'sample-tosca-vnfd2-1ins.yaml',
    'sample-tosca-vnfd2-2ins.yaml',
    'sample-tosca-vnfd2-3ins.yaml',
}

VNF3 = {
    'sample-tosca-vnfd3-1ins.yaml',
    'sample-tosca-vnfd3-2ins.yaml',
    'sample-tosca-vnfd3-3ins.yaml',
}

VNF4 = {
    'sample-tosca-vnfd4-1ins.yaml',
    'sample-tosca-vnfd4-2ins.yaml',
    'sample-tosca-vnfd4-3ins.yaml',
}

VNF5 = {
    'sample-tosca-vnfd5-1ins.yaml',
    'sample-tosca-vnfd5-2ins.yaml',
    'sample-tosca-vnfd5-3ins.yaml',
}

VNF6 = {
    'sample-tosca-vnfd6-1ins.yaml',
    'sample-tosca-vnfd6-2ins.yaml',
    'sample-tosca-vnfd6-3ins.yaml',
}

import matplotlib.pyplot as plt
from random import randint
import random
from numpy import random as random_choice
from algorithm import meso_algorithm

from confidence import mean_confidence_interval


def constrained_sum_sample_pos(n, total):
    dividers = sorted(random.sample(xrange(1, total), n - 1))
    return [a - b for a, b in zip(dividers + [total], [0] + dividers)]


# SYSTEM CAPACITY

P = 100
C = 1  # Maximum capacity which is the maximum of chain which a NF could serve --> it is the reuse factor of NFs
# Input
# Offerred environment
N = 6  # Number of NFs -- > Maximum of NFs

# Set the number of NF instances for NFs
# NumNFinstances = constrained_sum_sample_pos(N,M)

# -------------------------------Requests------------------------------------------------

# Fixed with number of NF instance and change the length of SFCs
min_resue = 0.5  # Set the reuse factor of the NS
max_lenSFC = 3
NSins_list = [1, 2, 3, 4, 5, 6]
req_nf_list = range(0, N)
maxRetry = 1000
total_apmec_list = list()
total_normal_list = list()
total_avg_mec_list = list()
total_avg_normal_list = list()

nf_set = dict()
for i in range(0, N):
    nf_set[i] = randint(1, vm_capacity)
lenSFC = randint(1, max_lenSFC)
                # Build the SFC request
                nf_list = random_choice.choice(req_nf_list, lenSFC, replace=False)
                for i in nf_list:
                    nf_instances = randint(1, l)
                    req_sfc.update({i: nf_instances})
                request_vms = 0
                for nf_index, nf_ins in req_sfc.items():
                    request_vms = request_vms + nf_ins
                tmp_vms = normal_vms + request_vms
                if tmp_vms <= P:
                    normal_vms = tmp_vms
                    numOfRequests_normal = numOfRequests_normal + 1

                # print req_sfc
                nf_instances, is_matched = meso_algorithm(nf_set, system_sfc_dict, req_sfc, min_resue)
                #print {is_matched: {nf_instances: lenSFC}}
                tmp_avg_vms = avg_vms + nf_instances
                if tmp_avg_vms <= P:
                    numOfRequests_apmec = numOfRequests_apmec + 1
                    avg_vms = avg_vms + nf_instances
                # index = index + 1
                res = res + nf_instances

            # numOfRequest_list_apmec.append(numOfRequests_apmec)
            # numOfRequest_list_normal.append(numOfRequests_normal)
            if avgRequest_apmec_dict.get(l) is None:
                avgRequest_apmec_dict[l] = 0
            if avgRequest_normal_dict.get(l) is None:
                avgRequest_normal_dict[l] = 0
            if apmec_dict.get(l) is None:
                apmec_dict[l] = list()
            if normal_dict.get(l) is None:
                normal_dict[l] = list()
            avgRequest_apmec_dict[l] = avgRequest_apmec_dict[l] + numOfRequests_apmec
            avgRequest_normal_dict[l] = avgRequest_normal_dict[l] + numOfRequests_normal
            apmec_dict[l].append(numOfRequests_apmec)
            normal_dict[l].append(numOfRequests_normal)

    numOfRequest_list_apmec = [NumReq/float(maxRetry) for i, NumReq in avgRequest_apmec_dict.items()]
    numOfRequest_list_normal = [NumReq/float(maxRetry) for i, NumReq in avgRequest_normal_dict.items()]
    # print numOfRequest_list_apmec
    # print numOfRequest_list_normal
    avg_mec_list = list()
    lower_bound_mec_list = list()
    upper_bound_mec_list = list()

    avg_normal_list = list()
    lower_bound_normal_list = list()
    upper_bound_normal_list = list()

    for apmec_test_bench, apmec_numReq in apmec_dict.items():
          m,n,p = mean_confidence_interval(apmec_numReq, confidence=0.95)
          avg_mec_list.append(m)
          lower_bound_mec_list.append(n)
          upper_bound_mec_list.append(p)

    for normal_test_bench, normal_numReq in normal_dict.items():
          m, n, p = mean_confidence_interval(normal_numReq, confidence=0.95)
          avg_normal_list.append(m)
          lower_bound_normal_list.append(n)
          upper_bound_normal_list.append(p)


        # print avg_mec_list
        # print lower_bound_mec_list
        # print upper_bound_mec_list

        # print avg_normal_list
        # print lower_bound_normal_list
        # print upper_bound_normal_list
    bp_data_mec = [apmec_req_list for apmec_bench, apmec_req_list in apmec_dict.items()]
    bp_normal_mec = [normal_req_list for normal_bench, normal_req_list in normal_dict.items()]
    total_apmec_list.append(bp_data_mec)
    total_normal_list.append(bp_normal_mec)

    total_avg_mec_list.append(avg_mec_list)
    total_avg_normal_list.append(avg_normal_list)
