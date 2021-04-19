# Greedy search expects to have lowest complexity
from collections import OrderedDict
import networkx as nx
import uuid
from baseline_lib import BaselineLib


def baseline(system_ns_dict, graph, nf_prop, req_dict, timer):
    baseline_solver = BaselineLib(nf_prop, req_dict, graph, system_ns_dict, timer)
    ns_candidate, result_dict = baseline_solver.execute_greedy()
    if not ns_candidate:
        print "Baseline algorithm is finished!!!"
        return None, None, None, None, None, None
    ns_id = baseline_solver.getReqID()
    total_cost = result_dict['total_cost']
    comp_cost = result_dict['comp_cost']
    routing_cost = result_dict['routing_cost']
    rel_cost = result_dict['rel_cost']
    rec_cost = result_dict['rec_cost']
    config_cost = result_dict['config_cost']

    system_ns_dict[ns_id] = OrderedDict()
    system_ns_dict[ns_id]['mapping'] = baseline_solver.reform_ns_candidate(ns_candidate)
    system_ns_dict[ns_id]['detailed_path'] = result_dict['detailed_path']    # print 'sfc_detail', req_dict['sfc']
    system_ns_dict[ns_id]['rel'] = result_dict['rel_cost']
    # print 'mea node', req_dict['mea_node']
    print 'Baseline final_candidate', ns_candidate.values()
    # print 'final path', greedy_solver.get_path()
    # Update graph
    baseline_solver.update_graph(ns_candidate.values())

    return total_cost, routing_cost, comp_cost, rec_cost, rel_cost, config_cost
