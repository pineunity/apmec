#!/bin/sh
from tackerclient.v1_0 import client as tacker_client
import ast

class TackerClient(object):
    """Tacker Client class for VNFM and NFVO negotiation"""

    def __init__(self, sess):
        self.client = tacker_client.Client(session=sess)

    def nsd_create(self, nsd_dict):
        nsd_instance = self.client.create_nsd(body=nsd_dict)
        if nsd_instance:
            return nsd_instance['nsd']['id']
        else:
            return None

    def nsd_get_by_name(self, nsd_name):
        nsd_dict = self.client.list_nsds()
        nsd_list = nsd_dict['nsds']
        nsd_dict = None
        for nsd in nsd_list:
            if nsd['name'] == nsd_name:
                nsd_dict = nsd
        return nsd_dict

    def nsd_get(self, nsd_id):
        nsd_dict = self.client.show_nsd(nsd_id)
        return nsd_dict['nsd']

    def ns_create(self, ns_dict):
        ns_instance = self.client.create_ns(body=ns_dict)
        if ns_instance:
            return ns_instance['ns']['id']
        else:
            return None

    def ns_get_by_name(self, ns_name):
        ns_dict = self.client.list_nsds()
        ns_list = ns_dict['nss']
        ns_id = None
        for ns in ns_list:
            if ns['name'] == ns_name:
                ns_id = ns['id']
        return ns_id

    def vim_get(self, vim_name):
        vim_dict = self.client.list_vims()
        vim_list = vim_dict['vims']
        vim_info = None
        for vim in vim_list:
            if vim['name'] == vim_name:
                vim_info = vim
        return vim_info

    def ns_get(self, ns_id):
        ns_instance = self.client.show_ns(ns_id)
        return ns_instance['ns']

    def ns_delete_by_name(self, ns_name):
        ns_id = self.ns_get_by_name(ns_name)
        if ns_id:
            self.client.delete_ns(ns_id)

    def ns_check(self, ns_id):
        ns_dict = self.client.list_nss()
        ns_list = ns_dict['nss']
        check = False
        for ns in ns_list:
            if ns['id'] == ns_id:
                check = True
        return check

    def ns_delete(self, ns_id):
        return self.client.delete_ns(ns_id)

    def ns_update(self, ns_id, ns_dict):
        return self.client.update_ns(ns_id, ns_dict)

    def vnfd_create(self, vnfd_dict):
        vnfd_instance = self.client.create_vnfd(body=vnfd_dict)
        if vnfd_instance:
            return vnfd_instance['vnf']['id']
        else:
            return None

    def vnf_create(self, vnf_dict):
        vnf_instance = self.client.create_vnf(body=vnf_dict)
        if vnf_instance:
            return vnf_instance['vnf']['id']
        else:
            return None

    def vnf_get(self, vnf_id):
        vnf_instance = self.client.show_vnf(vnf_id)
        return vnf_instance['vnf']

    def nfins_tracking(self):
        vnf_dict = self.client.list_vnfs()
        vnf_list = vnf_dict['vnfs']
        vnf_ins = dict()
        # example: VNF1:, VNF2,
        for vnf_info in vnf_list:
            if vnf_info['status'] == "ACTIVE":
                vnfd_id = vnf_info['vnfd_id']
                vnfd_info = self.client.show_vnfd(vnfd_id)
                vnfd = vnfd_info['vnfd']
                orig_vnfd_name = vnfd['name']
                vnfd_name = orig_vnfd_name[0:5]
                mgmt_dict = ast.literal_eval(vnf_info['mgmt_url'])
                nfins = len(mgmt_dict)
                if not vnf_ins.get(vnfd_name):
                    vnf_ins[vnfd_name] = 0
                vnf_ins[vnfd_name] = vnf_ins[vnfd_name] + nfins
        return vnf_ins


    def vnfd_get(self, vnfd_id):
        vnfd_instance = self.client.show_vnfd(vnfd_id)
        return vnfd_instance['vnfd']

    def vnffgd_get_by_name(self, vnffgd_name):
        vnffgd_dict = self.client.list_vnffgds()
        vnffgd_list = vnffgd_dict['vnffgds']
        vnffgd_dict = None
        for vnffgd in vnffgd_list:
            if vnffgd['name'] == vnffgd_name:
                vnffgd_dict = vnffgd
        return vnffgd_dict

    def vnffgd_get(self, vnffgd_id):
        vnffgd_instance = self.client.show_vnffgd(vnffgd_id)
        return vnffgd_instance['vnffgd']

    def vnffg_create(self, vnffgd_dict):
        vnffg_instance = self.client.create_vnffg(body=vnffgd_dict)
        if vnffg_instance:
            return vnffg_instance['vnffg']['id']
        else:
            return None

    def vnffg_get_by_name(self, vnffg_name):
        vnffg_dict = self.client.list_vnffgs()
        vnffg_list = vnffg_dict['vnffgs']
        vnffg_id = None
        for vnffg in vnffg_list:
            if vnffg['name'] == vnffg_name:
                vnffg_id = vnffg['id']
        return vnffg_id

    def vnffg_get(self, vnffg_id):
        vnffg_instance = self.client.show_vnffg(vnffg_id)
        return vnffg_instance['vnffg']

    def vnffg_delete_by_name(self, vnffg_name):
        vnffg_id = self.vnffg_get_by_name(vnffg_name)
        if vnffg_id:
            self.client.delete_vnffg(vnffg_id)

    def vnffg_delete(self, vnffg_id):
        return self.client.delete_vnffg(vnffg_id)

    def vnffg_check(self, vnffg_id):
        vnffg_dict = self.client.list_vnffgs()
        vnffg_list = vnffg_dict['vnffgs']
        check = False
        for vnffg in vnffg_list:
            if vnffg['id'] == vnffg_id:
                check = True
        return check

    def vnffg_update(self, vnffg_id, vnffg_dict):
        return self.client.update_ns(vnffg_id, vnffg_dict)

