import yaml

from random import randint
import random
from numpy import random as random_choice
import time
from collections import OrderedDict
import uuid

import apmec_sap
import apmec_jvp
import apmec_baseline
import apmec_greedy

import pickle

# Randomize the properties of VNF between m1.tiny, m1.small, m1.medium, m1.large among 10 VNFs


sys_Nmax = 10  # Number of NFs -- > Maximum of NFs
vm_max_capacity = 10  # valiadate how many instances for m1.large
# req_Nmax = 3
req_Nmax_ins = 1

# Set the number of NF instances for NFs
# NumNFinstances = constrained_sum_sample_pos(N,M)

# -------------------------------Requests------------------------------------------------

# Fixed with number of NF instance and change the length of SFCs

SAMPLE = {'VNF0': 'vnfd11', 'VNF1': 'vnfd21', 'VNF2': 'vnfd31', 'VNF3': 'vnfd41', 'VNF4': 'vnfd51', 'VNF5': 'vnfd61',
          'VNF6': 'vnfd71', 'VNF7': 'vnfd81', 'VNF8': 'vnfd91', 'VNF9': 'vnfd101'}

VM_CAP = OrderedDict()

for index, vnf_name in enumerate(SAMPLE.keys()):
    VM_CAP[vnf_name] = random.randint(1, vm_max_capacity)

# NSins_list = [1, 2, 3, 4, 5, 6]
sys_nf_list = range(0, sys_Nmax)


# nf_set = dict()
# for i in range(0, sys_Nmax):
#    nf_set[i] = randint(1, vm_capacity)


def request_generator(nslen_max):
    lenSFC = randint(1, nslen_max)
    # Build the NS request
    req_nf_list = random_choice.choice(sys_nf_list, lenSFC, replace=False)
    # Transform the request to the TOSCA template
    req_list = list()
    for nf in req_nf_list:
        index = 'VNF' + str(nf)
        req_list.append(index)
    return req_list


NODE_CAP = 10
comp_node_list = ['edge1', 'edge2', 'edge3', 'edge4', 'edge5', 'edge6', 'edge7', 'edge8', 'edge9', 'edge10']


# Run algorithm here to store network function and instances


def initiate_graph():
    graph = OrderedDict()
    for node in comp_node_list:
        graph[node] = OrderedDict()
        graph[node]['cap'] = NODE_CAP
        graph[node]['load'] = 0
        graph[node]['instances'] = OrderedDict()
        graph[node]['allowed_vnf_list'] = list()
        for nfi in sys_nf_list:
            nf_name = "VNF" + str(nfi)
            graph[node]['allowed_vnf_list'].append(nf_name) if random.choice([True, False]) else None

    return graph


# KPI here:
#  1. Number of accepted requests
#  2. Number of used VMs for NFV network services
#  3. Chain configuration cost


def reform_tosca_list(solution):
    tosca_list = list()
    for vnfi, vnf_name in enumerate(solution.keys()):
        inst = solution[vnf_name]
        if inst is None:
            continue
        orig_index = int(vnf_name[3:])
        orig_vnf_name = 'VNF' + str(orig_index + 1)
        sample = SAMPLE[vnf_name]
        sample_dict = dict()
        sample_dict['name'] = orig_vnf_name
        sample_dict['vnfd_template'] = sample
        tosca_list.append(sample_dict)
        # edit the vnfd-file also for the availability node
    return tosca_list


sap_req_results = OrderedDict()
sap_total_cost_results = OrderedDict()
sap_comp_cost_results = OrderedDict()
sap_config_cost_results = OrderedDict()

jvp_req_results = OrderedDict()
jvp_total_cost_results = OrderedDict()
jvp_comp_cost_results = OrderedDict()
jvp_config_cost_results = OrderedDict()


greedy_req_results = OrderedDict()
greedy_total_cost_results = OrderedDict()
greedy_comp_cost_results = OrderedDict()
greedy_config_cost_results = OrderedDict()

base_req_results = OrderedDict()
base_total_cost_results = OrderedDict()
base_comp_cost_results = OrderedDict()
base_config_cost_results = OrderedDict()

ns_len_list = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
maxRetry = 10
retry = 0
while retry < maxRetry:
    sap_graph = initiate_graph()
    for nslen_max in ns_len_list:
        # NOTE: use script to remove database if some entries are error
        sap_vm_count = 0
        sap_req_count = 0
        sap_system_dict = OrderedDict()
        sap_req_entry = 0
        sap_total_cost_entry = list()
        sap_comp_cost_entry = list()
        sap_config_cost_entry = list()
        # jvp_graph = initiate_graph()
        # jvp_vm_count = 0
        # jvp_req_count = 0
        # jvp_system_dict = OrderedDict()
        #
        # greedy_graph = initiate_graph()
        # greedy_vm_count = 0
        # greedy_req_count = 0
        # greedy_system_dict = OrderedDict()
        #
        # base_graph = initiate_graph()
        # base_vm_count = 0
        # base_req_count = 0
        # base_system_dict = OrderedDict()

        cont = True
        while cont:
            req_list = request_generator(nslen_max)
            # print "=================================="
            # print "Request:", req_list

            sap_total_cost, sap_comp_cost, sap_config_cost, sap_solution = apmec_sap.sap(req_list, sap_graph, sap_system_dict,
                                                                                     VM_CAP)
            if sap_total_cost is None:
                print 'SAP Request is rejected!'
                break

            # print "Solution:", sap_solution
            # print "SAP config cost:", sap_config_cost
            sap_req_entry += 1
            sap_total_cost_entry.append(sap_total_cost)
            sap_comp_cost_entry.append(sap_comp_cost)
            sap_config_cost_entry.append(sap_config_cost)

            # # ========================================================================================
            # jvp_total_cost, jvp_comp_cost, jvp_config_cost, jvp_solution = apmec_jvp.jvp(req_list, jvp_graph,
            #                                                                          jvp_system_dict,
            #                                                                          VM_CAP)
            # if jvp_total_cost is None:
            #     print 'JVP Request is rejected!'
            #     break
            # # new_vnf_list, reused_vnf_list = jvp.execute()
            # print "Solution:", jvp_solution
            # print "JVP total cost:", jvp_total_cost
            # print "JVP comp cost:", jvp_comp_cost
            # print "JVP config cost:", jvp_config_cost
            # jvp_req_count += 1
            #
            # # ========================================================================================
            # base_total_cost, base_comp_cost, base_config_cost, base_solution = apmec_baseline.baseline(req_list, base_graph,
            #                                                                                       base_system_dict,
            #                                                                                       VM_CAP)
            # if base_total_cost is None:
            #     print 'Baseline Request is rejected!'
            #     break
            # print "Solution:", base_solution
            # print "Baseeline total cost:", base_total_cost
            # print "Baseline comp cost:", base_comp_cost
            # print "Baseline config cost:", base_config_cost
            # base_req_count += 1
            #
            # # ========================================================================================
            # greedy_total_cost, greedy_comp_cost, greedy_config_cost, greedy_solution = apmec_greedy.greedy(req_list, greedy_graph,
            #                                                                                         greedy_system_dict,
            #                                                                                         VM_CAP)
            # if greedy_total_cost is None:
            #     print 'Greedy Request is rejected!'
            #     break
            # print "Solution:", greedy_solution
            # print "Greedy total cost:", greedy_total_cost
            # print "Greedy comp cost:", greedy_comp_cost
            # print "Greedy config cost:", greedy_config_cost

        if not sap_req_entry:
            # retry = retry - 1 if retry else 0
            continue
        if sap_total_cost_results.get(nslen_max) is None:
            sap_total_cost_results[nslen_max] = list()
        sap_total_cost_results[nslen_max].append(sum(sap_total_cost_entry)/float(len(sap_total_cost_entry)))

        if sap_comp_cost_results.get(nslen_max) is None:
            sap_comp_cost_results[nslen_max] = list()
        sap_comp_cost_results[nslen_max].append(sum(sap_comp_cost_entry)/float(len(sap_comp_cost_entry)))

        if sap_config_cost_results.get(nslen_max) is None:
            sap_config_cost_results[nslen_max] = list()
        sap_config_cost_results[nslen_max].append(sum(sap_config_cost_entry)/float(len(sap_config_cost_entry)))

        if sap_req_results.get(nslen_max) is None:
            sap_req_results[nslen_max] = list()
        sap_req_results[nslen_max].append(sap_req_entry)

    retry += 1

print sap_req_results
print sap_total_cost_results
print sap_comp_cost_results
print sap_config_cost_results

pickle.dump(sap_total_cost_results, open("sap_total_cost_results.pickle", "wb"))
pickle.dump(sap_comp_cost_results, open("sap_comp_cost_results.pickle", "wb"))
pickle.dump(sap_config_cost_results, open("sap_config_cost_results.pickle", "wb"))
pickle.dump(sap_req_results, open("sap_req_results.pickle", "wb"))




































