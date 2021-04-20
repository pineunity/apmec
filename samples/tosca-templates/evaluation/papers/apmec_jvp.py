# Reference for VNF reuse
# Following KPIs need to be returned: Configuration cost, Usage, and Reliability per NS
from collections import OrderedDict
import uuid
from tabu import Tabu


# system_ns_dict save the info of mapping
def jvp(req_list, graph, system_ns_dict, vm_cap):
    # graph will be changed automatically in Tabu
    tabu_solver = Tabu(req_list, graph, system_ns_dict, vm_cap)
    ns_candidate, result_dict, solution = tabu_solver.execute_tabu()
    if not ns_candidate:
        print "Algorithm is finished!!!"
        return None, None, None, None
    ns_id = tabu_solver.getReqID()
    total_cost = result_dict['total_cost']
    comp_cost = result_dict['comp_cost']
    config_cost = result_dict['config_cost']
    print 'Tabu final_candidate', ns_candidate
    # Update graph
    tabu_solver.update_graph(ns_candidate)
    system_ns_dict[ns_id] = OrderedDict()
    system_ns_dict[ns_id]['mapping'] = tabu_solver.reform_ns_candidate(ns_candidate)

    return total_cost, comp_cost, config_cost, solution
