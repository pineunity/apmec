# Copyright 2016 Brocade Communications System, Inc.
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

import yaml

from oslo_config import cfg
from apmecclient.common import exceptions

from apmec.plugins.common import constants as evt_constants
from apmec.tests import constants
from apmec.tests.functional import base
from apmec.tests.utils import read_file

import time
CONF = cfg.CONF


class NsdTestCreate(base.BaseTackerTest):
    def _test_create_tosca_mead(self, tosca_mead_file, mead_name):
        input_yaml = read_file(tosca_mead_file)
        tosca_dict = yaml.safe_load(input_yaml)
        tosca_arg = {'mead': {'name': mead_name,
                              'attributes': {'mead': tosca_dict}}}
        mead_instance = self.client.create_mead(body=tosca_arg)
        self.assertEqual(mead_instance['mead']['name'], mead_name)
        self.assertIsNotNone(mead_instance)

        meads = self.client.list_meads().get('meads')
        self.assertIsNotNone(meads, "List of meads are Empty after Creation")
        return mead_instance['mead']['id']

    def _test_create_nsd(self, tosca_nsd_file, nsd_name):
        input_yaml = read_file(tosca_nsd_file)
        tosca_dict = yaml.safe_load(input_yaml)
        tosca_arg = {'nsd': {'name': nsd_name,
                             'attributes': {'nsd': tosca_dict}}}
        nsd_instance = self.client.create_nsd(body=tosca_arg)
        self.assertIsNotNone(nsd_instance)
        return nsd_instance['nsd']['id']

    def _test_delete_nsd(self, nsd_id):
        try:
            self.client.delete_nsd(nsd_id)
        except Exception:
                assert False, "nsd Delete failed"

    def _test_delete_mead(self, mead_id, timeout=constants.NS_DELETE_TIMEOUT):
        start_time = int(time.time())
        while True:
            try:
                self.client.delete_mead(mead_id)
            except exceptions.Conflict:
                time.sleep(2)
            except Exception:
                assert False, "mead Delete failed"
            else:
                break
            if (int(time.time()) - start_time) > timeout:
                assert False, "mead still in use"
        self.verify_mead_events(mead_id, evt_constants.RES_EVT_DELETE,
                                evt_constants.RES_EVT_NA_STATE)

    def _wait_until_ns_status(self, ns_id, target_status, timeout,
                              sleep_interval):
        start_time = int(time.time())
        while True:
                ns_result = self.client.show_ns(ns_id)
                status = ns_result['ns']['status']
                if (status == target_status) or (
                        (int(time.time()) - start_time) > timeout):
                    break
                time.sleep(sleep_interval)

        self.assertEqual(status, target_status,
                         "ns %(ns_id)s with status %(status)s is"
                         " expected to be %(target)s" %
                         {"ns_id": ns_id, "status": status,
                          "target": target_status})

    def _wait_until_ns_delete(self, ns_id, timeout):
        start_time = int(time.time())
        while True:
            try:
                ns_result = self.client.show_ns(ns_id)
                time.sleep(2)
            except Exception:
                return
            status = ns_result['ns']['status']
            if (status != 'PENDING_DELETE') or ((
                    int(time.time()) - start_time) > timeout):
                raise Exception("Failed with status: %s" % status)

    def _test_create_delete_ns(self, nsd_file, ns_name,
                               template_source='onboarded'):
        mead1_id = self._test_create_tosca_mead(
            'test-ns-mead1.yaml',
            'test-ns-mead1')
        mead2_id = self._test_create_tosca_mead(
            'test-ns-mead2.yaml',
            'test-ns-mead2')

        if template_source == 'onboarded':
            nsd_id = self._test_create_nsd(
                nsd_file,
                'test-ns-nsd')
            ns_arg = {'ns': {
                'nsd_id': nsd_id,
                'name': ns_name,
                'attributes': {"param_values": {
                    "nsd": {
                        "vl2_name": "net0",
                        "vl1_name": "net_mgmt"}}}}}
            ns_instance = self.client.create_ns(body=ns_arg)
            ns_id = ns_instance['ns']['id']

        if template_source == 'inline':
            input_yaml = read_file(nsd_file)
            template = yaml.safe_load(input_yaml)
            ns_arg = {'ns': {
                'name': ns_name,
                'attributes': {"param_values": {
                    "nsd": {
                        "vl2_name": "net0",
                        "vl1_name": "net_mgmt"}}},
                'nsd_template': template}}
            ns_instance = self.client.create_ns(body=ns_arg)
            ns_id = ns_instance['ns']['id']

        self._wait_until_ns_status(ns_id, 'ACTIVE',
                                   constants.NS_CREATE_TIMEOUT,
                                   constants.ACTIVE_SLEEP_TIME)
        ns_show_out = self.client.show_ns(ns_id)['ns']
        self.assertIsNotNone(ns_show_out['mgmt_urls'])

        try:
            self.client.delete_ns(ns_id)
        except Exception as e:
            print("Exception:", e)
            assert False, "ns Delete failed"
        if template_source == 'onboarded':
            self._wait_until_ns_delete(ns_id, constants.NS_DELETE_TIMEOUT)
            self._test_delete_nsd(nsd_id)
        self._test_delete_mead(mead1_id)
        self._test_delete_mead(mead2_id)

    def test_create_delete_nsd(self):
        mead1_id = self._test_create_tosca_mead(
            'test-nsd-mead1.yaml',
            'test-nsd-mead1')
        mead2_id = self._test_create_tosca_mead(
            'test-nsd-mead2.yaml',
            'test-nsd-mead2')
        nsd_id = self._test_create_nsd(
            'test-nsd.yaml',
            'test-nsd')
        self._test_delete_nsd(nsd_id)
        self._test_delete_mead(mead1_id)
        self._test_delete_mead(mead2_id)

    def test_create_delete_network_service(self):
        self._test_create_delete_ns('test-ns-nsd.yaml',
                                    'test-ns-onboarded',
                                    template_source='onboarded')
        time.sleep(1)
        self._test_create_delete_ns('test-ns-nsd.yaml',
                                    'test-ns-inline',
                                    template_source='inline')
