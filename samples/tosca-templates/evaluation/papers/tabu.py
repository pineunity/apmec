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
ALPHA = 0.6   # weight for computation cost
GAMMA = 0.6  # Chain config cost
BETA = 0.4  # weight for routing cost
DELTA = 0.4  # reliability cost
TABU_ITER_MAX = 300   # Tabu size: stop after algorithm reaches this size
LOOP_ITER_MAX = 100   # Number of iterations is executed for each tabu search
MAX = 10**6


def split_path(path):
    split_list = list()
    for idx, val in enumerate(path):
        if (idx + 1) < len(path):
            nxt_val = path[idx + 1]
            split_list.append((val, nxt_val))
    return split_list


class Tabu(object):
    def __init__(self, nf_prop, req_dict, graph, sys_ns_dict, timer):
        self.graph = graph
        # self.ns_dict = system_ns_dict
        self.nf_prop = nf_prop
        self.req_dict = req_dict
        self.tabu_list = list()
        self.sfc_dict = self.req_dict['sfc']
        self.timer = timer
        self.req_id = uuid.uuid4()
        self.req_info = self.req_dict['info']
        self.sys_ns_dict = sys_ns_dict
        self.req_requirements = self.req_info['requirements']
        self.e2e_path = list()
        self.paid_visited_list = list()
        self.NSlen = len(self.sfc_dict)
        self.lat = self.req_info['requirements']['latency_budget']

    def execute_tabu(self):
        # This method returns initial ns_dict and initial cost
        init_candidate, init_cost = self.find_first_solution(strategy="random")
        if init_candidate is None:
            print "Algorithm failed at first step."
            return None, None
        self.e2e_path = init_cost['detailed_path'][:]
        # print 'first path', self.e2e_path
        # print 'first candidate', init_candidate
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
            # print bst_candidate, solution_info_dict['detailed_path']
            # bst_candidate, bst_cost = self.find_best_neighborhood(curr_solution, policy='paid')
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
                self.e2e_path = solution_info_dict['detailed_path'][:]
                loop_index = 0
                # if policy is paid
                self.paid_visited_list = list()
                print "Tabu worked here"
                # print 'Inner final path', solution_info_dict['detailed_path']
                # print 'Inner final candidate', final_best_candidate

        if final_best_cost >= MAX:
            print "Tabu: Unable to find better solution due the the constraint"
            print "Service latency:", self.lat
            print "Chain:", self.sfc_dict.keys()
            print "Total node processing latency:", sum([self.nf_prop['proc_delay'][nf] for nf in self.sfc_dict.keys()])
            return None, None
            # time.sleep(10)

        final_best_result_dict['config_cost'] = self.chain_config_cost(final_best_candidate, self.sys_ns_dict)
        final_best_result_dict['total_cost'] = final_best_result_dict['total_cost'] + GAMMA*final_best_result_dict['config_cost']
        # should return best candidate
        return final_best_candidate, final_best_result_dict

    # Find first solution: apply local search for this case (one-by-one)
    def find_first_solution(self, strategy):
        # total_cost is calculated from the problem formulation
        solution_info_dict = OrderedDict()
        solution_info_dict['total_cost'] = 0
        solution_info_dict['routing_cost'] = 0
        solution_info_dict['comp_cost'] = 0
        solution_info_dict['rec_cost'] = 1
        solution_info_dict['rel_cost'] = 1
        solution_info_dict['detailed_path'] = list()
        curr_solution = OrderedDict()
        est_graph = copy.deepcopy(self.graph)
        total_lat = 0
        if strategy == "random":
            for nf_index, nf_instances in self.sfc_dict.items():
                # vnf_load = self.nf_prop['proc_cap'][nf_index]
                node_candidate = list()
                for node in est_graph.nodes():
                    if nf_index in est_graph.node[node]['allowed_vnf_list']:
                        node_candidate.append(node)

                # Run comp cost function
                comp_cost_dict, node_match = self.comp_cost_func(nf_index, node_candidate[:], est_graph)
                routing_cost_dict, path_dict, path_lat = self.routing_cost_func(node_candidate[:], curr_solution, est_graph)
                rel_cost_dict = self.rel_cost_func(nf_index, node_candidate[:])
                local_node_candidate = OrderedDict()
                sub_path_dict = OrderedDict()
                for node in node_candidate:
                    if routing_cost_dict.get(node) is None or comp_cost_dict.get(node) is None:
                        routing_cost_dict[node] = MAX
                        path_dict[node] = list()
                        comp_cost_dict[node] = MAX
                        path_lat[node] = MAX
                        continue
                    if (total_lat + path_lat[node] + self.nf_prop['proc_delay'][nf_index]) > self.lat:
                        print 'Tabu: violate the latency constraint'
                        local_node_candidate[node] = MAX
                        continue
                    sub_path_dict[node] = path_dict[node]
                    local_node_candidate[node] = ALPHA * comp_cost_dict[node] + BETA * routing_cost_dict[
                        node] + DELTA * (1 - rel_cost_dict[node])
                if not local_node_candidate:
                    print 'tabu: What is the fault reason'
                    print 'At VNF-th', nf_index
                    print 'Current solution', curr_solution
                    print 'tabu: routing cost', routing_cost_dict
                    print 'Tabu: comp cost', comp_cost_dict
                    return None, None
                else:
                    final_candidate = random.choice(local_node_candidate.keys())
                    total_lat += path_lat[final_candidate] + self.nf_prop['proc_delay'][nf_index]
                    exp_total_cost = local_node_candidate[final_candidate]
                    curr_solution[nf_index] = {final_candidate: node_match[final_candidate]}
                    solution_info_dict['total_cost'] = solution_info_dict['total_cost'] + exp_total_cost
                    solution_info_dict['routing_cost'] = solution_info_dict['routing_cost'] + routing_cost_dict[final_candidate]
                    solution_info_dict['comp_cost'] = solution_info_dict['comp_cost'] + comp_cost_dict[final_candidate]
                    solution_info_dict['rec_cost'] += (1 - rel_cost_dict[final_candidate])
                    solution_info_dict['rel_cost'] = solution_info_dict['rel_cost'] * rel_cost_dict[final_candidate]
                    solution_info_dict['detailed_path'].extend(path_dict[final_candidate])
                    self.update_graph({nf_index: {final_candidate: copy.deepcopy(node_match[final_candidate])}},
                                      [nf_index], est_graph, path_dict[final_candidate])

        return curr_solution, solution_info_dict

    # This is used to calculate chain configuration cost
    # If reused instance exists, simply choose the least idle one
    def chain_config_cost(self, curr_solution, sample_dict):
        # check each chain candidate whether they have consecutive VNFs
        # dont need to check bandwidth between two consecutive VNFs since routing cost already check it
        # somewhere should store dict for mapping between vnf_index and node index
        # calculate number of consecutive VNFs
        consec_counts = 0
        forbiden_list = list()
        # ns_candidate = OrderedDict()
        for node_index, nf_index in enumerate(self.sfc_dict.keys()):
            for ns_id, ns_info_dict in sample_dict.items():
                if nf_index in forbiden_list:  # to avoid accidentally increasing consec_counts
                    break
                mapping_dict = ns_info_dict['mapping']
                # share_list = list()
                for mp_index, mp_nf in enumerate(mapping_dict.keys()):
                    mp_node_dict = mapping_dict[mp_nf]
                    if nf_index == mp_nf and curr_solution[nf_index] == mp_node_dict:
                        # print 'SINGLE map detected'
                        # share_list.append({nf_index: mp_node_id})
                        # determine number of consecutive VNFs
                        # Find the perfect mapping between VNF index and node index
                        # for index, node_index in enumerate(curr_solution):
                        # find the vnf index
                        # src_vnf_index = self.sfc_dict.keys()[index]
                        # if {src_vnf_index: node_index} in share_list:
                        if node_index < len(curr_solution) - 1:
                            dst_vnf_index = self.sfc_dict.keys()[node_index + 1]
                            dst_node_dict = curr_solution[dst_vnf_index]

                            if mp_index < len(mapping_dict) - 1:
                                nxt_mp_nf = mapping_dict.keys()[mp_index + 1]
                                nxt_node_dict = mapping_dict[nxt_mp_nf]
                                # print 'Target couple: ' + str(dst_vnf_index) + ' - ' + str(dst_node_index)
                                # print 'Candidate couple: ' + str(nxt_mp_nf) + ' - ' + str(nxt_node)
                                if {dst_vnf_index: dst_node_dict} == {nxt_mp_nf: nxt_node_dict}:
                                    print 'Tabu: COUPLE map detected!!!'
                                    consec_counts = consec_counts + 1
                                    forbiden_list.append(nf_index)
                                    break
                                    # if consec_counts:
                                    #     ns_candidate[ns_id] = consec_counts
        config_cost = (self.NSlen - 1) - consec_counts
        # config_rate = config_cost/float(self.NSlen)
        # if ns_candidate:
        #     final_candidate = max(ns_candidate, key=ns_candidate.get)
        #     config_cost = config_cost - ns_candidate[final_candidate]
        return config_cost

    def cal_total_cost(self, visited_solution):
        solution_info_dict = OrderedDict()
        solution_info_dict['total_cost'] = 0
        solution_info_dict['routing_cost'] = 0
        solution_info_dict['comp_cost'] = 0
        solution_info_dict['rec_cost'] = 0
        solution_info_dict['rel_cost'] = 1
        solution_info_dict['detailed_path'] = list()
        curr_solution = OrderedDict()
        bst_graph = copy.deepcopy(self.graph)
        total_lat = 0
        for index, vnf_index in enumerate(visited_solution.keys()):
            node_candidate_dict = visited_solution[vnf_index]
            node_candidate = node_candidate_dict.keys()
            pnode = node_candidate[0]
            node_candidate = [pnode]
            comp_cost_dict, node_match = self.comp_cost_func(vnf_index, node_candidate, bst_graph)
            routing_cost_dict, path_dict, path_lat = self.routing_cost_func(node_candidate, curr_solution, bst_graph)
            if comp_cost_dict.get(pnode) is None or routing_cost_dict.get(pnode) is None:
                return None          # also means that loop will be automatically broken
            if total_lat + path_lat[pnode] + self.nf_prop['proc_delay'][vnf_index] > self.lat:
                return None
            rel_cost_dict = self.rel_cost_func(vnf_index, node_candidate)
            curr_solution[vnf_index] = {pnode: node_match[pnode]}
            curr_cost = ALPHA*comp_cost_dict[pnode] + BETA*routing_cost_dict[pnode] + DELTA*(1 - rel_cost_dict[pnode])
            solution_info_dict['total_cost'] = solution_info_dict['total_cost'] + curr_cost
            solution_info_dict['routing_cost'] = solution_info_dict['routing_cost'] + routing_cost_dict[pnode]
            solution_info_dict['comp_cost'] = solution_info_dict['comp_cost'] + comp_cost_dict[pnode]
            solution_info_dict['rec_cost'] += (1 - rel_cost_dict[pnode])
            solution_info_dict['rel_cost'] = solution_info_dict['rel_cost'] * rel_cost_dict[pnode]
            solution_info_dict['detailed_path'].extend(path_dict[pnode])
            total_lat += path_lat[pnode] + self.nf_prop['proc_delay'][vnf_index]
            self.update_graph({vnf_index: copy.deepcopy(node_candidate_dict)}, [vnf_index], bst_graph, path_dict[pnode])
        # solution_info_dict['curr_solution'] = curr_solution
        # solution_info_dict['solution_tracking'] = visited_solution
        return solution_info_dict

    # apply proposed Tabu strategies here
    # def find_best_neighborhood(self, curr_solution, policy):
    #     bst_cost_dict = OrderedDict()
    #     picked_vnf = None
    #     picked_index = None
    #     # apply random VNF first
    #     if policy == 'random':
    #         picked_vnf = random.choice(self.sfc_dict.keys())
    #         # vnf_load = self.nf_prop['proc_cap'][picked_vnf]
    #         # print self.sfc_dict
    #         # print picked_vnf, self.sfc_dict.keys().index(picked_vnf)
    #
    #     # Expect to reduce the complexity. VNF is not picked randomly
    #     # calculate paid index of curr_solution. Choose the mapping which has min paid
    #     if policy == 'paid':
    #         # pick VNFs following paid
    #         paid_list = self.paid_engine(curr_solution, type_of_search='single')
    #         ordered_paid_tup = self.ordered_path_list(paid_list)
    #         for paid_tup in ordered_paid_tup:
    #             if paid_tup[0] not in self.paid_visited_list:
    #                 picked_index = paid_tup[0]
    #                 break
    #         print 'tupple test', picked_index
    #         self.paid_visited_list.append(picked_index)
    #         if picked_index is None:
    #             print 'revise paid!!!'
    #
    #     # from nf_index in nf_dict, find index in chain
    #     picked_index = self.sfc_dict.keys().index(picked_vnf) if picked_vnf is not None else picked_index
    #     visited_node_dict = curr_solution[self.sfc_dict.keys()[picked_index]]
    #     visited_node = visited_node_dict.keys()[0]
    #     node_candidate = list()
    #     for node in self.graph.nodes():
    #         if node != visited_node:
    #             if picked_vnf in self.graph.node[node]['allowed_vnf_list']:
    #                 # curr_node_cap = self.graph.node[node]['curr_load']
    #                 # total_node_cap = self.graph.node[node]['cpu']
    #                 # if (vnf_load + curr_node_cap) <= total_node_cap:
    #                 node_candidate.append(node)
    #     candidate_list = list()
    #     for cnode in node_candidate:
    #         temp_solution = self.find_temp_solution(curr_solution, picked_vnf, cnode)
    #         if temp_solution is None:
    #             continue
    #         solution_info_dict = self.cal_total_cost(temp_solution)
    #         if solution_info_dict is not None:
    #             temp_candidate_dict = OrderedDict()
    #             temp_candidate_dict['solution'] = copy.deepcopy(temp_solution)
    #             temp_candidate_dict['solution_info_dict'] = copy.deepcopy(solution_info_dict)
    #             candidate_list.append(temp_candidate_dict)
    #         else:
    #             continue
    #     if not candidate_list:
    #         return None, None, None
    #     else:
    #         final_bst_cost = min([candidate['solution_info_dict']['total_cost'] for candidate in candidate_list])
    #         final_candidate_list = [candidate for candidate in candidate_list if candidate['solution_info_dict']['total_cost'] == final_bst_cost]
    #         # Can think about strict constrain here
    #         final_candidate = final_candidate_list[0]
    #         final_solution = final_candidate['solution']
    #         final_solution_info_dict = final_candidate['solution_info_dict']
    #         # print 'inner path', final_candidate['solution_info_dict']['detailed_path']
    #         # print 'original solution', curr_solution
    #         # print 'candidate before cal_total_cost', final_candidate['solution']
    #         # print 'candidate after cal_total_cost', final_candidate['solution_info_dict']['curr_solution']
    #         # print 'inner detailed path', final_candidate['solution_info_dict']['detailed_path']
    #         # print 'solution_tracking', final_candidate['solution_info_dict']['solution_tracking']
    #
    #     return {picked_vnf: visited_node_dict}, final_solution, final_solution_info_dict

    # apply proposed Tabu strategies here

    def find_best_neighborhood(self, curr_solution, policy):
        bst_cost_dict = OrderedDict()
        picked_vnf = None
        picked_index = None
        # apply random VNF first
        if policy == 'random':
            picked_vnf = random.choice(self.sfc_dict.keys())
            # vnf_load = self.nf_prop['proc_cap'][picked_vnf]
            # print self.sfc_dict
            # print picked_vnf, self.sfc_dict.keys().index(picked_vnf)

        # Expect to reduce the complexity. VNF is not picked randomly
        # calculate paid index of curr_solution. Choose the mapping which has min paid
        if policy == 'paid':
            # pick VNFs following paid
            paid_list = self.paid_engine(curr_solution, type_of_search='single')
            ordered_paid_tup = self.ordered_path_list(paid_list)
            for paid_tup in ordered_paid_tup:
                if paid_tup[0] not in self.paid_visited_list:
                    picked_index = paid_tup[0]
                    break
            print 'tupple test', picked_index
            self.paid_visited_list.append(picked_index)
            if picked_index is None:
                print 'revise paid!!!'

        # from nf_index in nf_dict, find index in chain
        picked_index = self.sfc_dict.keys().index(picked_vnf) if picked_vnf is not None else picked_index
        visited_node_dict = curr_solution[self.sfc_dict.keys()[picked_index]]
        visited_node = visited_node_dict.keys()[0]
        node_candidate = list()
        for node in self.graph.nodes():
            if node != visited_node:
                if picked_vnf in self.graph.node[node]['allowed_vnf_list']:
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
        visited_solution = copy.deepcopy(orig_solution)
        prev_node_dict = visited_solution[orig_vnf]
        curr_node_load = self.graph.node[visited_node]['curr_load']
        total_node_cap = self.graph.node[visited_node]['cpu']
        if self.graph.node[visited_node]['instances'].get(orig_vnf) is None:
            if {visited_node: None} != prev_node_dict:
                if (self.nf_prop['proc_cap'][orig_vnf] + curr_node_load) > total_node_cap:
                    return None
                else:
                    # print 'choose an empty node'
                    visited_solution[orig_vnf] = {visited_node: None}
        else:
            local_inst_dict = OrderedDict()
            for inst_id, inst_list in self.graph.node[visited_node]['instances'][orig_vnf].items():
                if {visited_node: inst_id} != prev_node_dict:
                    total_load = sum([inst_info_dict['req_load'] for inst_info_dict in inst_list if
                                      inst_info_dict['lifetime'] >= self.timer])
                    if self.req_requirements['proc_cap'] + total_load <= self.nf_prop['proc_cap'][orig_vnf]:
                        local_inst_dict[inst_id] = total_load
            if not local_inst_dict:
                if (self.nf_prop['proc_cap'][orig_vnf] + curr_node_load) > total_node_cap:
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

    # def tabu_condition(self, punishment_node):
    #     return punishment_node

    # Calculate the communication cost
    def routing_cost_func(self, node_candidate, curr_solution, graph):
        path_dict = OrderedDict()
        path_lat = OrderedDict()
        # routing_cost includes key (target node) and value(routing_cost)
        curr_routing_cost = OrderedDict()
        source_node = None
        if curr_solution:
            curr_len = len(curr_solution)
            source_node_dict = curr_solution.values()[curr_len - 1]
            source_node = source_node_dict.keys()[0]
        for node in node_candidate:
            if node == source_node or not curr_solution:
                curr_routing_cost[node] = 0
                path_dict[node] = list()
                path_lat[node] = 0
            else:
                # This can return a list of paths, strictly condition needed
                path_list = nx.all_shortest_paths(graph, source=source_node, target=node)
                # path_list = nx.all_shortest_paths(self.graph, source=source_node, target=node, weight='delay')
                # Add constrains for link capacity. Traffic rate is also considered as link rate
                filtered_path = list()
                # Determine the current link usage the existing source and destination for link
                # Find link with lowest latency: path = [1 5 7]
                # visited_path = list()
                # print 'loop detection', node_candidate
                for path in path_list:
                    # if path in visited_path:
                    #    continue
                    # print path
                    # visited_path.append(path)
                    illegal_path = False
                    for pindex, pnode in enumerate(path):
                        if pindex < len(path) - 1:
                            p_snode = pnode
                            p_dnode = path[pindex+1]
                            # determine the BW usage between them. Check whether there are same NS
                            # across 2 physical nodes
                            if not nx.has_path(graph, p_snode, p_dnode):
                                print 'Tabu: There is no direct link. Revise routing_cost_func'
                                return

                            self.update_curr_link_usage(p_snode, p_dnode, graph)
                            if graph[p_snode][p_dnode]['curr_load'] + self.req_requirements['rate'] > graph[p_snode][p_dnode]['maxBW']:
                                illegal_path = True
                                break
                    if not illegal_path:
                        filtered_path.append(path)

                # nx.dijkstra_path(rdgraph, source=0, target=5, weight='avail')
                # remember here paths can have same cost but different length
                if not filtered_path:
                    continue
                else:
                    path_candidate = OrderedDict()
                    for pi, dpath in enumerate(filtered_path):
                        spath = split_path(dpath)
                        curr_load = 0
                        exp_load = 0
                        for pair in spath:
                            src_node = pair[0]
                            dst_node = pair[1]
                            self.update_curr_link_usage(src_node, dst_node, graph)
                            curr_load += graph[src_node][dst_node]['curr_load']
                            exp_load += self.req_requirements['rate']

                        path_candidate[pi] = exp_load / float(curr_load + exp_load)

                    selected_pi = min(path_candidate, key=path_candidate.get)
                    path_dict[node] = filtered_path[selected_pi]
                    lat_data = 0
                    for pindex, pnode in enumerate(path_dict[node]):
                        if pindex < len(path_dict[node]) - 1:
                            p_snode = pnode
                            p_dnode = path_dict[node][pindex + 1]
                            lat_data += graph[p_snode][p_dnode]['delay']
                    path_lat[node] = lat_data
                    curr_routing_cost[node] = path_candidate[selected_pi]
        return curr_routing_cost, path_dict, path_lat

    def update_curr_link_usage(self, src_node, dst_node, graph):
        graph[src_node][dst_node]['curr_load'] = 0
        if graph[src_node][dst_node].get('req'):
            for req in graph[src_node][dst_node]['req']:
                if req['lifetime'] >= self.timer:
                    graph[src_node][dst_node]['curr_load'] =\
                        graph[src_node][dst_node]['curr_load'] + req['rate']

    # Calculate the computation cost
    def comp_cost_func(self, nf_index, node_candidate, graph):
        req_load = self.req_requirements['proc_cap']
        vnf_load = self.nf_prop['proc_cap'][nf_index]
        # routing_cost includes key (target node) and value(routing_cost)
        curr_comp_cost = OrderedDict()
        node_match = OrderedDict()
        for node in node_candidate:
            curr_node_load = graph.node[node]['curr_load']
            total_node_cap = graph.node[node]['cpu']
            exp_node_load = curr_node_load + vnf_load
            cni = vnf_load/float(exp_node_load)
            inst_existed = False
            if graph.node[node]['instances'].get(nf_index):
                inst_dict = OrderedDict()
                nf_inst_dict = graph.node[node]['instances'][nf_index]
                for inst_index, inst_info_list in nf_inst_dict.items():
                    total_load = sum([inst_info_dict['req_load'] for inst_info_dict in inst_info_list if inst_info_dict['lifetime'] >= self.timer])
                    if req_load + total_load <= self.nf_prop['proc_cap'][nf_index]:
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
                # curr_node_load = 0.01 if curr_node_load == 0 else curr_node_load

                curr_comp_cost[node] = 1 * cni   # This is node-level index

        return curr_comp_cost, node_match

    # Calculate the reliability cost. Re-examine it
    def rel_cost_func(self, nf_index, node_candidate):
        rel_cost = OrderedDict()
        for node in node_candidate:
            node_rel = self.graph.node[node]['rel']
            origin_nf_rel = self.nf_prop['rel'][nf_index]
            nf_rel = origin_nf_rel * node_rel
            rel_cost[node] = nf_rel
        return rel_cost

    def find_coloc(self, candidate):
        conv_candidate = OrderedDict()
        for index, node in enumerate(candidate):
            if node not in conv_candidate:
                conv_candidate[node] = list()
                conv_candidate[node].append(index)
            else:
                conv_candidate[node].append(index)
        return conv_candidate

    def add_link_usage(self, src_node, dst_node, graph, test):
        # BW(src_node, dst_node) does not specify the endpoints
        if nx.has_path(graph, src_node, dst_node):
            self.update_curr_link_usage(src_node, dst_node, graph)
            if graph[src_node][dst_node]['curr_load'] + self.req_requirements['rate'] > \
                    graph[src_node][dst_node]['maxBW']:
                print 'Tabu: The link capacity is over!!! Revise add_link_usage'
                # print src_node, dst_node
            graph[src_node][dst_node]['curr_load'] = graph[src_node][dst_node]['curr_load'] + \
                                                          self.req_requirements['rate']
            if graph[src_node][dst_node].get('req') is None:
                graph[src_node][dst_node]['req'] = list()
            graph[src_node][dst_node]['req'].append(
                {'id': self.req_id, 'lifetime': self.req_info['lifetime'], 'rate': self.req_requirements['rate']})
        else:
            print 'Tabu: there is no direct link. Revise add_link_usage'

    def update_graph(self, ns_candidate, vnf_list=None, graph=None, path_list=None):
        # For Tabu, VNF instance is unknown. It does not care about it
        if graph is None:
            graph = self.graph
        if path_list is None:
            path_list = self.e2e_path
        if vnf_list is None:
            vnf_list = self.sfc_dict.keys()
        # Update physical node
        check_list = list()
        for vnf_index, node_dict in ns_candidate.items():
            if not node_dict:
                print 'Tabu: Node dict error. Revise update graph'
                return
            node = node_dict.keys()[0]
            inst_info = OrderedDict()
            inst_info['lifetime'] = self.req_info['lifetime']
            inst_info['req_load'] = self.req_requirements['proc_cap']
            inst_info['ns_id'] = self.req_id
            new_inst_detection = False
            if graph.node[node]['instances'].get(vnf_index) is None:
                new_inst_detection = True
                graph.node[node]['instances'][vnf_index] = OrderedDict()
            else:
                inst_dict = OrderedDict()
                nf_inst_dict = graph.node[node]['instances'][vnf_index]
                for inst_index, inst_info_list in nf_inst_dict.items():
                    total_load = sum([inst_info_dict['req_load'] for inst_info_dict in inst_info_list if
                                      inst_info_dict['lifetime'] >= self.timer])
                    if self.req_requirements['proc_cap'] + total_load <= self.nf_prop['proc_cap'][vnf_index]:
                        inst_dict[inst_index] = total_load
                # print 'there is instance to reuse', nf_inst_dict
                # print 'timer', self.timer
                if inst_dict:
                    # print 'successfully loaded'
                    target_inst_id = max(inst_dict, key=inst_dict.get)
                    # if vnf_list == self.sfc_dict.keys():
                        # print 'Tabu: current load', max_load
                        # print 'Tabu: request load', self.req_requirements['proc_cap']
                        # print 'expected load', (self.req_requirements['proc_cap']+max_load)
                        # print 'VNF cap', self.nf_prop['proc_cap'][vnf_index]
                    nf_inst_dict[target_inst_id].append(inst_info)
                    check_list.append({vnf_index: {node: target_inst_id}})
                else:
                    if vnf_list == self.sfc_dict.keys() and len(vnf_list) != 1:
                        print 'Tabu: new instance!!!'
                        print 'NF index', vnf_index
                    new_inst_detection = True

            if new_inst_detection:
                if graph.node[node]['curr_load'] + self.nf_prop['proc_cap'][vnf_index] > graph.node[node]['cpu']:
                    print 'Tabu: Load in physical node is over. Revise update_graph'
                    return
                graph.node[node]['curr_load'] =\
                    graph.node[node]['curr_load'] + self.nf_prop['proc_cap'][vnf_index]
                inst_id = uuid.uuid4()
                node_dict[node] = inst_id
                graph.node[node]['instances'][vnf_index][inst_id] = list()
                graph.node[node]['instances'][vnf_index][inst_id].append(inst_info)
                check_list.append({vnf_index: {node: inst_id}})
        # if vnf_list == self.sfc_dict.keys() and len(vnf_list) != 1:
            # print 'Tabu candidate after update'
            # print check_list
        # Update physical link
        for node_index, node in enumerate(path_list):
            if node_index < len(path_list) - 1:
                p_snode = node
                p_dnode = path_list[node_index + 1]
                if p_snode == p_dnode:
                    continue
                self.add_link_usage(p_snode, p_dnode, graph, len(ns_candidate))

    def get_graph(self):
        return self.graph

    def get_path(self):
        return self.e2e_path

    # def reform_ns_candidate(self, ns_candidate):
    #     # ns_candidate is a list of node
    #     mapping_dict = OrderedDict()
    #     for index, node in enumerate(ns_candidate):
    #         vnf_index = self.sfc_dict.keys()[index]
    #         mapping_dict[vnf_index] = node
    #     return mapping_dict

    def reform_ns_candidate(self, ns_candidate):
        # ns_candidate is a list of node: VNF index:(node - instance index)
        mapping_dict = OrderedDict()
        for vnf_index, node_dict in ns_candidate.items():
            mapping_dict[vnf_index] = node_dict
        return mapping_dict

    def getReqID(self):
        return self.req_id
