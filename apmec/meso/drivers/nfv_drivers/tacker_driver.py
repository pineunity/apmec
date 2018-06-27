#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
from keystoneauth1 import identity
from keystoneauth1 import session
from tackerclient.v1_0 import client as tacker_client


# Copyright 2016 Brocade Communications System, Inc.
# All Rights Reserved.
#
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import os
import six
import yaml

from apmec._i18n import _
from apmec.common import log
from apmec.extensions import meo
from apmec.keymgr import API as KEYMGR_API
from apmec.mistral import mistral_client
from apmec.meso.drivers.nfv_drivers import abstract_driver
from apmec.meo.drivers.workflow import workflow_generator
from apmec.mem import keystone

from keystoneauth1 import exceptions
from keystoneauth1 import identity
from keystoneauth1.identity import v2
from keystoneauth1.identity import v3
from keystoneauth1 import session
from oslo_config import cfg
from oslo_log import log as logging

LOG = logging.getLogger(__name__)
CONF = cfg.CONF

OPTS = [cfg.StrOpt('openstack', default='/etc/apmec/vim/fernet_keys',
                   help='Dir.path to store fernet keys.'),
        cfg.BoolOpt('use_barbican', default=False,
                    help=_('Use barbican to encrypt vim password if True, '
                           'save vim credentials in local file system '
                           'if False'))
        ]

# same params as we used in ping monitor driver
OPENSTACK_OPTS = [
    cfg.StrOpt('count', default='1',
               help=_('number of ICMP packets to send')),
    cfg.StrOpt('timeout', default='1',
               help=_('number of seconds to wait for a response')),
    cfg.StrOpt('interval', default='1',
               help=_('number of seconds to wait between packets'))
]
cfg.CONF.register_opts(OPTS, 'vim_keys')
cfg.CONF.register_opts(OPENSTACK_OPTS, 'vim_monitor')

_VALID_RESOURCE_TYPES = {'network': {'client': neutron_client.Client,
                                     'cmd': 'list_networks',
                                     'vim_res_name': 'networks',
                                     'filter_attr': 'name'
                                     }
                         }


CONNECTION_POINT = 'connection_points'


def config_opts():
    return [('vim_keys', OPTS), ('vim_monitor', OPENSTACK_OPTS)]


class Tacker_Driver(abstract_driver.NfvAbstractDriver):
    """Driver for NFV

    OpenStack driver handles interactions with local as well as
    remote OpenStack instances. The driver invokes keystone service for VIM
    authorization and validation. The driver is also responsible for
    discovering placement attributes such as regions, availability zones
    """

    def __init__(self):
        self.keystone = keystone.Keystone()
        self.keystone.create_key_dir(CONF.vim_keys.openstack)

    def get_type(self):
        return 'tacker'

    def get_name(self):
        return 'OpenStack Tacker Driver'

    def get_description(self):
        return 'OpenStack Tacker Driver'

    def nsd_create(self, auth_attr, nsd_dict):
        tacker_client = TackerClient(auth_attr)
        return tacker_client.nsd_create(nsd_dict)

    def nsd_get(self, auth_attr, nsd_name):
        tacker_client = TackerClient(auth_attr)
        return tacker_client.nsd_get(nsd_name)

    def ns_create(self, auth_attr, ns_dict):
        tacker_client = TackerClient(auth_attr)
        return tacker_client.ns_create(ns_dict)

    def ns_get(self, auth_attr, ns_name):
        tacker_client = TackerClient(auth_attr)
        return tacker_client.ns_get(ns_name)

    def ns_delete(self, auth_attr, ns_name):
        tacker_client = TackerClient(auth_attr)
        return tacker_client.ns_delete(ns_name)

    def vnfd_create(self, auth_attr, vnfd_dict):
        tacker_client = TackerClient(auth_attr)
        return tacker_client.vnfd_create(vnfd_dict)

    def vnf_create(self, auth_attr, vnf_dict):
        tacker_client = TackerClient(auth_attr)
        return tacker_client.vnf_create(vnf_dict)

    def vnffgd_get(self, auth_attr, vnffgd_name):
        tacker_client = TackerClient(auth_attr)
        return tacker_client.vnffgd_get(vnffgd_name)

    def vnffg_create(self, auth_attr, vnffg_dict):
        tacker_client = TackerClient(auth_attr)
        return tacker_client.vnffg_create(vnffg_dict)

    def vnffg_get(self, auth_attr, vnffg_name):
        tacker_client = TackerClient(auth_attr)
        return tacker_client.vnffg_get(vnffg_name)

    def vnffg_delete(self, auth_attr, vnffg_name):
        tacker_client = TackerClient(auth_attr)
        return tacker_client.vnffg_delete(vnffg_name)


class TackerClient(object):
    """Tacker Client class for VNFM and NFVO negotiation"""

    def __init__(self, auth_attr):
        auth = identity.Password(**auth_attr)
        sess = session.Session(auth=auth)
        self.client = tacker_client.Client(session=sess)

    def nsd_create(self, nsd_dict):
        nsd_instance = self.client.create_nsd(body=nsd_dict)
        if nsd_instance:
            return nsd_instance['nsd']['id']
        else:
            return None

    def nsd_get(self, nsd_name):
        nsd_dict = self.client.list_nsds()
        nsd_list = nsd_dict['nsds']
        nsd_id = None
        for nsd in nsd_list:
            if nsd['name'] == nsd_name:
                nsd_id = nsd['id']
        return nsd_id

    def ns_create(self, ns_dict):
        ns_instance = self.client.create_ns(body=ns_dict)
        if ns_instance:
            return ns_instance['ns']['id']
        else:
            return None

    def ns_get(self, ns_name):
        ns_dict = self.client.list_nsds()
        ns_list = ns_dict['nss']
        ns_id = None
        for ns in ns_list:
            if ns['name'] == ns_name:
                ns_id = ns['id']
        return ns_id

    def ns_delete(self, ns_name):
        nsd_id = self.ns_get(ns_name)
        if nsd_id:
            self.client.delete_ns(nsd_id)

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

    def vnffgd_get(self, vnffgd_name):
        vnffgd_dict = self.client.list_vnffgds()
        vnffgd_list = vnffgd_dict['vnffgds']
        vnffgd_id = None
        for vnffgd in vnffgd_list:
            if vnffgd['name'] == vnffgd_name:
                vnffgd_id = vnffgd['id']
        return vnffgd_id

    def vnffg_create(self, vnffgd_dict):
        vnffg_instance = self.client.create_vnffg(body=vnffgd_dict)
        if vnffg_instance:
            return vnffg_instance['vnffg']['id']
        else:
            return None

    def vnffg_get(self, vnffg_name):
        vnffg_dict = self.client.list_vnffgs()
        vnffg_list = vnffg_dict['vnffgs']
        vnffg_id = None
        for vnffg in vnffg_list:
            if vnffg['name'] == vnffg_name:
                vnffg_id = vnffg['id']
        return vnffg_id

    def vnffg_delete(self, vnffg_name):
        vnffg_id = self.vnffg_get(vnffg_name)
        if vnffg_id:
            self.client.delete_vnffg(vnffg_id)