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
import time
from tempfile import mkstemp

import eventlet
import yaml
from oslo_config import cfg
from oslo_log import log as logging
from toscaparser import tosca_template
from toscaparser.tosca_template import ToscaTemplate

from apmec import manager
from apmec._i18n import _
from apmec.catalogs.tosca import utils as toscautils
from apmec.common import driver_manager
from apmec.common import log
from apmec.common import utils
from apmec.db.meso import meso_db
from apmec.extensions import common_services as cs
from apmec.extensions import meso
from apmec.mem import vim_client

LOG = logging.getLogger(__name__)
CONF = cfg.CONF
MISTRAL_RETRIES = 30
MISTRAL_RETRY_WAIT = 6


def config_opts():
    return [('meso', MesoPlugin.OPTS)]


class MesoPlugin(meso_db.MESOPluginDb):
    """MESO reference plugin for MESO extension

    Implements the MESO extension and defines public facing APIs for VIM
    operations. MESO internally invokes the appropriate VIM driver in
    backend based on configured VIM types. Plugin also interacts with MEM
    extension for providing the specified VIM information
    """
    supported_extension_aliases = ['meso']

    OPTS = [
        cfg.ListOpt(
            'nfv_drivers', default=['tacker'],
            help=_('NFV drivers for launching NSs')),
    ]
    cfg.CONF.register_opts(OPTS, 'meso')

    def __init__(self):
        super(MesoPlugin, self).__init__()
        self._pool = eventlet.GreenPool()
        self._mano_drivers = driver_manager.DriverManager(
            'apmec.meso.drivers',
            cfg.CONF.meso.nfv_drivers)

    def get_auth_dict(self, context):
        auth = CONF.keystone_authtoken
        return {
            'auth_url': auth.auth_url + '/v3',
            'token': context.auth_token,
            'project_domain_name': auth.project_domain_name or context.domain,
            'project_name': context.tenant_name
        }

    def spawn_n(self, function, *args, **kwargs):
        self._pool.spawn_n(function, *args, **kwargs)

    def _build_vim_auth(self, context, vim_info):
        LOG.debug('VIM id is %s', vim_info['id'])
        vim_auth = vim_info['auth_cred']
        vim_auth['password'] = self._decode_vim_auth(context,
                                                     vim_info['id'],
                                                     vim_auth)
        vim_auth['auth_url'] = vim_info['auth_url']

        # These attributes are needless for authentication
        # from keystone, so we remove them.
        needless_attrs = ['key_type', 'secret_uuid']
        for attr in needless_attrs:
            if attr in vim_auth:
                vim_auth.pop(attr, None)
        return vim_auth

    @log.log
    def create_mesd(self, context, mesd):
        mesd_data = mesd['mesd']
        template = mesd_data['attributes'].get('mesd')
        if isinstance(template, dict):
            mesd_data['attributes']['mesd'] = yaml.safe_dump(
                template)
        LOG.debug('mesd %s', mesd_data)

        if 'template_source' in mesd_data:
            template_source = mesd_data.get('template_source')
        else:
            template_source = "onboarded"
        mesd['mesd']['template_source'] = template_source

        self._parse_template_input(context, mesd)
        return super(MesoPlugin, self).create_mesd(
            context, mesd)

    def _parse_template_input(self, context, mesd):
        mesd_dict = mesd['mesd']
        mesd_yaml = mesd_dict['attributes'].get('mesd')
        inner_mesd_dict = yaml.safe_load(mesd_yaml)
        mesd['meads'] = dict()
        LOG.debug('mesd_dict: %s', inner_mesd_dict)
        # From import we can deploy both NS and MEC Application
        nsd_imports = inner_mesd_dict['imports'].get('nsds')
        vnffg_imports = inner_mesd_dict['imports'].get('vnffgds')
        if nsd_imports:
            mesd_dict['attributes']['nsds'] = '-'.join(nsd_imports)
        if vnffg_imports:
            mesd_dict['attributes']['vnffgds'] = '-'.join(vnffg_imports)

        # Deploy MEC applications
        mem_plugin = manager.ApmecManager.get_service_plugins()['MEM']
        mead_imports = inner_mesd_dict['imports']['meads']
        inner_mesd_dict['imports'] = []
        new_files = []
        for mead_name in mead_imports:
            mead = mem_plugin.get_mead(context, mead_name)
            # Copy MEA types and MEA names
            sm_dict = yaml.safe_load(mead['attributes']['mead'])[
                'topology_template'][
                'substitution_mappings']
            mesd['meads'][sm_dict['node_type']] = mead['name']
            # Ugly Hack to validate the child templates
            # TODO(tbh): add support in tosca-parser to pass child
            # templates as dict
            fd, temp_path = mkstemp()
            with open(temp_path, 'w') as fp:
                fp.write(mead['attributes']['mead'])
            os.close(fd)
            new_files.append(temp_path)
            inner_mesd_dict['imports'].append(temp_path)
        # Prepend the apmec_defs.yaml import file with the full
        # path to the file
        toscautils.updateimports(inner_mesd_dict)

        try:
            ToscaTemplate(a_file=False,
                          yaml_dict_tpl=inner_mesd_dict)
        except Exception as e:
            LOG.exception("tosca-parser error: %s", str(e))
            raise meso.ToscaParserFailed(error_msg_details=str(e))
        finally:
            for file_path in new_files:
                os.remove(file_path)
            inner_mesd_dict['imports'] = mead_imports

        if ('description' not in mesd_dict or
                mesd_dict['description'] == ''):
            mesd_dict['description'] = inner_mesd_dict.get(
                'description', '')
        if (('name' not in mesd_dict or
                not len(mesd_dict['name'])) and
                'metadata' in inner_mesd_dict):
            mesd_dict['name'] = inner_mesd_dict['metadata'].get(
                'template_name', '')

        LOG.debug('mesd %s', mesd)

    def _get_mead_id(self, mead_name, onboarded_meads):
        for mead in onboarded_meads:
            if mead_name == mead['name']:
                return mead['id']

    @log.log
    def create_mes(self, context, mes):
        """Create MES and corresponding MEAs.

        :param mes: mes dict which contains mesd_id and attributes
        This method has 3 steps:
        step-1: substitute all get_input params to its corresponding values
        step-2: Build params dict for substitution mappings case through which
        MEAs will actually substitute their requirements.
        step-3: Create mistral workflow and execute the workflow
        """
        mes_info = mes['mes']
        name = mes_info['name']

        if mes_info.get('mesd_template'):
            mesd_name = utils.generate_resource_name(name, 'inline')
            mesd = {'mesd': {
                'attributes': {'mesd': mes_info['mesd_template']},
                'description': mes_info['description'],
                'name': mesd_name,
                'template_source': 'inline',
                'tenant_id': mes_info['tenant_id']}}
            mes_info['mesd_id'] = self.create_mesd(context, mesd).get('id')

        mesd = self.get_mesd(context, mes['mes']['mesd_id'])
        mesd_dict = yaml.safe_load(mesd['attributes']['mesd'])
        mem_plugin = manager.ApmecManager.get_service_plugins()['MEM']
        onboarded_meads = mem_plugin.get_meads(context, [])
        region_name = mes.setdefault('placement_attr', {}).get(
            'region_name', None)
        vim_res = self.vim_client.get_vim(context, mes['mes']['vim_id'],
                                          region_name)
        driver_type = vim_res['vim_type']
        if not mes['mes']['vim_id']:
            mes['mes']['vim_id'] = vim_res['vim_id']

        nsds = mesd['attributes'].get('nsds')
        if nsds:
          nsds_list = nsds.split('-')
          for nsd in nsds_list:
            vim_obj = self.get_vim(context, mes['mes']['vim_id'], mask_password=False)
            self._build_vim_auth(context, vim_obj)
            client = self.tackerclient(vim_obj['auth_cred'])
            ns_name = nsd + name
            nsd_instance = client.nsd_get(nsd)
            ns_arg = {'ns': {'nsd_id': nsd_instance, 'name': ns_name}}
            ns_instance = client.ns_create(ns_arg)

            # Call tacker client driver

        vnffgds = mesd['attributes'].get('vnffgds')
        if vnffgds:
          vnffgds_list = vnffgds.split('-')
          for vnffgd in vnffgds_list:
            vim_obj = self.get_vim(context, mes['mes']['vim_id'], mask_password=False)
            self._build_vim_auth(context, vim_obj)
            client = self.tackerclient(vim_obj['auth_cred'])
            vnffg_name = vnffgds + name
            vnffgd_instance = client.vnffgd_get(vnffgd)
            vnffg_arg = {'vnffg': {'vnffgd_id': vnffgd_instance, 'name': vnffg_name}}
            vnffg_instance = client.vnffg_create(vnffg_arg)
            # Call Tacker client driver

        # Step-1
        param_values = mes['mes']['attributes'].get('param_values', {})
        if 'get_input' in str(mesd_dict):
            self._process_parameterized_input(mes['mes']['attributes'],
                                              mesd_dict)
        # Step-2
        meads = mesd['meads']
        # mead_dict is used while generating workflow
        mead_dict = dict()
        for node_name, node_val in \
                (mesd_dict['topology_template']['node_templates']).items():
            if node_val.get('type') not in meads.keys():
                continue
            mead_name = meads[node_val.get('type')]
            if not mead_dict.get(mead_name):
                mead_dict[mead_name] = {
                    'id': self._get_mead_id(mead_name, onboarded_meads),
                    'instances': [node_name]
                }
            else:
                mead_dict[mead_name]['instances'].append(node_name)
            if not node_val.get('requirements'):
                continue
            if not param_values.get(mead_name):
                param_values[mead_name] = {}
            param_values[mead_name]['substitution_mappings'] = dict()
            req_dict = dict()
            requirements = node_val.get('requirements')
            for requirement in requirements:
                req_name = list(requirement.keys())[0]
                req_val = list(requirement.values())[0]
                res_name = req_val + mes['mes']['mesd_id'][:11]
                req_dict[req_name] = res_name
                if req_val in mesd_dict['topology_template']['node_templates']:
                    param_values[mead_name]['substitution_mappings'][
                        res_name] = mesd_dict['topology_template'][
                            'node_templates'][req_val]

            param_values[mead_name]['substitution_mappings'][
                'requirements'] = req_dict
        mes['mead_details'] = mead_dict
        # Step-3
        kwargs = {'mes': mes, 'params': param_values}

        # NOTE NoTasksException is raised if no tasks.
        workflow = self._vim_drivers.invoke(
            driver_type,
            'prepare_and_create_workflow',
            resource='mea',
            action='create',
            auth_dict=self.get_auth_dict(context),
            kwargs=kwargs)
        try:
            mistral_execution = self._vim_drivers.invoke(
                driver_type,
                'execute_workflow',
                workflow=workflow,
                auth_dict=self.get_auth_dict(context))
        except Exception as ex:
            LOG.error('Error while executing workflow: %s', ex)
            self._vim_drivers.invoke(driver_type,
                                     'delete_workflow',
                                     workflow_id=workflow['id'],
                                     auth_dict=self.get_auth_dict(context))
            raise ex
        mes_dict = super(MesoPlugin, self).create_mes(context, mes)

        def _create_mes_wait(self_obj, mes_id, execution_id):
            exec_state = "RUNNING"
            mistral_retries = MISTRAL_RETRIES
            while exec_state == "RUNNING" and mistral_retries > 0:
                time.sleep(MISTRAL_RETRY_WAIT)
                exec_state = self._vim_drivers.invoke(
                    driver_type,
                    'get_execution',
                    execution_id=execution_id,
                    auth_dict=self.get_auth_dict(context)).state
                LOG.debug('status: %s', exec_state)
                if exec_state == 'SUCCESS' or exec_state == 'ERROR':
                    break
                mistral_retries = mistral_retries - 1
            error_reason = None
            if mistral_retries == 0 and exec_state == 'RUNNING':
                error_reason = _(
                    "MES creation is not completed within"
                    " {wait} seconds as creation of mistral"
                    " execution {mistral} is not completed").format(
                    wait=MISTRAL_RETRIES * MISTRAL_RETRY_WAIT,
                    mistral=execution_id)
            exec_obj = self._vim_drivers.invoke(
                driver_type,
                'get_execution',
                execution_id=execution_id,
                auth_dict=self.get_auth_dict(context))
            self._vim_drivers.invoke(driver_type,
                                     'delete_execution',
                                     execution_id=execution_id,
                                     auth_dict=self.get_auth_dict(context))
            self._vim_drivers.invoke(driver_type,
                                     'delete_workflow',
                                     workflow_id=workflow['id'],
                                     auth_dict=self.get_auth_dict(context))
            super(MesoPlugin, self).create_mes_post(context, mes_id, exec_obj,
                                                   mead_dict, error_reason)

        self.spawn_n(_create_mes_wait, self, mes_dict['id'],
                     mistral_execution.id)
        return mes_dict

    @log.log
    def _update_params(self, original, paramvalues):
        for key, value in (original).items():
            if not isinstance(value, dict) or 'get_input' not in str(value):
                pass
            elif isinstance(value, dict):
                if 'get_input' in value:
                    if value['get_input'] in paramvalues:
                        original[key] = paramvalues[value['get_input']]
                    else:
                        LOG.debug('Key missing Value: %s', key)
                        raise cs.InputValuesMissing(key=key)
                else:
                    self._update_params(value, paramvalues)

    @log.log
    def _process_parameterized_input(self, attrs, mesd_dict):
        param_vattrs_dict = attrs.pop('param_values', None)
        if param_vattrs_dict:
            for node in \
                    mesd_dict['topology_template']['node_templates'].values():
                if 'get_input' in str(node):
                    self._update_params(node, param_vattrs_dict['mesd'])
        else:
            raise cs.ParamYAMLInputMissing()

    @log.log
    def delete_mes(self, context, mes_id):
        mes = super(MesoPlugin, self).get_mes(context, mes_id)
        vim_res = self.vim_client.get_vim(context, mes['vim_id'])
        driver_type = vim_res['vim_type']
        workflow = None
        try:
            workflow = self._vim_drivers.invoke(
                driver_type,
                'prepare_and_create_workflow',
                resource='mea',
                action='delete',
                auth_dict=self.get_auth_dict(context),
                kwargs={
                    'mes': mes})
        except meso.NoTasksException:
            LOG.warning("No MEA deletion task(s).")
        if workflow:
            try:
                mistral_execution = self._vim_drivers.invoke(
                    driver_type,
                    'execute_workflow',
                    workflow=workflow,
                    auth_dict=self.get_auth_dict(context))

            except Exception as ex:
                LOG.error('Error while executing workflow: %s', ex)
                self._vim_drivers.invoke(driver_type,
                                         'delete_workflow',
                                         workflow_id=workflow['id'],
                                         auth_dict=self.get_auth_dict(context))

                raise ex
        super(MesoPlugin, self).delete_mes(context, mes_id)

        def _delete_mes_wait(mes_id, execution_id):
            exec_state = "RUNNING"
            mistral_retries = MISTRAL_RETRIES
            while exec_state == "RUNNING" and mistral_retries > 0:
                time.sleep(MISTRAL_RETRY_WAIT)
                exec_state = self._vim_drivers.invoke(
                    driver_type,
                    'get_execution',
                    execution_id=execution_id,
                    auth_dict=self.get_auth_dict(context)).state
                LOG.debug('status: %s', exec_state)
                if exec_state == 'SUCCESS' or exec_state == 'ERROR':
                    break
                mistral_retries -= 1
            error_reason = None
            if mistral_retries == 0 and exec_state == 'RUNNING':
                error_reason = _(
                    "MES deletion is not completed within"
                    " {wait} seconds as deletion of mistral"
                    " execution {mistral} is not completed").format(
                    wait=MISTRAL_RETRIES * MISTRAL_RETRY_WAIT,
                    mistral=execution_id)
            exec_obj = self._vim_drivers.invoke(
                driver_type,
                'get_execution',
                execution_id=execution_id,
                auth_dict=self.get_auth_dict(context))
            self._vim_drivers.invoke(driver_type,
                                     'delete_execution',
                                     execution_id=execution_id,
                                     auth_dict=self.get_auth_dict(context))
            self._vim_drivers.invoke(driver_type,
                                     'delete_workflow',
                                     workflow_id=workflow['id'],
                                     auth_dict=self.get_auth_dict(context))
            super(MesoPlugin, self).delete_mes_post(context, mes_id, exec_obj,
                                                   error_reason)
        if workflow:
            self.spawn_n(_delete_mes_wait, mes['id'], mistral_execution.id)
        else:
            super(MesoPlugin, self).delete_mes_post(
                context, mes_id, None, None)
        return mes['id']