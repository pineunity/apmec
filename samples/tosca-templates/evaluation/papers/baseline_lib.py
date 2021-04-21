# Greedy search expects to have lowest complexity
from collections import OrderedDict
import networkx as nx
import uuid
import copy
import time

# Set weight for problem optimization
ALPHA = 0.6  # weight for computation cost
BETA = 0.4  # weight for config cost
TABU_ITER_MAX = 30   # Tabu size: stop after algorithm reaches this size
LOOP_ITER_MAX = 10   # Number of iterations is executed for each tabu search
MAX = 10**6


class BaselineLib(object):
    def __init__(self, req_list, graph, sys_nf_info, vm_cap):
        self.graph = graph
        self.sfc_dict = req_list
        self.tabu_list = list()
        self.req_id = uuid.uuid4()
        self.vm_cap = vm_cap
        self.sys_ns_dict = sys_nf_info
        self.NSlen = len(req_list)
        self.inst_mapping = OrderedDict()    # used for reuse, this is later used to update graph
        self.shared_path_dict = OrderedDict()

    # Find first solution: apply local search for this case (one-by-one)
    def execute_greedy(self):
        # total_cost is calculated from the problem formulation
        solution_info_dict = OrderedDict()
        solution_info_dict['total_cost'] = 0
        solution_info_dict['config_cost'] = 0
        solution_info_dict['comp_cost'] = 0
        curr_solution = OrderedDict()
        est_graph = copy.deepcopy(self.graph)
        for index, nf_index in enumerate(self.sfc_dict):
            src_dict = OrderedDict()
            if index:
                prev_vnf = self.sfc_dict[index - 1]
                src_dict[prev_vnf] = curr_solution[prev_vnf]
            node_candidate = list()
            for node in est_graph:
                if nf_index in est_graph[node]['allowed_vnf_list']:
                    node_candidate.append(node)

            # Run comp cost function
            comp_cost_dict = self.comp_cost_func(nf_index, node_candidate[:], est_graph)
            local_node_candidate = OrderedDict()
            for node in node_candidate:
                if comp_cost_dict.get(node) is None:
                    continue
                local_node_candidate[node] = \
                    ALPHA * comp_cost_dict[node]  

            if not local_node_candidate:
                print 'baseline: What is the fault reason'
                print 'At VNF-th', nf_index
                print 'Current solution', curr_solution
                print 'Node candidate', node_candidate
                print 'baseline: comp cost', comp_cost_dict
                return None, None, None
            else:
                min_total_cost = min([cost for node, cost in local_node_candidate.items()])
                candidate_list = [node for node, cost in local_node_candidate.items() if cost == min_total_cost]
                final_candidate = candidate_list[0]
                curr_solution[nf_index] = final_candidate
                solution_info_dict['total_cost'] = solution_info_dict['total_cost'] + min_total_cost
                solution_info_dict['comp_cost'] = solution_info_dict['comp_cost'] + comp_cost_dict[final_candidate]
                self.update_graph([final_candidate], [nf_index], est_graph)

        if curr_solution:
            solution_info_dict['config_cost'] = (len(self.sfc_dict) - 1)

        return curr_solution, solution_info_dict, curr_solution

    # Calculate the computation cost
    def comp_cost_func(self, nf_index, node_candidate, est_graph):
        vnf_load = 1
        curr_comp_cost = OrderedDict()
        for node in node_candidate:
                # Limit the number of node by overal node capacity
                curr_node_load = est_graph[node]['load']
                total_node_cap = est_graph[node]['cap']
                if (vnf_load + curr_node_load) > total_node_cap:
                    continue
                # curr_node_load = 0.01 if curr_node_load == 0 else curr_node_load
                exp_node_load = curr_node_load + vnf_load
                curr_comp_cost[node] = vnf_load / float(exp_node_load)  # This is node-level index
        return curr_comp_cost

    def find_coloc(self, candidate):
        conv_candidate = OrderedDict()
        for index, node in enumerate(candidate):
            if node not in conv_candidate:
                conv_candidate[node] = list()
                conv_candidate[node].append(index)
            else:
                conv_candidate[node].append(index)
        return conv_candidate

    def update_graph(self, ns_candidate, vnf_list=None, graph=None):
        if graph is None:
            yep = True
            graph = self.graph
        if vnf_list is None:
            vnf_list = self.sfc_dict
        # Update physical node
        for index, node in enumerate(ns_candidate):
            vnf_index = vnf_list[index]
            inst_info = OrderedDict()
            if graph[node]['instances'].get(vnf_index) is None:
                graph[node]['instances'][vnf_index] = OrderedDict()
            inst_info['ns_id'] = self.req_id
            if graph[node]['load'] + 1 > graph[node]['cap']:
                    print 'Baseline: Load in physical node is over. Revise update_graph'
                    return

            graph[node]['load'] += 1
            print "I am here", graph[node]['load']
            print graph[node]['cap']
            inst_id = uuid.uuid4()
            graph[node]['instances'][vnf_index][inst_id] = list()
            graph[node]['instances'][vnf_index][inst_id].append(inst_info)

    def get_graph(self):
        return self.graph

    def getReqID(self):
        return self.req_id

    def reform_ns_candidate(self, ns_candidate):
        # ns_candidate is a list of node
        mapping_dict = OrderedDict()
        for index, node in enumerate(ns_candidate):
            vnf_index = self.sfc_dict[index]
            mapping_dict[vnf_index] = node
        return mapping_dict

