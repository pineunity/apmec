# Greedy search expects to have lowest complexity. Desc: Run only the initial algorithm in Tabu-based schemes
from collections import OrderedDict
import networkx as nx
import uuid
import copy

# Set weight for problem optimization
ALPHA = 0.6   # weight for communication cost
GAMMA = 0.6  # weight for chain configuration cost
BETA = 0.4  # weight for routing cost
DELTA = 0.4  # weight for reliability cost
TABU_ITER_MAX = 30   # Tabu size: stop after algorithm reaches this size
LOOP_ITER_MAX = 10   # Number of iterations is executed for each tabu search


class GreedyLib(object):
    def __init__(self, req_list, graph, sys_nf_info, vm_cap):
        self.graph = graph
        # self.ns_dict = system_ns_dict
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
        total_lat = 0
        # node:{vnf_index: instance_id} if reuse, else: node:{vnf_index: None}
        prev_node_dict = OrderedDict()
        for index, nf_index in enumerate(self.sfc_dict):
            src_dict = OrderedDict()
            if index:
                prev_vnf = self.sfc_dict[index - 1]
                src_dict[prev_vnf] = prev_node_dict
            # time.sleep(3)
            node_candidate = list()
            for node in est_graph:
                if nf_index in est_graph[node]['allowed_vnf_list']:
                    node_candidate.append(node)

            # Run comp cost function
            comp_cost_dict, config_cost_dict, match_dict = self.pre_comp_config_cost_func(nf_index, src_dict,
                                                                                          node_candidate[:], est_graph)

            local_node_candidate = OrderedDict()
            for node in node_candidate:
                if comp_cost_dict.get(node) is None:
                    continue
                local_node_candidate[node] = ALPHA * comp_cost_dict[node] + BETA * config_cost_dict[node]     # noqa
            if not local_node_candidate:
                print 'greedy: What is the fault reason'
                print 'At VNF-th', nf_index
                print 'Current solution', curr_solution
                print 'greddy: comp cost', comp_cost_dict
                return None, None, None
            else:
                # print 'Total cost at first', local_node_candidate
                min_total_cost = min([cost for node, cost in local_node_candidate.items()])
                candidate_list = [node for node, cost in local_node_candidate.items() if cost == min_total_cost]
                final_candidate = candidate_list[0]
                curr_solution[nf_index] = {final_candidate: match_dict[final_candidate]}
                solution_info_dict['total_cost'] = solution_info_dict['total_cost'] + min_total_cost
                solution_info_dict['config_cost'] = solution_info_dict['config_cost'] + config_cost_dict[
                    final_candidate]
                solution_info_dict['comp_cost'] = solution_info_dict['comp_cost'] + comp_cost_dict[final_candidate]

                prev_node_dict = {final_candidate: match_dict[final_candidate]}
                # print 'First update graph', prev_node_dict
                self.update_graph({nf_index: {final_candidate: copy.deepcopy(match_dict[final_candidate])}},
                                  est_graph)  # noqa

        return curr_solution, solution_info_dict, curr_solution

    def pre_comp_config_cost_func(self, nf_index, src_dict, node_candidate, graph):
        req_load = 1
        vnf_load = 1
        # comm_cost includes key (target node) and value(comm_cost)
        curr_comp_cost = OrderedDict()
        config_cost = OrderedDict()
        final_dst_node = OrderedDict()
        node_match = OrderedDict()
        load_dict = OrderedDict()
        # Determine a set of possible instances on a visited node
        for node in node_candidate:
            inst_existed = False
            if graph[node]['instances'].get(nf_index):
                nf_inst_dict = graph[node]['instances'][nf_index]
                node_match[node] = list()
                print 'Checked node', node
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
                        print 'expected load', (total_load + req_load)
            if not inst_existed:
                # Limit the number of node by overal node capacity
                curr_node_load = graph[node]['load']
                total_node_cap = graph[node]['cap']
                if (vnf_load + curr_node_load) > total_node_cap:
                    continue
                # curr_node_load = 0.01 if curr_node_load == 0 else curr_node_load
                exp_node_load = curr_node_load + vnf_load
                curr_comp_cost[node] = vnf_load / float(exp_node_load)  # This is node-level index
                final_dst_node[node] = None  # There is no instance to reuse
                config_cost[node] = 0 if not src_dict else 1

                if node in node_match:
                    node_match.pop(node)
        # find the best instance, which is the chain-aware,  to reuse here
        if node_match:  # this is just for existing instance
            print 'Node match:', node_match
            inst_candidate = self.matched_config_cost(nf_index, src_dict, node_match)
            print 'Matched instance', inst_candidate
            if inst_candidate:
                # choose the min inst load
                for cd_node, cd_inst_dict in inst_candidate.items():
                    if not cd_inst_dict:
                        print 'Greedy: can reuse but {src-int, dst-inst} not in any chain'
                        config_cost[cd_node] = 0 if not src_dict else 1
                        unmatched_inst_list = node_match[cd_node]
                        final_dst_node[cd_node] = self.unmatched_config_cost(nf_index, cd_node, unmatched_inst_list)
                        print 'Final unmatched candidate', cd_node
                        continue
                    print 'Greedy: couple detected!!!'
                    local_ins_dict = OrderedDict()
                    for inst_id, ns_list in cd_inst_dict.items():
                        local_ins_dict[inst_id] = load_dict[cd_node][inst_id]
                    target_inst_id = max(local_ins_dict, key=local_ins_dict.get)
                    final_dst_node[cd_node] = target_inst_id
                    config_cost[cd_node] = 0
                    curr_node_load = graph[cd_node]['load']
                    exp_node_load = curr_node_load + vnf_load
                    cni = vnf_load / float(exp_node_load)  # computation node index
                    curr_comp_cost[cd_node] = cni * req_load / float(req_load + local_ins_dict[target_inst_id])

        if len(final_dst_node) != len(config_cost):
            print 'Greedy: Error in comp_config_cost!'
            print final_dst_node
            print config_cost
        return curr_comp_cost, config_cost, final_dst_node

    def matched_config_cost(self, nf_index, src_dict, match_node):
        # find which node matched with existing sub-chain
        # inst here was already verified with enough resources
        inst_candidate = dict()
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
                                if map_index < len(mapping_dict) - 1:
                                    nxt_orig_nf = mapping_dict.keys()[map_index+1]
                                    # print 'Possible Mirror', {nxt_orig_nf: mapping_dict[nxt_orig_nf]}
                                    # import time
                                    # time.sleep(3)
                                    if {nxt_orig_nf: mapping_dict[nxt_orig_nf]} == dst_dict:
                                        # print 'Match detected!!!'

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
                            print 'Instance matched detected!!!!'
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

    # This is used to calculate chain configuration cost
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
                                # print 'Target couple: ' + str(dst_vnf_index) + ' - ' + str(dst_node_index)
                                # print 'Candidate couple: ' + str(nxt_mp_nf) + ' - ' + str(nxt_node)
                                if {dst_nf: dst_node} == {nxt_mp_nf: nxt_node}:
                                    print 'Greedy: COUPLE map detected!!!'
                                    config_cost[dst_node] = 0
                            break
                    if config_cost.get(dst_node) == 0:
                        break
                if config_cost.get(dst_node) is None:
                    config_cost[dst_node] = 1
        return config_cost

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
                graph[node]['load'] += 1
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

    def get_graph(self):
        return self.graph

    def getReqID(self):
        return self.req_id

    def reform_ns_candidate(self, ns_candidate):
        # ns_candidate is a list of node: VNF index:(node - instance index)
        mapping_dict = OrderedDict()
        for vnf_index, node_dict in ns_candidate.items():
            mapping_dict[vnf_index] = node_dict
        return mapping_dict

