# Add tabu search algorithm (local search). This engine will be used for reach and jvp
# Candidate in tabu list is chosen if it does not repeat in the chain
# Tabu KPI for selection is the Paid factor
from collections import OrderedDict
import networkx as nx
from numpy import random
import uuid
import copy
import time

# Set weight for problem optimization
ALPHA = 0.6  # weight for computation cost
BETA = 0.4  # weight for config cost
TABU_ITER_MAX = 30   # Tabu size: stop after algorithm reaches this size
LOOP_ITER_MAX = 10   # Number of iterations is executed for each tabu search
MAX = 10**6


class Tabu(object):
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

    def execute_tabu(self):
        # This method returns initial ns_dict and initial cost
        init_candidate, init_cost = self.find_first_solution(strategy="random")
        if init_candidate is None:
            print "Algorithm failed at first step."
            return None, None, None
        curr_solution = copy.deepcopy(init_candidate)
        final_best_cost = init_cost['total_cost']
        # print final_best_cost
        final_best_candidate = copy.deepcopy(init_candidate)
        final_best_result_dict = copy.deepcopy(init_cost)
        loop_index = 0
        while loop_index < LOOP_ITER_MAX:
            # print 'start tracking'
            match_dict, bst_candidate, solution_info_dict = self.find_best_neighborhood(curr_solution, policy='random')
            # print 'end tracking'
            if bst_candidate is None:
                loop_index = loop_index + 1
                continue
            bst_cost = solution_info_dict['total_cost']
            curr_solution = copy.deepcopy(bst_candidate)
            # A solution belong to the current visiting VNF back to its original physical node
            if self.in_tabu_list(match_dict):   # Tabu list is a list of vnf_index:node mapping
                # override if meet aspiration condition
                if bst_cost < final_best_cost:
                    # this makes sure there is only one mapping vnf_index:node_index in tabu list
                    self.tabu_list_remove(match_dict)
            else:
                if (len(self.tabu_list) + 1) < TABU_ITER_MAX:
                    self.tabu_list.append(match_dict)  # {nf:node} is a move
                else:
                    break        # stop if tabu list size exceeds TABU_ITER_MAX
            loop_index = loop_index + 1
            # print loop_index
            # print loop_index
            if bst_cost < final_best_cost:
                final_best_cost = bst_cost
                final_best_candidate = copy.deepcopy(bst_candidate)
                final_best_result_dict = copy.deepcopy(solution_info_dict)
                loop_index = 0
                # if policy is paid
                print "Tabu worked here"

        if final_best_cost >= MAX:
            print "Tabu: Unable to find better solution due the the constraint"
            print "Chain:", self.sfc_dict
            return None, None, None

        final_best_result_dict['config_cost'] = self.chain_config_cost(final_best_candidate, self.sys_ns_dict)
        final_best_result_dict['total_cost'] = final_best_result_dict['total_cost'] + BETA*final_best_result_dict['config_cost']
        # should return best candidate
        return final_best_candidate, final_best_result_dict, curr_solution

    # Find first solution: apply local search for this case (one-by-one)
    def find_first_solution(self, strategy):
        # total_cost is calculated from the problem formulation
        solution_info_dict = OrderedDict()
        solution_info_dict['total_cost'] = 0
        solution_info_dict['comp_cost'] = 0
        curr_solution = OrderedDict()
        est_graph = copy.deepcopy(self.graph)
        if strategy == "random":
            for nf_index in self.sfc_dict:
                # vnf_load = self.vm_cap[nf_index]
                node_candidate = list()
                for node in est_graph:
                    node_candidate.append(node)

                # Run comp cost function
                comp_cost_dict, node_match = self.comp_cost_func(nf_index, node_candidate[:], est_graph)
                local_node_candidate = OrderedDict()
                for node in node_candidate:
                    if comp_cost_dict.get(node) is None:
                        comp_cost_dict[node] = MAX
                        continue
                    local_node_candidate[node] = ALPHA * comp_cost_dict[node]
                if not local_node_candidate:
                    print 'tabu: What is the fault reason'
                    print 'At VNF-th', nf_index
                    print 'Current solution', curr_solution
                    print 'Tabu: comp cost', comp_cost_dict
                    return None, None
                else:
                    final_candidate = random.choice(local_node_candidate.keys())
                    exp_total_cost = local_node_candidate[final_candidate]
                    curr_solution[nf_index] = {final_candidate: node_match[final_candidate]}
                    solution_info_dict['total_cost'] = solution_info_dict['total_cost'] + exp_total_cost
                    solution_info_dict['comp_cost'] = solution_info_dict['comp_cost'] + comp_cost_dict[final_candidate]
                    self.update_graph({nf_index: {final_candidate: copy.deepcopy(node_match[final_candidate])}},
                                      [nf_index], est_graph)

        return curr_solution, solution_info_dict

    # This is used to calculate chain configuration cost
    # If reused instance exists, simply choose the least idle one
    def chain_config_cost(self, curr_solution, sample_dict):
        consec_counts = 0
        forbiden_list = list()
        # ns_candidate = OrderedDict()
        for node_index, nf_index in enumerate(self.sfc_dict):
            for ns_id, ns_info_dict in sample_dict.items():
                if nf_index in forbiden_list:  # to avoid accidentally increasing consec_counts
                    break
                mapping_dict = ns_info_dict['mapping']
                # share_list = list()
                for mp_index, mp_nf in enumerate(mapping_dict.keys()):
                    mp_node_dict = mapping_dict[mp_nf]
                    if nf_index == mp_nf and curr_solution[nf_index] == mp_node_dict:
                        if node_index < len(curr_solution) - 1:
                            dst_vnf_index = self.sfc_dict[node_index + 1]
                            dst_node_dict = curr_solution[dst_vnf_index]
                            if mp_index < len(mapping_dict) - 1:
                                nxt_mp_nf = mapping_dict.keys()[mp_index + 1]
                                nxt_node_dict = mapping_dict[nxt_mp_nf]
                                if {dst_vnf_index: dst_node_dict} == {nxt_mp_nf: nxt_node_dict}:
                                    print 'Tabu: COUPLE map detected!!!'
                                    consec_counts = consec_counts + 1
                                    forbiden_list.append(nf_index)
                                    break
        config_cost = (self.NSlen - 1) - consec_counts
        return config_cost

    def cal_total_cost(self, visited_solution):
        solution_info_dict = OrderedDict()
        solution_info_dict['total_cost'] = 0
        solution_info_dict['comp_cost'] = 0
        curr_solution = OrderedDict()
        bst_graph = copy.deepcopy(self.graph)
        for index, vnf_index in enumerate(visited_solution.keys()):
            node_candidate_dict = visited_solution[vnf_index]
            node_candidate = node_candidate_dict.keys()
            pnode = node_candidate[0]
            node_candidate = [pnode]
            comp_cost_dict, node_match = self.comp_cost_func(vnf_index, node_candidate, bst_graph)
            if comp_cost_dict.get(pnode) is None:
                return None          # also means that loop will be automatically broken
            curr_solution[vnf_index] = {pnode: node_match[pnode]}
            curr_cost = ALPHA*comp_cost_dict[pnode]
            solution_info_dict['total_cost'] = solution_info_dict['total_cost'] + curr_cost
            solution_info_dict['comp_cost'] = solution_info_dict['comp_cost'] + comp_cost_dict[pnode]
            self.update_graph({vnf_index: copy.deepcopy(node_candidate_dict)}, [vnf_index], bst_graph)
        return solution_info_dict

    def find_best_neighborhood(self, curr_solution, policy):
        picked_vnf = None
        picked_index = None
        # apply random VNF first
        if policy == 'random':
            picked_vnf = random.choice(self.sfc_dict)

        # from nf_index in nf_dict, find index in chain
        picked_index = self.sfc_dict.index(picked_vnf) if picked_vnf is not None else picked_index
        visited_node_dict = curr_solution[self.sfc_dict[picked_index]]
        visited_node = visited_node_dict.keys()[0]
        node_candidate = list()
        for node in self.graph:
            if node != visited_node:
                node_candidate.append(node)

        trial_node = random.choice(node_candidate)
        trial_solution = self.find_temp_solution(curr_solution, picked_vnf, trial_node)
        if trial_solution is None:
            return None, None, None
        else:
            final_solution = copy.deepcopy(trial_solution)
            final_solution_info_dict = self.cal_total_cost(final_solution)
            if final_solution_info_dict is None:
                return None, None, None

        return {picked_vnf: visited_node_dict}, final_solution, final_solution_info_dict

    def find_temp_solution(self, orig_solution, orig_vnf, visited_node):
        req_load = 1
        vnf_load = 1
        visited_solution = copy.deepcopy(orig_solution)
        prev_node_dict = visited_solution[orig_vnf]
        curr_node_load = self.graph[visited_node]['load']
        total_node_cap = self.graph[visited_node]['cap']
        if self.graph[visited_node]['instances'].get(orig_vnf) is None:
            if {visited_node: None} != prev_node_dict:
                if (vnf_load + curr_node_load) > total_node_cap:
                    return None
                else:
                    # print 'choose an empty node'
                    visited_solution[orig_vnf] = {visited_node: None}
        else:
            local_inst_dict = OrderedDict()
            for inst_id, inst_list in self.graph[visited_node]['instances'][orig_vnf].items():
                if {visited_node: inst_id} != prev_node_dict:
                    total_load = len(inst_list)
                    if req_load + total_load <= self.vm_cap[orig_vnf]:
                        local_inst_dict[inst_id] = total_load
            if not local_inst_dict:
                if (vnf_load + curr_node_load) > total_node_cap:
                    return None
                else:
                    if {visited_node: None} != prev_node_dict:
                        visited_solution[orig_vnf] = {visited_node: None}
                    else:
                        return None
            else:
                target_inst_id = max(local_inst_dict, key=local_inst_dict.get)
                visited_solution[orig_vnf] = {visited_node: target_inst_id}

        return visited_solution

    def ordered_path_list(self, paid_list):
        paid_dict = OrderedDict()
        for paid_index, paid in enumerate(paid_list):
            paid_dict[paid_index] = paid
        order_path_tup = sorted(paid_dict.items(), key=lambda kv: kv[1])
        return order_path_tup

    def in_tabu_list(self, match_dict):
        check = False
        for tabu_dict in self.tabu_list:
            if tabu_dict == match_dict:
                check = True
                break
        return check

    def tabu_list_remove(self, match_dict):
        temp_tabu_list = self.tabu_list
        for tabu_index, tabu_dict in enumerate(temp_tabu_list):
            if tabu_dict == match_dict:
                self.tabu_list.pop(tabu_index)

    # Calculate the computation cost
    def comp_cost_func(self, nf_index, node_candidate, graph):
        req_load = 1
        vnf_load = 1
        curr_comp_cost = OrderedDict()
        node_match = OrderedDict()
        for node in node_candidate:
            curr_node_load = graph[node]['load']
            total_node_cap = graph[node]['cap']
            exp_node_load = curr_node_load + vnf_load
            cni = vnf_load/float(exp_node_load)
            inst_existed = False
            if graph[node]['instances'].get(nf_index):
                inst_dict = OrderedDict()
                nf_inst_dict = graph[node]['instances'][nf_index]
                for inst_index, inst_info_list in nf_inst_dict.items():
                    total_load = len(inst_info_list)
                    if req_load + total_load <= self.vm_cap[nf_index]:
                        inst_existed = True
                        inst_dict[inst_index] = total_load
                if inst_dict:
                    target_inst_id = max(inst_dict, key=inst_dict.get)
                    curr_comp_cost[node] = cni * (req_load/(req_load + inst_dict[target_inst_id]))
                    node_match[node] = target_inst_id
                else:
                    node_match[node] = None
            if not inst_existed:
                # Limit the number of node by overal node capacity
                if (vnf_load + curr_node_load) > total_node_cap:
                    node_match[node] = None
                    continue
                node_match[node] = None
                curr_comp_cost[node] = 1 * cni   # This is node-level index

        return curr_comp_cost, node_match

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
        # For Tabu, VNF instance is unknown. It does not care about it
        if graph is None:
            graph = self.graph
        if vnf_list is None:
            vnf_list = self.sfc_dict
        # Update physical node
        check_list = list()
        for vnf_index, node_dict in ns_candidate.items():
            if not node_dict:
                print 'Tabu: Node dict error. Revise update graph'
                return
            node = node_dict.keys()[0]
            inst_info = OrderedDict()
            inst_info['ns_id'] = self.req_id
            req_load = 1
            new_inst_detection = False
            if graph[node]['instances'].get(vnf_index) is None:
                new_inst_detection = True
                graph[node]['instances'][vnf_index] = OrderedDict()
            else:
                inst_dict = OrderedDict()
                nf_inst_dict = graph[node]['instances'][vnf_index]
                for inst_index, inst_info_list in nf_inst_dict.items():
                    total_load = len(inst_info_list)
                    if req_load + total_load <= self.vm_cap[vnf_index]:
                        inst_dict[inst_index] = total_load
                if inst_dict:
                    # print 'successfully loaded'
                    target_inst_id = max(inst_dict, key=inst_dict.get)
                    nf_inst_dict[target_inst_id].append(inst_info)
                    check_list.append({vnf_index: {node: target_inst_id}})
                else:
                    if vnf_list == self.sfc_dict and len(vnf_list) != 1:
                        print 'Tabu: new instance!!!'
                        print 'NF index', vnf_index
                    new_inst_detection = True

            if new_inst_detection:
                if graph[node]['load'] + 1 > graph[node]['cap']:
                    print 'Tabu: Load in physical node is over. Revise update_graph'
                    return
                graph[node]['load'] += 1
                inst_id = uuid.uuid4()
                node_dict[node] = inst_id
                graph[node]['instances'][vnf_index][inst_id] = list()
                graph[node]['instances'][vnf_index][inst_id].append(inst_info)
                check_list.append({vnf_index: {node: inst_id}})

    def get_graph(self):
        return self.graph

    def reform_ns_candidate(self, ns_candidate):
        # ns_candidate is a list of node: VNF index:(node - instance index)
        mapping_dict = OrderedDict()
        for vnf_index, node_dict in ns_candidate.items():
            mapping_dict[vnf_index] = node_dict
        return mapping_dict

    def getReqID(self):
        return self.req_id
