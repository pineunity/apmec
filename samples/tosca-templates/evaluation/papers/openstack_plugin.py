#!/bin/sh
from keystoneauth1 import identity
import sys
import yaml
#import os
from keystoneauth1 import identity
from keystoneauth1 import session

import tacker_client
import apmec_client


# from novaclient.v2 import client as nova_client
from novaclient import client as nova_client


auth = identity.Password(auth_url='http://192.168.0.4/identity/v3',
                      username='admin',
                      password='devstack',
                      project_name='admin',
                      project_id = None,
                      project_domain_name='Default',
                      user_domain_name='Default')
sess = session.Session(auth=auth, verify=False)


nfv_client = tacker_client.TackerClient(sess)
mec_client = apmec_client.ApmecClient(sess)


def yaml_file(sample):
    base_path = os.path.dirname(os.path.abspath(__file__))
    path = base_path + '/' + sample
    with open(path, 'r') as f:
      sample_dict = yaml.safe_load(f.read())

    return sample_dict

# Get tenant if from vim
nfv_vim_info = nfv_client.vim_get(vim_name='vim0')
#print(nfv_vim_info)
nfv_tenant_id = nfv_vim_info['tenant_id']

mec_vim_info = mec_client.vim_get(vim_name='vim0')
mec_tenant_id = mec_vim_info['tenant_id']


def nfins_tracking():
    nfins_dict = getattr(nfv_client, 'nfins_tracking')()
    return nfins_dict


def ns_create(ns_name):
    sepa_sample = yaml_file(sample='sepa-nsd.yaml')
    ns_dict = {'ns': {'nsd_template': sepa_sample, 'name': ns_name,
                         'description': '', 'tenant_id': nfv_tenant_id,
                                     'vim_id': '', 'attributes': {}}}
    #print nfv_client.ns_create(ns_dict)
    return getattr(nfv_client, 'ns_create')(ns_dict)


def mes_create(mes_name):
    coop_sample = yaml_file(sample='test_simple_mesd.yaml')
    mes_dict = {'mes': {'mesd_template': coop_sample, 'name': mes_name,
                         'description': '', 'tenant_id': mec_tenant_id,
                                     'vim_id': '', 'attributes': {}}}
    # print(mes_dict)
    mes_instance = getattr(mec_client, 'mes_create')(mes_dict)
    return mes_instance

def get_nfins():
    n_client = nova_client.Client(version='2', session=sess)
    return len(n_client.servers.list())


