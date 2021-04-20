# Greedy search expects to have lowest complexity
from collections import OrderedDict
import networkx as nx
import uuid
from baseline_lib import BaselineLib


def baseline(req_list, graph, system_ns_dict, vm_cap):
    baseline_solver = BaselineLib(req_list, graph, system_ns_dict, vm_cap)
    ns_candidate, result_dict, solution = baseline_solver.execute_greedy()
    if not ns_candidate:
        print "Baseline algorithm is finished!!!"
        return None, None, None, None
    ns_id = baseline_solver.getReqID()
    total_cost = result_dict['total_cost']
    comp_cost = result_dict['comp_cost']
    config_cost = result_dict['config_cost']

    system_ns_dict[ns_id] = OrderedDict()
    system_ns_dict[ns_id]['mapping'] = baseline_solver.reform_ns_candidate(ns_candidate)
    print 'Baseline final_candidate', ns_candidate.values()
    baseline_solver.update_graph(ns_candidate.values())

    return total_cost, comp_cost, config_cost, solution
