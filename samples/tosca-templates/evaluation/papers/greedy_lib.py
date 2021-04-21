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
        for index, nf_index in enumerate(self.sfc_dict.keys()):
            src_dict = OrderedDict()
            if index:
                prev_vnf = self.sfc_dict.keys()[index - 1]
                src_dict[prev_vnf] = prev_node_dict
            # time.sleep(3)
            node_candidate = list()
            for node in est_graph.nodes():
                if nf_index in est_graph.node[node]['allowed_vnf_list']:
                    node_candidate.append(node)

            # Run comp cost function
            comp_cost_dict, config_cost_dict, match_dict = self.pre_comp_config_cost_func(nf_index, src_dict,
                                                                                          node_candidate[:], est_graph)

            # routing cost here did not include from MEA node
            routing_cost_dict, path_dict, path_lat = self.routing_cost_func(node_candidate[:], curr_solution, est_graph)
            # print 'Routing cost at first', routing_cost_dict
            rel_cost_dict = self.rel_cost_func(nf_index, node_candidate)
            # print 'Reliability cost', rel_cost_dict
            # print 'NS system', self.sys_ns_dict
            local_node_candidate = OrderedDict()
            sub_path_dict = OrderedDict()
            for node in node_candidate:
                if routing_cost_dict.get(node) is None or comp_cost_dict.get(node) is None:
                    continue

                if total_lat + path_lat[node] + self.nf_prop['proc_delay'][nf_index] > self.lat:
                    continue

                sub_path_dict[node] = path_dict[node]
                local_node_candidate[node] = ALPHA * comp_cost_dict[node] + BETA * routing_cost_dict[node] + GAMMA * config_cost_dict[node] + DELTA * (1 - rel_cost_dict[node])  # noqa
            if not local_node_candidate:
                print 'greedy: What is the fault reason'
                print 'At VNF-th', nf_index
                print 'Current solution', curr_solution
                print 'greedy: routing cost', routing_cost_dict
                print 'greddy: comp cost', comp_cost_dict
                import time
                # time.sleep(10)
                return None, None
            else:
                # print 'Total cost at first', local_node_candidate
                min_total_cost = min([cost for node, cost in local_node_candidate.items()])
                candidate_list = [node for node, cost in local_node_candidate.items() if cost == min_total_cost]
                final_candidate = candidate_list[0]
                total_lat += path_lat[final_candidate] + self.nf_prop['proc_delay'][nf_index]
                curr_solution[nf_index] = {final_candidate: match_dict[final_candidate]}
                solution_info_dict['total_cost'] = solution_info_dict['total_cost'] + min_total_cost
                solution_info_dict['config_cost'] = solution_info_dict['config_cost'] + config_cost_dict[
                    final_candidate]
                solution_info_dict['routing_cost'] = solution_info_dict['routing_cost'] + routing_cost_dict[
                    final_candidate]
                solution_info_dict['comp_cost'] = solution_info_dict['comp_cost'] + comp_cost_dict[final_candidate]
                solution_info_dict['rec_cost'] += (1 - rel_cost_dict[final_candidate])
                solution_info_dict['rel_cost'] = solution_info_dict['rel_cost'] * rel_cost_dict[final_candidate]
                solution_info_dict['detailed_path'].extend(path_dict[final_candidate])

                prev_node_dict = {final_candidate: match_dict[final_candidate]}
                # print 'First update graph', prev_node_dict
                self.update_graph({nf_index: {final_candidate: copy.deepcopy(match_dict[final_candidate])}},
                                  est_graph, path_dict[final_candidate])  # noqa

        return curr_solution, solution_info_dict

    # Calculate the routing cost cost
    def routing_cost_func(self, node_candidate, curr_solution, graph):
        path_dict = OrderedDict()
        # comm_cost includes key (target node) and value(comm_cost)
        curr_routing_cost = OrderedDict()
        path_lat = OrderedDict()
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
                # this will be a number of nodes for routing cost
                path_list = nx.all_shortest_paths(graph, source=source_node, target=node)
                # path_list = nx.all_shortest_paths(self.graph, source=source_node, target=node, weight='delay')
                # Add constrains for link capacity. Traffic rate is also considered as link rate
                filtered_path = list()
                # Determine the current link usage the existing source and destination for link
                # Find link with lowest latency: path = [1 5 7]
                # visited_path = list()
                for path in path_list:
                    illegal_path = False
                    for pindex, pnode in enumerate(path):
                        if pindex < len(path) - 1:
                            p_snode = pnode
                            p_dnode = path[pindex + 1]
                            # determine the BW usage between them. Check whether there are same NS
                            # across 2 physical nodes
                            if not nx.has_path(graph, p_snode, p_dnode):
                                print 'Greedy: There is no direct link. Revise comm_cost_func'
                                return

                            self.update_curr_link_usage(p_snode, p_dnode, graph)
                            if graph[p_snode][p_dnode]['curr_load'] + self.req_requirements['rate'] > \
                                    graph[p_snode][p_dnode]['maxBW']:
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
                    print "Greedy:", path_dict[node]
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
                    graph[src_node][dst_node]['curr_load'] = \
                        graph[src_node][dst_node]['curr_load'] + req['rate']

                    # Calculate the computation cost

                    # Combine comp cost and config cost - chain aware

    def pre_comp_config_cost_func(self, nf_index, src_dict, node_candidate, graph):
        req_load = self.req_requirements['proc_cap']
        vnf_load = self.nf_prop['proc_cap'][nf_index]
        # comm_cost includes key (target node) and value(comm_cost)
        curr_comp_cost = OrderedDict()
        config_cost = OrderedDict()
        final_dst_node = OrderedDict()
        node_match = OrderedDict()
        load_dict = OrderedDict()
        # Determine a set of possible instances on a visited node
        for node in node_candidate:
            inst_existed = False
            if graph.node[node]['instances'].get(nf_index):
                nf_inst_dict = graph.node[node]['instances'][nf_index]
                node_match[node] = list()
                print 'Checked node', node
                load_dict[node] = OrderedDict()
                for inst_index, inst_info_list in nf_inst_dict.items():
                    total_load = sum([inst_info_dict['req_load'] for inst_info_dict in inst_info_list if
                                      inst_info_dict['lifetime'] >= self.timer])
                    if req_load + total_load <= self.nf_prop['proc_cap'][nf_index]:
                        inst_existed = True
                        # node_match[node].append({'id': inst_index, 'curr_load': total_load})
                        load_dict[node][inst_index] = total_load
                        node_match[node].append(inst_index)
                    else:
                        print 'Overloaded node', node
                        print 'current load', total_load
                        print 'Req load', req_load
                        print 'expected load', (total_load + req_load)
                        print 'VNF cap', self.nf_prop['proc_cap'][nf_index]
            if not inst_existed:
                # Limit the number of node by overal node capacity
                curr_node_load = graph.node[node]['curr_load']
                total_node_cap = graph.node[node]['cpu']
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
                    curr_node_load = graph.node[cd_node]['curr_load']
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
                            # if src_dict:
                                # print 'check the match'
                                # print {orig_nf: mapping_dict[orig_nf]}
                                # print src_dict
                                # import time
                                # time.sleep(2)
                            if {orig_nf: mapping_dict[orig_nf]} == src_dict:
                                # print 'I am here'
                                # print 'Destination dict', dst_dict
                                # print 'Src', src_dict
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

    # Calculate the reliability cost. Re-examine it
    def rel_cost_func(self, nf_index, node_candidate):
        rel_cost = OrderedDict()
        for node in node_candidate:
            node_rel = self.graph.node[node]['rel']
            origin_nf_rel = self.nf_prop['rel'][nf_index]
            nf_rel = origin_nf_rel * node_rel
            rel_cost[node] = nf_rel
        return rel_cost

    # This is used to calculate chain configuration cost
    # def chain_config_cost(self, curr_solution, sample_dict):
    #     # check each chain candidate whether they have consecutive VNFs
    #     # dont need to check bandwidth between two consecutive VNFs since routing cost already check it
    #     # somewhere should store dict for mapping between vnf_index and node index
    #     # calculate number of consecutive VNFs
    #     consec_counts = 0
    #     forbiden_list = list()
    #     # ns_candidate = OrderedDict()
    #     for node_index, nf_index in enumerate(self.sfc_dict.keys()):
    #         for ns_id, ns_info_dict in sample_dict.items():
    #             if nf_index in forbiden_list:  # to avoid accidentally increasing consec_counts
    #                 break
    #             mapping_dict = ns_info_dict['mapping']
    #             # share_list = list()
    #             for mp_index, mp_nf in enumerate(mapping_dict.keys()):
    #                 mp_node_id = mapping_dict[mp_nf]
    #                 if nf_index == mp_nf and curr_solution[node_index] == mp_node_id:
    #                     # print 'SINGLE map detected'
    #                     # share_list.append({nf_index: mp_node_id})
    #                     # determine number of consecutive VNFs
    #                     # Find the perfect mapping between VNF index and node index
    #                     # for index, node_index in enumerate(curr_solution):
    #                     # find the vnf index
    #                     # src_vnf_index = self.sfc_dict.keys()[index]
    #                     # if {src_vnf_index: node_index} in share_list:
    #                     if node_index < len(curr_solution) - 1:
    #                         dst_vnf_index = self.sfc_dict.keys()[node_index + 1]
    #                         dst_node_index = curr_solution[node_index + 1]
    #
    #                         if mp_index < len(mapping_dict) - 1:
    #                             nxt_mp_nf = mapping_dict.keys()[mp_index + 1]
    #                             nxt_node = mapping_dict[nxt_mp_nf]
    #                             # print 'Target couple: ' + str(dst_vnf_index) + ' - ' + str(dst_node_index)
    #                             # print 'Candidate couple: ' + str(nxt_mp_nf) + ' - ' + str(nxt_node)
    #                             if {dst_vnf_index: dst_node_index} == {nxt_mp_nf: nxt_node}:
    #                                 print 'COUPLE map detected!!!'
    #                                 consec_counts = consec_counts + 1
    #                                 forbiden_list.append(nf_index)
    #                                 break
    #                                 # if consec_counts:
    #                                 #     ns_candidate[ns_id] = consec_counts
    #     config_cost = (self.NSlen - 1) - consec_counts
    #     config_rate = config_cost / float(self.NSlen)
    #     # if ns_candidate:
    #     #     final_candidate = max(ns_candidate, key=ns_candidate.get)
    #     #     config_cost = config_cost - ns_candidate[final_candidate]
    #     return config_rate

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

    # The good thing of paid is calculate the reliability of all VNFs on the same node
    # type_of_search=single, cluster
    def paid_engine(self, candidate, type_of_search):
        paid_list = list()
        if type_of_search == 'single':
            for nf_index, nf_inst in self.sfc_dict:
                index = self.sfc_dict.keys().index(nf_index)
                target_node = candidate[index]
                rel = self.graph.node[target_node]['rel']
                # availability if this node is shared with other VNFs in chain
                for cindex in self.find_coloc(target_node):
                    dup_nf_index = self.sfc_dict.keys()[cindex]
                    rel = rel * self.nf_prop['rel'][dup_nf_index]
                # load_index = req_load/curr_load      # This is VNF-level index
                req_load = self.req_requirements['proc_cap']
                inst_dict = OrderedDict()
                min_load = 0.01
                if self.graph.node[target_node]['instances'].get(nf_index):
                    nf_inst_dict = self.graph.node[target_node]['instances'][nf_index]
                    for inst_index, inst_info_list in nf_inst_dict.items():
                        total_load = sum([inst_info_dict['vnf_load'] for inst_info_dict in inst_info_list if
                                          inst_info_dict['lifetime'] >= self.timer])
                        if req_load + total_load <= self.nf_prop['proc_cap'][nf_index]:
                            inst_dict[inst_index] = total_load
                if inst_dict:
                    min_load = min([load for inst_index, load in inst_dict.items()])
                reuse_factor = req_load / float(min_load)
                paid = rel / reuse_factor
                paid_list.append(paid)

        if type_of_search == 'cluster':
            return []
        return paid_list

    def find_coloc(self, candidate):
        conv_candidate = OrderedDict()
        for index, node in enumerate(candidate):
            if node not in conv_candidate:
                conv_candidate[node] = list()
                conv_candidate[node].append(index)
            else:
                conv_candidate[node].append(index)
        return conv_candidate

    def add_link_usage(self, src_node, dst_node, graph):
        # BW(src_node, dst_node) does not specify the endpoints
        if nx.has_path(graph, src_node, dst_node):
            self.update_curr_link_usage(src_node, dst_node, graph)
            if graph[src_node][dst_node]['curr_load'] + self.req_requirements['rate'] > \
                    graph[src_node][dst_node]['maxBW']:
                print 'Greedy: The link capacity is over!!! Revise add_link_usage'
            graph[src_node][dst_node]['curr_load'] = graph[src_node][dst_node]['curr_load'] + \
                                                          self.req_requirements['rate']
            if graph[src_node][dst_node].get('req') is None:
                graph[src_node][dst_node]['req'] = list()
            graph[src_node][dst_node]['req'].append(
                {'id': self.req_id, 'lifetime': self.req_info['lifetime'], 'rate': self.req_requirements['rate']})
        else:
            print 'Greedy: there is no direct link. Revise add_link_usage'

    def update_graph(self, ns_candidate, graph=None, path_list=None):
        # For Greedy, target VNF instance is known
        if graph is None:
            graph = self.graph
        if path_list is None:
            path_list = self.e2e_path
        # Update physical node
        for vnf_index, node_dict in ns_candidate.items():
            if not node_dict:
                print 'Greedy: Node dict error. Revise update graph'
                return
            node = node_dict.keys()[0]
            vnf_inst = node_dict[node]

            inst_info = OrderedDict()
            inst_info['lifetime'] = self.req_info['lifetime']
            inst_info['req_load'] = self.req_requirements['proc_cap']
            inst_info['ns_id'] = self.req_id

            if vnf_inst is None:
                if graph.node[node]['curr_load'] + self.nf_prop['proc_cap'][vnf_index] > graph.node[node]['cpu']:
                    print 'Greedy: Load in physical node is over. Revise update_graph'
                    # print index
                    return
                graph.node[node]['curr_load'] =\
                    graph.node[node]['curr_load'] + self.nf_prop['proc_cap'][vnf_index]
                inst_id = uuid.uuid4()
                node_dict[node] = inst_id       # Update ns_candidate
                graph.node[node]['instances'][vnf_index] = OrderedDict()
                graph.node[node]['instances'][vnf_index][inst_id] = list()
                graph.node[node]['instances'][vnf_index][inst_id].append(inst_info)
            else:
                nf_inst_list = graph.node[node]['instances'][vnf_index][vnf_inst]
                total_load = sum([inst_info_dict['req_load'] for inst_info_dict in nf_inst_list if
                                  inst_info_dict['lifetime'] >= self.timer])
                if self.req_requirements['proc_cap'] + total_load <= self.nf_prop['proc_cap'][vnf_index]:
                    nf_inst_list.append(inst_info)
                else:
                    print 'Greedy: VNF instance load is over. Revise update_graph'

        # Update physical link
        for node_index, node in enumerate(path_list):
            if node_index < len(path_list) - 1:
                p_snode = node
                p_dnode = path_list[node_index + 1]
                if p_snode == p_dnode:
                    continue
                self.add_link_usage(p_snode, p_dnode, graph)

    def get_graph(self):
        return self.graph

    def get_path(self):
        return self.e2e_path

    def getReqID(self):
        return self.req_id

    def reform_ns_candidate(self, ns_candidate):
        # ns_candidate is a list of node: VNF index:(node - instance index)
        mapping_dict = OrderedDict()
        for vnf_index, node_dict in ns_candidate.items():
            mapping_dict[vnf_index] = node_dict
        return mapping_dict

