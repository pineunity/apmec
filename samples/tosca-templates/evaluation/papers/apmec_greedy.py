# Greedy search expects to have lowest complexity
from collections import OrderedDict
import networkx as nx
import uuid
from greedy_lib import GreedyLib


def greedy(system_ns_dict, graph, nf_prop, req_dict, timer):
    greedy_solver = GreedyLib(nf_prop, req_dict, graph, system_ns_dict, timer)
    ns_candidate, result_dict = greedy_solver.execute_greedy()
    if not ns_candidate:
        print "Algorithm is finished!!!"
        return None, None, None, None, None, None
    ns_id = greedy_solver.getReqID()
    total_cost = result_dict['total_cost']
    comp_cost = result_dict['comp_cost']
    routing_cost = result_dict['routing_cost']
    rec_cost = result_dict['rec_cost']
    rel_cost = result_dict['rel_cost']
    config_cost = result_dict['config_cost']

    # Update graph
    greedy_solver.update_graph(ns_candidate)

    system_ns_dict[ns_id] = OrderedDict()
    system_ns_dict[ns_id]['mapping'] = greedy_solver.reform_ns_candidate(ns_candidate)
    system_ns_dict[ns_id]['detailed_path'] = result_dict['detailed_path']
    system_ns_dict[ns_id]['rel'] = result_dict['rel_cost']
    # print 'mea node', req_dict['mea_node']
    print 'Greedy final_candidate', ns_candidate.values()
    # print 'final path', greedy_solver.get_path()

    return total_cost, routing_cost, comp_cost, rec_cost, rel_cost, config_cost
