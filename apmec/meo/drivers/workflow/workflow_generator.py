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

import ast
from oslo_utils import uuidutils

from apmec.mistral import workflow_generator


OUTPUT = {
    'create_mea': ['mea_id', 'vim_id', 'mgmt_url', 'status']
}


class WorkflowGenerator(workflow_generator.WorkflowGeneratorBase):

    def _add_create_mea_tasks(self, meca):
        meads = meca['mead_details']
        task_dict = dict()
        for mead_name, mead_info in (meads).items():
            nodes = mead_info['instances']
            for node in nodes:
                task = self.wf_name + '_' + node
                task_dict[task] = {
                    'action': 'apmec.create_mea body=<% $.mea.{0} '
                              '%>'.format(node),
                    'input': {'body': '<% $.mea.{0} %>'.format(node)},
                    'publish': {
                        'mea_id_' + node: '<% task({0}).result.mea.id '
                                          '%>'.format(task),
                        'vim_id_' + node: '<% task({0}).result.mea.vim_id'
                                          ' %>'.format(task),
                        'mgmt_url_' + node: '<% task({0}).result.mea.mgmt_url'
                                            ' %>'.format(task),
                        'status_' + node: '<% task({0}).result.mea.status'
                                          ' %>'.format(task),
                              },
                    'on-success': ['wait_mea_active_%s' % node]
                }
        return task_dict

    def _add_wait_mea_tasks(self, meca):
        meads = meca['mead_details']
        task_dict = dict()
        for mead_name, mead_info in (meads).items():
            nodes = mead_info['instances']
            for node in nodes:
                task = 'wait_mea_active_%s' % node
                task_dict[task] = {
                    'action': 'apmec.show_mea mea=<% $.mea_id_{0} '
                              '%>'.format(node),
                    'retry': {
                        'count': 10,
                        'delay': 10,
                        'break-on': '<% $.status_{0} = "ACTIVE" '
                                    '%>'.format(node),
                        'break-on': '<% $.status_{0} = "ERROR"'
                                    ' %>'.format(node),
                        'continue-on': '<% $.status_{0} = "PENDING_CREATE" '
                                       '%>'.format(node),
                              },
                    'publish': {
                        'mgmt_url_' + node: ' <% task({0}).result.mea.'
                                            'mgmt_url %>'.format(task),
                        'status_' + node: '<% task({0}).result.mea.status'
                                          ' %>'.format(task),
                              },
                    'on-success': [
                        {'delete_mea_' + node: '<% $.status_{0}='
                                               '"ERROR" %>'.format(node)}
                              ]
                }
        return task_dict

    def _add_delete_mea_tasks(self, meca):
        meads = meca['mead_details']
        task_dict = dict()
        for mead_name, mead_info in (meads).items():
            # mead_info is a list of mead_id
            nodes = mead_info['instances']
            for node in nodes:
                task = 'delete_mea_%s' % node
                task_dict[task] = {
                    'action': 'apmec.delete_mea mea=<% $.mea_id_{0}'
                              '%>'.format(node),
                }
        return task_dict

    def _build_output_dict(self, meca):
        meads = meca['mead_details']
        task_dict = dict()
        for mead_name, mead_info in (meads).items():
            nodes = mead_info['instances']
            for node in nodes:
                for op_name in OUTPUT[self.wf_name]:
                    task_dict[op_name + '_' + node] = \
                        '<% $.{0}_{1} %>'.format(op_name, node)
        return task_dict

    def get_input_dict(self):
        return self.input_dict

    def build_input(self, meca, params):
        meads = meca['mead_details']
        id = uuidutils.generate_uuid()
        self.input_dict = {'mea': {}}
        for mead_name, mead_info in (meads).items():
            nodes = mead_info['instances']
            for node in nodes:
                self.input_dict['mea'][node] = dict()
                self.input_dict['mea'][node]['mea'] = {
                    'attributes': {},
                    'vim_id': meca['meca'].get('vim_id', ''),
                    'mead_id': mead_info['id'],
                    'name': 'create_mea_%s_%s' % (mead_info['id'], id)
                }
                if params.get(mead_name):
                    self.input_dict['mea'][node]['mea']['attributes'] = {
                        'param_values': params.get(mead_name)
                    }

    def create_mea(self, **kwargs):
        meca = kwargs.get('meca')
        params = kwargs.get('params')
        # TODO(anyone): Keep this statements in a loop and
        # remove in all the methods.
        self.definition[self.wf_identifier]['tasks'] = dict()
        self.definition[self.wf_identifier]['tasks'].update(
            self._add_create_mea_tasks(meca))
        self.definition[self.wf_identifier]['tasks'].update(
            self._add_wait_mea_tasks(meca))
        self.definition[self.wf_identifier]['tasks'].update(
            self._add_delete_mea_tasks(meca))
        self.definition[self.wf_identifier]['output'] = \
            self._build_output_dict(meca)
        self.build_input(meca, params)

    def delete_mea(self, meca):
        meca_dict = {'mead_details': {}}
        mea_ids = ast.literal_eval(meca['mea_ids'])
        self.definition[self.wf_identifier]['input'] = []
        for mea in mea_ids.keys():
            mea_key = 'mea_id_' + mea
            meca_dict['mead_details'][mea] = dict()
            instances_dict = dict()
            instances_dict['instances'] = list()
            for index, mea_id in enumerate(mea_ids[mea]):
                mea_key_cp = mea_key + str(index)
                self.definition[self.wf_identifier]['input'].append(mea_key_cp)
                mea_name = mea + str(index)
                self.input_dict[mea_key_cp] = mea_id
                instances_dict['instances'].append(mea_name)
            meca_dict['mead_details'][mea].update(instances_dict)
        self.definition[self.wf_identifier]['tasks'] = dict()
        self.definition[self.wf_identifier]['tasks'].update(
            self._add_delete_mea_tasks(meca_dict))
