# Copyright 2016 Brocade Communications System, Inc.
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

from oslo_config import cfg
from toscaparser import tosca_template
import yaml

from apmec.common import utils
from apmec.plugins.common import constants as evt_constants
from apmec.tests import constants
from apmec.tests.functional import base
from apmec.tests.utils import read_file
from apmec.catalogs.tosca import utils as toscautils

CONF = cfg.CONF


class MeaTestToscaMultipleVDU(base.BaseApmecTest):
    def test_create_delete_tosca_mea_with_multiple_vdus(self):
        input_yaml = read_file('sample-tosca-mead-multi-vdu.yaml')
        tosca_dict = yaml.safe_load(input_yaml)
        mead_name = 'sample-tosca-mead-multi-vdu'
        tosca_arg = {'mead': {'name': mead_name,
                              'attributes': {'mead': tosca_dict}}}

        # Create mead with tosca template
        mead_instance = self.client.create_mead(body=tosca_arg)
        self.assertIsNotNone(mead_instance)

        # Create mea with mead_id
        mead_id = mead_instance['mead']['id']
        mea_arg = {'mea': {'mead_id': mead_id, 'name':
                           "test_tosca_mea_with_multiple_vdus"}}
        mea_instance = self.client.create_mea(body=mea_arg)

        mea_id = mea_instance['mea']['id']
        self.wait_until_mea_active(mea_id,
                                   constants.MEA_CIRROS_CREATE_TIMEOUT,
                                   constants.ACTIVE_SLEEP_TIME)
        self.assertEqual('ACTIVE',
                         self.client.show_mea(mea_id)['mea']['status'])
        self.validate_mea_instance(mead_instance, mea_instance)

        self.verify_mea_crud_events(
            mea_id, evt_constants.RES_EVT_CREATE,
            evt_constants.PENDING_CREATE, cnt=2)
        self.verify_mea_crud_events(
            mea_id, evt_constants.RES_EVT_CREATE, evt_constants.ACTIVE)

        # Validate mgmt_url with input yaml file
        mgmt_url = self.client.show_mea(mea_id)['mea']['mgmt_url']
        self.assertIsNotNone(mgmt_url)
        mgmt_dict = yaml.safe_load(str(mgmt_url))

        input_dict = yaml.safe_load(input_yaml)
        toscautils.updateimports(input_dict)

        tosca = tosca_template.ToscaTemplate(parsed_params={}, a_file=False,
                          yaml_dict_tpl=input_dict)

        vdus = toscautils.findvdus(tosca)

        self.assertEqual(len(vdus), len(mgmt_dict.keys()))
        for vdu in vdus:
            self.assertIsNotNone(mgmt_dict[vdu.name])
            self.assertEqual(True, utils.is_valid_ipv4(mgmt_dict[vdu.name]))

        # Delete mea_instance with mea_id
        try:
            self.client.delete_mea(mea_id)
        except Exception:
            assert False, "mea Delete of test_mea_with_multiple_vdus failed"

        self.wait_until_mea_delete(mea_id,
                                   constants.MEA_CIRROS_DELETE_TIMEOUT)
        self.verify_mea_crud_events(mea_id, evt_constants.RES_EVT_DELETE,
                                    evt_constants.PENDING_DELETE, cnt=2)

        # Delete mead_instance
        self.addCleanup(self.client.delete_mead, mead_id)
