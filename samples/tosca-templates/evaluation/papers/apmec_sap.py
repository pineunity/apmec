# Sub-chain based availability-aware MEC service placement (scamp)
from collections import OrderedDict
import uuid
from advanced_tabu import AdvTabu


def scamp(system_ns_dict, graph, nf_prop, vm_cap):
    # graph will be changed automatically in Tabu
    tabu_solver = AdvTabu(nf_prop, graph, system_ns_dict, vm_cap)
    # ns_candidate is formed as {node:instance}
    ns_candidate, result_dict = tabu_solver.execute_tabu()
    if not ns_candidate:
        print "Algorithm is finished!!!"
        return None, None, None, None, None, None
    ns_id = tabu_solver.getReqID()
    total_cost = result_dict['total_cost']
    comp_cost = result_dict['comp_cost']
    config_cost = result_dict['config_cost']
    print 'Tabu++ candidate before update'
    print ns_candidate
    # print 'final path', tabu_solver.get_path()
    # Update graph
    tabu_solver.update_graph(ns_candidate)
    system_ns_dict[ns_id] = OrderedDict()
    system_ns_dict[ns_id]['mapping'] = tabu_solver.reform_ns_candidate(ns_candidate)
    print 'Tabu++ final_candidate'
    print ns_candidate
    return total_cost, comp_cost, config_cost
