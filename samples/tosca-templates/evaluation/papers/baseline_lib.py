# Greedy search expects to have lowest complexity
from collections import OrderedDict
import networkx as nx
import uuid
import copy
import time

# Set weight for problem optimization
ALPHA = 0.6   # weight for computation cost
GAMMA = 0.6  # weight for chain configuration cost
BETA = 0.4  # weight for routing cost
DELTA = 0.4  # weight for reliability cost
TABU_ITER_MAX = 40   # Tabu size: stop after algorithm reaches this size
LOOP_ITER_MAX = 60   # Number of iterations is executed for each tabu search


def split_path(path):
    split_list = list()
    for idx, val in enumerate(path):
        if (idx + 1) < len(path):
            nxt_val = path[idx + 1]
            split_list.append((val, nxt_val))
    return split_list


class BaselineLib(object):
    def __init__(self, nf_prop, req_dict, graph, sys_ns_dict, timer):
        self.graph = graph
        self.nf_prop = nf_prop
        self.req_dict = req_dict
        self.sfc_dict = self.req_dict['sfc']
        self.timer = timer
        self.req_id = uuid.uuid4()
        self.req_info = self.req_dict['info']
        self.req_requirements = self.req_info['requirements']
        self.e2e_path = list()
        self.NSlen = len(self.sfc_dict)
        self.sys_ns_dict = sys_ns_dict
        self.lat = self.req_info['requirements']['latency_budget']

    # Find first solution: apply local search for this case (one-by-one)
    def execute_greedy(self):
        # total_cost is calculated from the problem formulation
        solution_info_dict = OrderedDict()
        solution_info_dict['total_cost'] = 0
        solution_info_dict['config_cost'] = 0
        solution_info_dict['comp_cost'] = 0
        solution_info_dict['detailed_path'] = list()
        curr_solution = OrderedDict()
        est_graph = copy.deepcopy(self.graph)
        total_lat = 0
        for index, nf_index in enumerate(self.sfc_dict.keys()):
            src_dict = OrderedDict()
            if index:
                prev_vnf = self.sfc_dict.keys()[index - 1]
                src_dict[prev_vnf] = curr_solution[prev_vnf]
            node_candidate = list()
            for node in est_graph.nodes():
                if nf_index in est_graph.node[node]['allowed_vnf_list']:
                    node_candidate.append(node)

            # Run comp cost function
            comp_cost_dict = self.comp_cost_func(nf_index, node_candidate[:], est_graph)
            routing_cost_dict, path_dict, path_lat = self.routing_cost_func(node_candidate[:], curr_solution, est_graph)
            rel_cost_dict = self.rel_cost_func(nf_index, node_candidate[:])
            local_node_candidate = OrderedDict()
            sub_path_dict = OrderedDict()
            for node in node_candidate:
                if routing_cost_dict.get(node) is None or comp_cost_dict.get(node) is None:
                    continue
                if (total_lat + path_lat[node] + self.nf_prop['proc_delay'][nf_index]) > self.lat:
                    continue

                sub_path_dict[node] = path_dict[node]
                local_node_candidate[node] = \
                    ALPHA * comp_cost_dict[node] + BETA * routing_cost_dict[node] + GAMMA*1 + DELTA * (1 - rel_cost_dict[node])    # a special case without reuse

            if not local_node_candidate:
                print 'baseline: What is the fault reason'
                print 'At VNF-th', nf_index
                print 'Current solution', curr_solution
                print 'Node candidate', node_candidate
                print 'baseline: comp cost', comp_cost_dict
                import time
                # time.sleep(50)

                return None, None
            else:
                min_total_cost = min([cost for node, cost in local_node_candidate.items()])
                candidate_list = [node for node, cost in local_node_candidate.items() if cost == min_total_cost]
                final_candidate = candidate_list[0]
                total_lat += path_lat[final_candidate] + self.nf_prop['proc_delay'][nf_index]
                curr_solution[nf_index] = final_candidate
                solution_info_dict['total_cost'] = solution_info_dict['total_cost'] + min_total_cost
                solution_info_dict['routing_cost'] = solution_info_dict['routing_cost'] + routing_cost_dict[final_candidate]   # noqa
                solution_info_dict['comp_cost'] = solution_info_dict['comp_cost'] + comp_cost_dict[final_candidate]
                solution_info_dict['rec_cost'] += (1 - rel_cost_dict[final_candidate])
                solution_info_dict['rel_cost'] = solution_info_dict['rel_cost'] * rel_cost_dict[final_candidate]
                solution_info_dict['detailed_path'].extend(path_dict[final_candidate])
                self.update_graph([final_candidate], [nf_index], est_graph, path_dict[final_candidate])

        if curr_solution:
            solution_info_dict['config_cost'] = (len(self.sfc_dict) - 1)

        return curr_solution, solution_info_dict

    # Calculate the communication cost
    def routing_cost_func(self, node_candidate, curr_solution, est_graph):
        print "node candidate", node_candidate
        path_dict = OrderedDict()
        path_lat = OrderedDict()
        # routing_cost includes key (target node) and value(routing_cost)
        curr_routing_cost = OrderedDict()
        source_node = None
        if curr_solution:
            curr_len = len(curr_solution)
            source_node = curr_solution.values()[curr_len - 1]
        for node in node_candidate:
            if node == source_node or not curr_solution:
                curr_routing_cost[node] = 0
                path_dict[node] = list()
                path_lat[node] = 0
            else:
                # This can return a list of paths, strictly condition needed
                path_list = nx.all_shortest_paths(est_graph, source=source_node, target=node, weight='delay')
                # Add constrains for link capacity. Traffic rate is also considered as link rate
                filtered_path = list()
                for path in path_list:
                    illegal_path = False
                    for pindex, pnode in enumerate(path):
                        if pindex < len(path) - 1:
                            p_snode = pnode
                            p_dnode = path[pindex + 1]
                            # determine the BW usage between them. Check whether there are same NS
                            # across 2 physical nodes
                            if not nx.has_path(est_graph, p_snode, p_dnode):
                                print 'There is no direct link. Revise routing_cost_func'
                                return

                            self.update_curr_link_usage(p_snode, p_dnode, est_graph)
                            if est_graph[p_snode][p_dnode]['curr_load'] + self.req_requirements['rate'] > \
                                    est_graph[p_snode][p_dnode]['maxBW']:
                                illegal_path = True
                                break
                    if not illegal_path:
                        filtered_path.append(path)
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
                            self.update_curr_link_usage(src_node, dst_node, est_graph)
                            curr_load += est_graph[src_node][dst_node]['curr_load']
                            exp_load += self.req_requirements['rate']
                        path_candidate[pi] = exp_load / float(curr_load + exp_load)
                    selected_pi = min(path_candidate, key=path_candidate.get)
                    path_dict[node] = filtered_path[selected_pi]
                    lat_data = 0
                    for pindex, pnode in enumerate(path_dict[node]):
                        if pindex < len(path_dict[node]) - 1:
                            p_snode = pnode
                            p_dnode = path_dict[node][pindex + 1]
                            lat_data += est_graph[p_snode][p_dnode]['delay']
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
    def comp_cost_func(self, nf_index, node_candidate, est_graph):
        vnf_load = self.nf_prop['proc_cap'][nf_index]
        # routing_cost includes key (target node) and value(routing_cost)
        curr_comp_cost = OrderedDict()
        for node in node_candidate:
                # Limit the number of node by overal node capacity
                curr_node_load = est_graph.node[node]['curr_load']
                total_node_cap = est_graph.node[node]['cpu']
                if (vnf_load + curr_node_load) > total_node_cap:
                    continue
                # curr_node_load = 0.01 if curr_node_load == 0 else curr_node_load
                exp_node_load = curr_node_load + vnf_load
                curr_comp_cost[node] = vnf_load / float(exp_node_load)  # This is node-level index
        return curr_comp_cost

    # Calculate the reliability cost. Re-examine it
    def rel_cost_func(self, nf_index, node_candidate):
        rel_cost = OrderedDict()
        for node in node_candidate:
            node_rel = self.graph.node[node]['rel']
            origin_nf_rel = self.nf_prop['rel'][nf_index]
            nf_rel = origin_nf_rel * node_rel
            rel_cost[node] = nf_rel
        return rel_cost

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
                print 'Baseline: the link capacity is over. Revise add_link_usage'
                return
            graph[src_node][dst_node]['curr_load'] = graph[src_node][dst_node]['curr_load'] + \
                                                          self.req_requirements['rate']
            if graph[src_node][dst_node].get('req') is None:
                graph[src_node][dst_node]['req'] = list()
            graph[src_node][dst_node]['req'].append(
                {'id': self.req_id, 'lifetime': self.req_info['lifetime'], 'rate': self.req_requirements['rate']})
        else:
            print 'Baseline: there is no direct link. Revise add_link_usage'
            return

    def update_graph(self, ns_candidate, vnf_list=None, graph=None, path_list=None):
        if graph is None:
            graph = self.graph
        if path_list is None:
            path_list = self.e2e_path
        if vnf_list is None:
            vnf_list = self.sfc_dict.keys()
        # Update physical node
        for index, node in enumerate(ns_candidate):
            vnf_index = vnf_list[index]

            inst_info = OrderedDict()
            if graph.node[node]['instances'].get(vnf_index) is None:
                graph.node[node]['instances'][vnf_index] = OrderedDict()
            inst_info['lifetime'] = self.req_info['lifetime']
            inst_info['req_load'] = self.req_requirements['proc_cap']
            inst_info['ns_id'] = self.req_id
            if graph.node[node]['curr_load'] + self.nf_prop['proc_cap'][vnf_index] > \
                    graph.node[node]['cpu']:
                    print 'Baseline: Load in physical node is over. Revise update_graph'
                    return

            graph.node[node]['curr_load'] = \
                graph.node[node]['curr_load'] + self.nf_prop['proc_cap'][vnf_index]
            inst_id = uuid.uuid4()
            graph.node[node]['instances'][vnf_index][inst_id] = list()
            graph.node[node]['instances'][vnf_index][inst_id].append(inst_info)
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
        # ns_candidate is a list of node
        mapping_dict = OrderedDict()
        for index, node in enumerate(ns_candidate):
            vnf_index = self.sfc_dict.keys()[index]
            mapping_dict[vnf_index] = node
        return mapping_dict

