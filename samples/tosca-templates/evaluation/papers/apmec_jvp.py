# Reference for VNF reuse
# Following KPIs need to be returned: Configuration cost, Usage, and Reliability per NS
from collections import OrderedDict
import uuid
from tabu import Tabu


# system_ns_dict save the info of mapping
def jvp_plus(system_ns_dict, graph, nf_prop, req_dict, timer):
    # graph will be changed automatically in Tabu
    tabu_solver = Tabu(nf_prop, req_dict, graph, system_ns_dict, timer)
    ns_candidate, result_dict = tabu_solver.execute_tabu()
    if not ns_candidate:
        print "Algorithm is finished!!!"
        return None, None, None, None, None, None
    ns_id = tabu_solver.getReqID()
    total_cost = result_dict['total_cost']
    comp_cost = result_dict['comp_cost']
    routing_cost = result_dict['routing_cost']
    rec_cost = result_dict['rec_cost']
    rel_cost = result_dict['rel_cost']
    config_cost = result_dict['config_cost']

    # print 'sfc_detail', req_dict['sfc']
    # print 'mea node', req_dict['mea_node']
    print 'Tabu final_candidate', ns_candidate
    # print 'final path', tabu_solver.get_path()
    # Update graph
    tabu_solver.update_graph(ns_candidate)

    system_ns_dict[ns_id] = OrderedDict()
    system_ns_dict[ns_id]['mapping'] = tabu_solver.reform_ns_candidate(ns_candidate)
    system_ns_dict[ns_id]['detailed_path'] = result_dict['detailed_path']
    system_ns_dict[ns_id]['rel'] = result_dict['rel_cost']

    return total_cost, routing_cost, comp_cost, rec_cost, rel_cost, config_cost
