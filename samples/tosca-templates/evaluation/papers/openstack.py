#!/bin/sh
from keystoneauth1 import identity
import sys
import yaml
import os
from keystoneauth1 import identity
from keystoneauth1 import session

import tacker_client
import apmec_client


# from novaclient.v2 import client as nova_client
from novaclient import client as nova_client


first_arg = sys.argv[1]  # Function name
second_arg = sys.argv[2]  # Data


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
nfv_vim_info = nfv_client.vim_get(vim_name='VIM0')
nfv_tenant_id = nfv_vim_info['tenant_id']

mec_vim_info = mec_client.vim_get(vim_name='VIM0')
mec_tenant_id = mec_vim_info['tenant_id']


def nfins_tracking():
    nfins_dict = getattr(nfv_client, first_arg)()
    return nfins_dict


if 'ns_create' in first_arg:
    sepa_sample = yaml_file(sample='sepa-nsd.yaml')
    ns_dict = {'ns': {'nsd_template': sepa_sample, 'name': second_arg,
                         'description': '', 'tenant_id': nfv_tenant_id,
                                     'vim_id': '', 'attributes': {}}}
    #print nfv_client.ns_create(ns_dict)
    print getattr(nfv_client, first_arg)(ns_dict)


if 'mes_create' in first_arg:
    coop_sample = yaml_file(sample='coop-mesd.yaml')
    mes_dict = {'mes': {'mesd_template': coop_sample, 'name': second_arg,
                         'description': '', 'tenant_id': mec_tenant_id,
                                     'vim_id': '', 'attributes': {}}}
    mes_instance = getattr(mec_client, first_arg)(mes_dict)
    print mes_instance
    # if not isinstance(mes_id, dict):
    #     mes_info = mec_client.mes_get(mes_id)
    #     reused_dict = mes_info['reused']
    #     print reused_dict
    # else:
    #     print None

if 'tracking' in first_arg:
    print nfins_tracking()

if 'get_nfins' in first_arg:
    n_client = nova_client.Client(version='2', session=sess)
    # print len(n_client.servers.list(search_opts={'status': 'ACTIVE'}))
    print len(n_client.servers.list())

sys.stdout.flush()
