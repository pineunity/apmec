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

import time

import eventlet
import yaml
from oslo_config import cfg
from oslo_log import log as logging


from apmec import manager
from apmec._i18n import _
from apmec.common import driver_manager
from apmec.common import log
from apmec.common import utils
from apmec.db.meso import meso_db
from apmec.extensions import common_services as cs
from apmec.extensions import meso
from apmec.plugins.common import constants
from apmec.mem import vim_client



LOG = logging.getLogger(__name__)
CONF = cfg.CONF
NS_RETRIES = 30
NS_RETRY_WAIT = 6
MEC_RETRIES = 30
MEC_RETRY_WAIT = 6
VNFFG_RETRIES = 30
VNFFG_RETRY_WAIT = 6


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
        self._nfv_drivers = driver_manager.DriverManager(
            'apmec.meso.drivers',
            cfg.CONF.meso.nfv_drivers)
        self.vim_client = vim_client.VimClient()

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
        mesd_dict['mesd_mapping'] = dict()
        LOG.debug('mesd_dict: %s', inner_mesd_dict)
        # From import we can deploy both NS and MEC Application
        nsd_imports = inner_mesd_dict['imports'].get('nsds')
        vnffg_imports = inner_mesd_dict['imports'].get('vnffgds')
        if nsd_imports:
            nsd_tpls = nsd_imports.get('nsd_templates')
            nfv_driver = nsd_imports.get('nfv_driver')
            if not nsd_tpls:
                raise meso.NSDNotFound(mesd_name=mesd_dict['name'])
            if nfv_driver.lower() not in [driver.lower() for driver in constants.NFV_DRIVER]:
                raise meso.NFVDriverNotFound(mesd_name=mesd_dict['name'])
            mesd_dict['attributes']['nsds'] = '-'.join(nsd_tpls)
            mesd_dict['mesd_mapping']['NSD'] = nsd_tpls
        if vnffg_imports:
            vnffgd_tpls = vnffg_imports.get('vnffgd_templates')
            nfv_driver = vnffg_imports.get('nfv_driver')
            if not vnffgd_tpls:
                raise meso.VNFFGDNotFound(mesd_name=mesd_dict['name'])
            mesd_dict['mesd_mapping'] = vnffgd_tpls
            mesd_dict['attributes']['vnffgds'] = '-'.join(vnffgd_tpls)
            if nfv_driver.lower() not in [driver.lower() for driver in constants.NFV_DRIVER]:
                raise meso.NFVDriverNotFound(mesd_name=mesd_dict['name'])

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
        This method has 2 steps:
        step-1: Call MEO API to create MEAs
        step-2: Call Tacker drivers to create NSs
        """
        mes_info = mes['mes']
        name = mes_info['name']
        mes_info['mes_mapping'] = dict()

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
        meo_plugin = manager.ApmecManager.get_service_plugins()['MEO']
        meca_id = dict()
        # Create MEAs using MEO APIs
        try:
            meca_name = 'meca' + name
            meca_arg = {'meca': {'mecad_template': mesd['attributes']['mesd'], 'name': meca_name}}
            meca_dict = meo_plugin.create_meca(context, meca_arg)
            mes_info['mes_mapping']['MECA'] = meca_dict['id']
        except Exception as e:
            LOG.error('Error while creating the MEAs: %s', e)
        region_name = mes.setdefault('placement_attr', {}).get(
            'region_name', None)
        vim_res = self.vim_client.get_vim(context, mes['mes']['vim_id'],
                                          region_name)
        driver_type = vim_res['vim_type']
        if not mes['mes']['vim_id']:
            mes['mes']['vim_id'] = vim_res['vim_id']

        ##########################################
        # Detect MANO driver here:
        # Defined in the Tosca template
        nfv_dirver = None
        if mesd_dict['imports'].get('nsds'):
            nfv_dirver = mesd_dict['import']['nsds']['nfv_driver']
            nfv_dirver = nfv_dirver.lower()
        if mesd_dict['imports'].get('nsds'):
            nfv_dirver = mesd_dict['import']['vnffgds']['nfv_driver']
            nfv_dirver = nfv_dirver.lower()

        ##########################################
        vim_obj = self.get_vim(context, mes['mes']['vim_id'], mask_password=False)
        self._build_vim_auth(context, vim_obj)
        nsds = mesd['attributes'].get('nsds')
        if nsds:
          nsds_list = nsds.split('-')
          mes_info['mes_mapping']['NS'] = list()
          for nsd in nsds_list:
            ns_name = nsd + name
            nsd_instance = self._nfv_drivers.invoke(
                nfv_dirver, # How to tell it is Tacker
                'nsd_get',
                nsd_name=nsd,
                auth_attr=vim_obj['auth_cred'],)
            if nsd_instance:
                ns_arg = {'ns': {'nsd_id': nsd_instance, 'name': ns_name}}
                ns_instance = self._nfv_drivers.invoke(
                    nfv_dirver,  # How to tell it is Tacker
                    'ns_create',
                    ns_dict=ns_arg,
                    auth_attr=vim_obj['auth_cred'], )
                mes_info['mes_mapping']['NS'].append(ns_instance['ns']['id'])
            # Call tacker client driver

        vnffgds = mesd['attributes'].get('vnffgds')
        if vnffgds:
          vnffgds_list = vnffgds.split('-')
          mes_info['mes_mapping']['VNFFG'] = list()
          for vnffgd in vnffgds_list:
            vnffg_name = vnffgds + name
            vnffgd_instance = self._nfv_drivers.invoke(
                nfv_dirver,  # How to tell it is Tacker
                'vnffgd_get',
                nsd_name=vnffgd,
                auth_attr=vim_obj['auth_cred'], )
            if vnffgd_instance:
                vnffg_arg = {'vnffg': {'vnffgd_id': vnffgd_instance, 'name': vnffg_name}}
                vnffg_instance = self._nfv_drivers.invoke(
                    nfv_dirver,  # How to tell it is Tacker
                    'vnffg_create',
                    vnffg_dict=vnffg_arg,
                    auth_attr=vim_obj['auth_cred'], )
                mes_info['mes_mapping']['VNFFG'].append(vnffg_instance['vnffg']['id'])
            # Call Tacker client driver

        mes_dict = super(MesoPlugin, self).create_mes(context, mes)

        def _create_mes_wait(self_obj, mes_id):
            mes_status = "ACTIVE"
            ns_status = "ACTIVE"
            vnffg_status = "ACTIVE"
            mec_status = "ACTIVE"
            ns_retries = NS_RETRIES
            mec_retries = MEC_RETRIES
            vnffg_retries = VNFFG_RETRIES
            mes_mapping = self.get_mes(context, mes_id)['mes_mapping']
            # Check MECA
            while mec_status == "ACTIVE" and mec_retries > 0:
                time.sleep(MEC_RETRY_WAIT)
                meca_id = mes_mapping['MECA']
                mec_status = meo_plugin.get_meca(context, meca_id)['status']
                LOG.debug('status: %s', mec_status)
                if mec_status == 'ACTIVE' or mec_status == 'ERROR':
                    break
                mec_retries = mec_retries - 1
            error_reason = None
            if mec_retries == 0 and mec_status == 'PENDING_CREATE':
                error_reason = _(
                    "MES creation is not completed within"
                    " {wait} seconds as creation of MECA").format(
                    wait=MEC_RETRIES * MEC_RETRY_WAIT)
            # Check NS/VNFFG status
            if mes_mapping.get('NS'):
                while ns_status == "ACTIVE" and ns_retries > 0:
                    time.sleep(NS_RETRY_WAIT)
                    ns_list = mes_mapping['NS']
                    # Todo: support multiple NSs
                    ns_instance = self._nfv_drivers.invoke(
                        nfv_dirver,  # How to tell it is Tacker
                        'ns_get',
                        ns_id=ns_list[0],
                        auth_attr=vim_obj['auth_cred'], )
                    ns_status = ns_instance['status']
                    LOG.debug('status: %s', ns_status)
                    if ns_status == 'ACTIVE' or ns_status == 'ERROR':
                        break
                    ns_retries = ns_retries - 1
                error_reason = None
                if ns_retries == 0 and ns_status == 'PENDING_CREATE':
                    error_reason = _(
                        "MES creation is not completed within"
                        " {wait} seconds as creation of NS(s)").format(
                        wait=NS_RETRIES * NS_RETRY_WAIT)
            if mes_mapping.get('VNFFG'):
                while vnffg_status == "ACTIVE" and vnffg_retries > 0:
                    time.sleep(VNFFG_RETRY_WAIT)
                    vnffg_list = mes_mapping['VNFFG']
                    # Todo: support multiple VNFFGs
                    vnffg_instance = self._nfv_drivers.invoke(
                        nfv_dirver,  # How to tell it is Tacker
                        'vnffg_get',
                        ns_id=vnffg_list[0],
                        auth_attr=vim_obj['auth_cred'], )
                    vnffg_status = vnffg_instance['status']
                    LOG.debug('status: %s', vnffg_status)
                    if vnffg_status == 'ACTIVE' or vnffg_status == 'ERROR':
                        break
                    vnffg_retries = vnffg_retries - 1
                error_reason = None
                if vnffg_retries == 0 and vnffg_status == 'PENDING_CREATE':
                    error_reason = _(
                        "MES creation is not completed within"
                        " {wait} seconds as creation of VNFFG(s)").format(
                        wait=VNFFG_RETRIES * VNFFG_RETRY_WAIT)
            if mec_status == "ERROR" or ns_status == "ERROR" or vnffg_status == "ERROR":
                mes_status = "ERROR"
            if error_reason:
                mes_status = "PENDING_CREATE"

            super(MesoPlugin, self).create_mes_post(context, mes_id, mes_status, error_reason)
        self.spawn_n(_create_mes_wait, self, mes_dict['id'])
        return mes_dict

    @log.log
    def _get_from_ns(self, context, nsd_id):


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
            exec_state = constants.EXCEC_STATUS
            mistral_retries = MISTRAL_RETRIES
            while exec_state == constants.EXCEC_STATUS and mistral_retries > 0:
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