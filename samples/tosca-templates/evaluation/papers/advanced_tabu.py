# Advanced Tabu includes 2 phases:
# Phase 1: find the largest sub-chain to reuse
# Phase 2: apply Tabu search
# Tabu KPI for selection is the Paid factor
from collections import OrderedDict
from numpy import random
import uuid
import copy
import time


def split_path(path):
    split_list = list()
    for idx, val in enumerate(path):
        if (idx + 1) < len(path):
            nxt_val = path[idx + 1]
            split_list.append((val, nxt_val))
    return split_list


# Set weight for problem optimization
ALPHA = 0.6  # weight for computation cost
BETA = 0.4  # weight for config cost
TABU_ITER_MAX = 30   # Tabu size: stop after algorithm reaches this size
LOOP_ITER_MAX = 10   # Number of iterations is executed for each tabu search
MAX = 10**6


class AdvTabu(object):
    def __init__(self, req_dict, graph, sys_nf_info, vm_cap):
        self.graph = graph
        # self.ns_dict = system_ns_dict
        self.req_dict = req_dict
        self.sfc_dict = req_dict.keys()
        self.tabu_list = list()
        self.req_id = uuid.uuid4()
        self.vm_cap = vm_cap
        self.sys_ns_dict = sys_nf_info
        self.NSlen = len(req_dict)
        self.inst_mapping = OrderedDict()    # used for reuse, this is later used to update graph
        self.shared_path_dict = OrderedDict()

    def execute_tabu(self):
        init_candidate, init_cost = self.find_first_solution(strategy='random')
        # print 'orig-cost:', init_cost
        if init_candidate is None:
            print "Algorithm failed at first step."
            return None, None
        # print 'first path', self.e2e_path
        # print 'first candidate', init_candidate
        curr_solution = copy.deepcopy(init_candidate)
        final_best_cost = init_cost['total_cost']
        # print final_best_cost
        final_best_candidate = copy.deepcopy(init_candidate)
        final_best_result_dict = copy.deepcopy(init_cost)
        # print 'First result'
        # print final_best_candidate
        # print final_best_cost
        loop_index = 0
        while loop_index < LOOP_ITER_MAX:
            # match_dict is a move
            match_dict, bst_candidate, solution_info_dict = self.find_best_neighborhood(curr_solution, policy='random')
            # match_tpl = (vnf_index, node_index, instance_index)
            # print 'end tracking'
            if bst_candidate is None:
                # print 'Tabu++: I am None!!!'
                # print 'Loop index:', loop_index
                # import time
                # time.sleep(5)
                loop_index = loop_index + 1
                continue
            bst_cost = solution_info_dict['total_cost']

            # A solution belong to the current visiting VNF back to its original physical node
            if self.in_tabu_list(match_dict):   # Tabu list is a list of vnf_index:node:instance
                # override if meet aspiration condition
                if bst_cost < final_best_cost:
                    # import time
                    # time.sleep(10)
                    self.tabu_list_remove(match_dict)
            else:
                if (len(self.tabu_list) + 1) < TABU_ITER_MAX:
                    self.tabu_list.append(match_dict)    # {nf:node} is a move
                else:
                    print 'Tabu++: Break due to over tabu list'
                    # import time
                    # time.sleep(5)
                    break        # stop if tabu list size exceeds TABU_ITER_MAX
            loop_index = loop_index + 1
            # print loop_index
            if bst_cost < final_best_cost:
                final_best_cost = bst_cost
                final_best_candidate = copy.deepcopy(bst_candidate)
                final_best_result_dict = copy.deepcopy(solution_info_dict)
                curr_solution = copy.deepcopy(bst_candidate)
                loop_index = 0
                # if policy is paid
                print "Tabu++ worked here!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        if final_best_cost >= MAX:
            print "Tabu++: unable to find better solution due the the constraint"
            return None, None
        print "=========="
        print 'Tabu++ list:', len(self.tabu_list)
        # should return best candidate
        return final_best_candidate, final_best_result_dict

    # Find first solution: apply local search for this case (one-by-one)
    def find_first_solution(self, strategy):
        # total_cost is calculated from the problem formulation
        solution_info_dict = OrderedDict()
        solution_info_dict['total_cost'] = 0
        solution_info_dict['config_cost'] = 0
        solution_info_dict['comp_cost'] = 0
        solution_info_dict['detailed_path'] = list()
        curr_solution = OrderedDict()
        est_graph = copy.deepcopy(self.graph)

        if strategy == 'random':
            for index, nf_index in enumerate(self.sfc_dict.keys()):
                src_dict = OrderedDict()
                if index:
                    prev_vnf = self.sfc_dict.keys()[index - 1]
                    src_dict[prev_vnf] = copy.deepcopy(curr_solution[prev_vnf])
                
                # Run comp cost function
                comp_cost_dict, config_cost_dict, match_dict = self.pre_comp_config_cost_func(nf_index, src_dict, est_graph)

                local_node_candidate = OrderedDict()
                for node in est_graph.keys():
                    if comp_cost_dict.get(node) is None:
                        comp_cost_dict[node] = MAX
                        local_node_candidate[node] = MAX
                        continue
                    local_node_candidate[node] = ALPHA * comp_cost_dict[node] + BETA * config_cost_dict[node]    # noqa
                if not local_node_candidate:
                    print 'Tabu++: What is the fault reason:', local_node_candidate
                    print 'At VNF-th', nf_index
                    print 'Current solution', curr_solution
                    print 'Tabu++: comp cost', comp_cost_dict
                    return None, None
                else:
                    final_candidate = random.choice(local_node_candidate.keys())
                    exp_total_cost = local_node_candidate[final_candidate]
                    curr_solution[nf_index] = {final_candidate: match_dict[final_candidate]}
                    print "Tabu++: config cost:", config_cost_dict[final_candidate]
                    solution_info_dict['total_cost'] += exp_total_cost
                    solution_info_dict['config_cost'] += config_cost_dict[final_candidate]
                    solution_info_dict['comp_cost'] += comp_cost_dict[final_candidate]

                    prev_node_dict = {final_candidate: match_dict[final_candidate]}
                    # print 'First update graph', prev_node_dict
                    self.update_graph({nf_index: {final_candidate: copy.deepcopy(match_dict[final_candidate])}}, est_graph)  # noqa

            # print "Tabu++: conf cost for the first algorithm:", solution_info_dict['config_cost']
        return curr_solution, solution_info_dict

    def post_cal_total_cost(self, new_solution):
        solution_info_dict = OrderedDict()
        solution_info_dict['total_cost'] = 0
        solution_info_dict['config_cost'] = 0
        solution_info_dict['comp_cost'] = 0
        solution_info_dict['detailed_path'] = list()
        curr_solution = OrderedDict()
        bst_graph = copy.deepcopy(self.graph)
        for index, vnf_index in enumerate(new_solution.keys()):
            src_dict = OrderedDict()
            if index:
                prev_vnf = self.sfc_dict.keys()[index - 1]
                src_dict[prev_vnf] = copy.deepcopy(curr_solution[prev_vnf])
            node_candidate_dict = new_solution[vnf_index]
            node_candidate = node_candidate_dict.keys()
            pnode = node_candidate[0]
            comp_cost_dict, config_cost_dict = self.post_comp_config_cost_func(vnf_index, src_dict, node_candidate_dict, bst_graph)
            if comp_cost_dict.get(pnode) is None:
                return None          # also means that loop will be automatically broken
            curr_solution[vnf_index] = node_candidate_dict
            curr_cost = ALPHA*comp_cost_dict[pnode] + BETA*config_cost_dict[pnode]     # noqa
            solution_info_dict['total_cost'] = solution_info_dict['total_cost'] + curr_cost
            solution_info_dict['config_cost'] = solution_info_dict['config_cost'] + config_cost_dict[pnode]
            solution_info_dict['comp_cost'] = solution_info_dict['comp_cost'] + comp_cost_dict[pnode]
            self.update_graph({vnf_index: copy.deepcopy(node_candidate_dict)}, bst_graph)
        return solution_info_dict

    def find_match(self, orig_solution, visited_vnf, visited_node):
        vnf_load = 1
        req_load = 1
        visited_solution = copy.deepcopy(orig_solution)
        prev_node_dict = visited_solution[visited_vnf]
        curr_node_load = self.graph.node[visited_node]['load']
        total_node_cap = self.graph.node[visited_node]['cap']
        if self.graph[visited_node]['instances'].get(visited_vnf) is None:
            if {visited_node: None} != prev_node_dict:
                if (vnf_load + curr_node_load) > total_node_cap:
                    return None
                else:
                    visited_solution[visited_vnf] = {visited_node: None}
            # return None
        else:
            local_inst_list = list()
            for inst_id, inst_list in self.graph[visited_node]['instances'][visited_vnf].items():
                total_load = len(inst_list)
                if req_load + total_load <= self.vm_cap[visited_vnf]:
                    local_inst_list.append(inst_id)
            if not local_inst_list:
                if (vnf_load + curr_node_load) > total_node_cap:
                    return None
                else:
                    if {visited_node: None} != prev_node_dict:
                        visited_solution[visited_vnf] = {visited_node: None}
                    else:
                        return None
                # return None
            else:
                print 'Tabu++ for best solution: Instance with visited node is found'
                visited_solution[visited_vnf] = {visited_node: random.choice(local_inst_list)}

        return visited_solution

    def find_best_neighborhood(self, curr_solution, policy):
        bst_cost_dict = OrderedDict()
        picked_vnf = None
        picked_index = None
        # apply random VNF first
        if policy == 'random':
            picked_vnf = random.choice(self.sfc_dict.keys())
        picked_index = self.sfc_dict.keys().index(picked_vnf)
        node_candidate = list()
        for node in self.graph.nodes():
            if picked_vnf in self.graph.node[node]['allowed_vnf_list']:
                node_candidate.append(node)

        trial_node = random.choice(node_candidate)    # does not make any sense to the chain configuration
        new_solution = self.find_match(curr_solution, picked_vnf, trial_node)
        if new_solution is None:
            return None, None, None

        else:
            final_solution = copy.deepcopy(new_solution)
            final_solution_info_dict = self.post_cal_total_cost(new_solution)
            if final_solution_info_dict is None:
                return None, None, None

        return {picked_vnf: final_solution[picked_vnf]}, final_solution, final_solution_info_dict
        # Since the final result did not change, the same trial is run at the end

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

    # Perfect match will be: VNF-index: node-index: instance-index
    def chain_config_cost(self, dst_nf, src_dict, node_candidate):
        # calculate number of consecutive VNFs
        config_cost = OrderedDict()
        for dst_node in node_candidate:
            if not src_dict:
                config_cost[dst_node] = 0
            else:
                src_vnf = src_dict.keys()[0]
                src_node = src_dict[src_vnf]
                for ns_id, ns_info_dict in self.sys_ns_dict.items():
                    mapping_dict = ns_info_dict['mapping']
                    # share_list = list()
                    for mp_index, mp_nf in enumerate(mapping_dict.keys()):
                        mp_node_id = mapping_dict[mp_nf]
                        if src_vnf == mp_nf and src_node == mp_node_id:
                                if mp_index < len(mapping_dict) - 1:
                                    nxt_mp_nf = mapping_dict.keys()[mp_index + 1]
                                    nxt_node = mapping_dict[nxt_mp_nf]
                                    if {dst_nf: dst_node} == {nxt_mp_nf: nxt_node}:
                                        print 'Tabu++: COUPLE map detected!!!'
                                        config_cost[dst_node] = 0
                                break
                    if config_cost.get(dst_node) == 0:
                        break
                if config_cost.get(dst_node) is None:
                    config_cost[dst_node] = 1
        return config_cost

    # Combine comp cost and config cost - chain aware
    def pre_comp_config_cost_func(self, nf_index, src_dict, graph):
        req_load = 1
        vnf_load = 1
        # comm_cost includes key (target node) and value(comm_cost)
        curr_comp_cost = OrderedDict()
        config_cost = OrderedDict()
        final_dst_node = OrderedDict()
        node_match = OrderedDict()
        load_dict = OrderedDict()
        # Determine a set of possible instances on a visited node
        for node in graph.keys():
            inst_existed = False
            if graph[node]['instances'].get(nf_index):
                nf_inst_dict = graph['instances'][nf_index]
                node_match[node] = list()
                load_dict[node] = OrderedDict()
                for inst_index, inst_info_list in nf_inst_dict.items():
                    total_load = len(inst_info_list)
                    if total_load + req_load <= self.vm_cap[nf_index]:
                        inst_existed = True
                        load_dict[node][inst_index] = total_load
                        node_match[node].append(inst_index)
                    else:
                        print 'Overloaded node', node
                        print 'current load', total_load
                        print 'Req load', req_load
                        print 'expected load', (total_load+req_load)
                        # import time
                        # time.sleep(3)

            if not inst_existed:
                # Limit the number of node by overal node capacity
                curr_node_load = graph[node]['curr_load']
                total_node_cap = graph[node]['cap']
                if (vnf_load + curr_node_load) > total_node_cap:
                    final_dst_node[node] = None
                    continue

                # curr_node_load = 0.01 if curr_node_load == 0 else curr_node_load
                exp_node_load = curr_node_load + vnf_load
                # req_load/(curr_load + req_load)
                curr_comp_cost[node] = 1 * vnf_load / float(exp_node_load)     # This is node-level index or physical node factor
                final_dst_node[node] = None        # There is no instance to reuse
                config_cost[node] = 0 if not src_dict else 1

                if node in node_match:
                    node_match.pop(node)
        # find the best instance, which is the chain-aware,  to reuse here
        if node_match:     # this is just for existing instance
            # print 'Node match:', node_match
            inst_candidate = self.matched_config_cost(nf_index, src_dict, node_match)
            # print 'Matched instance', inst_candidate
            if inst_candidate:
                # choose the min inst load
                for cd_node, cd_inst_dict in inst_candidate.items():
                    if not cd_inst_dict:
                        print 'Tabu++: can reuse but {src-int, dst-inst} not in any chain'
                        config_cost[cd_node] = 0 if not src_dict else 1
                        unmatched_inst_list = node_match[cd_node]
                        final_dst_node[cd_node] = self.unmatched_config_cost(nf_index, cd_node, unmatched_inst_list)
                        # print 'Final unmatched candidate', cd_node
                        continue
                    print 'Tabu++: couple detected!!!'
                    local_ins_dict = OrderedDict()
                    for inst_id, ns_list in cd_inst_dict.items():
                        # local_ins_dict[inst_id] = len(ns_list)
                        local_ins_dict[inst_id] = load_dict[cd_node][inst_id]
                    target_inst_id = max(local_ins_dict, key=local_ins_dict.get)
                    final_dst_node[cd_node] = target_inst_id
                    config_cost[cd_node] = 0
                    curr_node_load = graph[cd_node]['load']
                    exp_node_load = curr_node_load + vnf_load
                    cni = vnf_load / float(exp_node_load)          # computation node index
                    curr_comp_cost[cd_node] = cni * req_load / float(req_load + local_ins_dict[target_inst_id])

        if len(final_dst_node) != len(config_cost):
            print 'Tabu++: Error in comp_config_cost!'
            print final_dst_node
            print config_cost
        return curr_comp_cost, config_cost, final_dst_node
        # config_cost = 0, final_dst_node != None: reused instance, reused sub-chain
        # config_cost = 1, final_dst_node == None: new instance, new chain
        # config_cost = 1, final_dst_node != None: reused instance, new chain

    # Combine comp cost and config cost - chain aware
    def post_comp_config_cost_func(self, nf_index, src_dict, node_dict, graph):
        vnf_load = 1
        # comm_cost includes key (target node) and value(comm_cost)
        curr_comp_cost = OrderedDict()
        config_cost = OrderedDict()
        for visited_node, visited_instance in node_dict.items():            # instance can be None here
            if visited_instance is None:
                curr_node_load = graph[visited_node]['load']
                total_node_cap = graph[visited_node]['cap']
                if (vnf_load + curr_node_load) > total_node_cap:
                    continue
                exp_node_load = curr_node_load + vnf_load
                curr_comp_cost[visited_node] = vnf_load / float(exp_node_load)  # This is node-level index
                config_cost[visited_node] = 1 if src_dict else 0
            else:
                curr_comp_cost[visited_node] = 0
                match_dict = self.matched_config_cost(nf_index, src_dict, {visited_node: [visited_instance]})
                if not match_dict[visited_node]:
                    config_cost[visited_node] = 1 if src_dict else 0
                else:
                    print 'Tabu++ for the best solution: Couple detected!!!'
                    # import time
                    # time.sleep(10)
                    config_cost[visited_node] = 0

        return curr_comp_cost, config_cost

    def matched_config_cost(self, nf_index, src_dict, match_node):
        # find which node matched with existing sub-chain
        # inst here was already verified with enough resources
        inst_candidate = OrderedDict()
        for node, inst_list in match_node.items():
            inst_candidate[node] = OrderedDict()
            if src_dict:
                for inst_index in inst_list:   # inst_id changed here
                    # inst_index = inst_dict['id']
                    dst_dict = {nf_index: {node: inst_index}}
                    for ns_id, ns_info_dict in self.sys_ns_dict.items():   # ns_id changed here
                        mapping_dict = ns_info_dict['mapping']
                        for map_index, orig_nf in enumerate(mapping_dict.keys()):
                            if {orig_nf: mapping_dict[orig_nf]} == src_dict:
                                print 'Tabu++ : Source check worked!!!'
                                # print 'Destination dict', dst_dict
                                # print 'Src', src_dict
                                if map_index < len(mapping_dict) - 1:
                                    nxt_orig_nf = mapping_dict.keys()[map_index+1]
                                    # print 'Possible Mirror', {nxt_orig_nf: mapping_dict[nxt_orig_nf]}
                                    # import time
                                    # time.sleep(3)
                                    if {nxt_orig_nf: mapping_dict[nxt_orig_nf]} == dst_dict:
                                        print 'Tabu++: Match detected both for source and dest.!!!'
                                        # import time
                                        # time.sleep(5)

                                        if inst_candidate[node].get(inst_index) is None:
                                            inst_candidate[node][inst_index] = list()
                                        inst_candidate[node][inst_index].append(ns_id)
                                        break

        return inst_candidate

    def unmatched_config_cost(self, nf_index, target_node, inst_list):
        # find which node matched with existing sub-chain
        # inst here was already verified with enough resources
        inst_candidate = dict()
        for inst_index in inst_list:
            inst_candidate[inst_index] = list()
            move = {nf_index: {target_node: inst_index}}
            for ns_id, ns_info_dict in self.sys_ns_dict.items():   # ns_id changed here
                mapping_dict = ns_info_dict['mapping']
                for orig_nf, node_dict in mapping_dict.items():
                    # print 'trial', {orig_nf: node_dict}
                    # print 'actual', move
                    if {orig_nf: node_dict} == move:
                            print 'Tabu++: Dest. node matched detected!!!! But source node is different'
                            inst_candidate[inst_index].append(ns_id)
                            break
            if not inst_candidate.get(inst_index):
                print self.sys_ns_dict
                print 'why?????'
        if not inst_candidate:
            return None
        else:
            max_ns = max([len(ns_list) for inst_id, ns_list in inst_candidate.items()])
            # print 'Maximum shared!!!!!!!!!!!!!!!!!!!!!!!!!!', max_ns
            most_shared_list = [inst_id for inst_id, ns_list in inst_candidate.items() if len(ns_list) == max_ns]
            return most_shared_list[0]

    def find_coloc(self, candidate):
        conv_candidate = OrderedDict()
        for index, node in enumerate(candidate):
            if node not in conv_candidate:
                conv_candidate[node] = list()
                conv_candidate[node].append(index)
            else:
                conv_candidate[node].append(index)
        return conv_candidate

    def update_graph(self, ns_candidate, graph=None):
        # For Tabu++, target VNF instance is known
        if graph is None:
            graph = self.graph
        # Update physical node
        for vnf_index, node_dict in ns_candidate.items():
            if not node_dict:
                print 'Tabu++: Node dict error. Revise update graph'
                return
            node = node_dict.keys()[0]
            vnf_inst = node_dict[node]

            inst_info = OrderedDict()
            inst_info['ns_id'] = self.req_id
            req_load = 1
            if vnf_inst is None:
                if graph[node]['load'] + 1 > graph[node]['cap']:
                    print 'Tabu++: Load in physical node is over. Revise update_graph'
                    # print index
                    return
                graph[node]['load'] =\
                    graph[node]['load'] + 1
                inst_id = uuid.uuid4()
                node_dict[node] = inst_id       # Update ns_candidate
                graph[node]['instances'][vnf_index] = OrderedDict()
                graph[node]['instances'][vnf_index][inst_id] = list()
                graph[node]['instances'][vnf_index][inst_id].append(inst_info)
            else:
                nf_inst_list = graph[node]['instances'][vnf_index][vnf_inst]
                total_load = len(nf_inst_list)
                if req_load + total_load <= self.vm_cap[vnf_index]:
                    nf_inst_list.append(inst_info)
                else:
                    print 'Tabu++: VNF instance load is over. Revise update_graph'

    def reform_ns_candidate(self, ns_candidate):
        # ns_candidate is a list of node: VNF index:(node - instance index)
        mapping_dict = OrderedDict()
        for vnf_index, node_dict in ns_candidate.items():
            mapping_dict[vnf_index] = node_dict
        return mapping_dict

    def reform_list(self, shared_list):
        tp_list = list()
        for list_index, vnf_index in enumerate(shared_list):
            if list_index < len(shared_list) - 1:
                tp = (vnf_index, shared_list[list_index+1])
                tp_list.append(tp)
        return tp_list

    def getReqID(self):
        return self.req_id

    def get_graph(self):
        return self.graph

