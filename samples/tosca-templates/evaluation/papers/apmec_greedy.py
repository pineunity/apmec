# Greedy search expects to have lowest complexity
from collections import OrderedDict
import networkx as nx
import uuid
from greedy_lib import GreedyLib


def greedy(req_list, graph, system_ns_dict, vm_cap):
    greedy_solver = GreedyLib(req_list, graph, system_ns_dict, vm_cap)
    ns_candidate, result_dict, solution = greedy_solver.execute_greedy()
    if not ns_candidate:
        print "Algorithm is finished!!!"
        return None, None, None, None
    ns_id = greedy_solver.getReqID()
    total_cost = result_dict['total_cost']
    comp_cost = result_dict['comp_cost']
    config_cost = result_dict['config_cost']

    # Update graph
    greedy_solver.update_graph(ns_candidate)

    system_ns_dict[ns_id] = OrderedDict()
    system_ns_dict[ns_id]['mapping'] = greedy_solver.reform_ns_candidate(ns_candidate)
    print 'Greedy final_candidate', ns_candidate.values()
    return total_cost, comp_cost, config_cost, solution
