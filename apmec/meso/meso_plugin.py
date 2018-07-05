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
from oslo_utils import uuidutils
import copy

from oslo_utils import excutils
from oslo_utils import strutils

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
            meca_name = 'meca' + '-' + name + '-' + uuidutils.generate_uuid()
            # Separate the imports out from template
            mead_tpl_dict = dict()
            mead_tpl_dict['imports'] = mesd_dict['imports']['meads']['mead_templates']
            mecad_dict = copy.deepcopy(mesd_dict)
            mecad_dict.pop('imports')
            mecad_dict.update(mead_tpl_dict)
            LOG.debug('mesd %s', mecad_dict)
            meca_arg = {'meca': {'mecad_template': mecad_dict, 'name': meca_name,
                                 'description': mes_info['description'], 'tenant_id': mes_info['tenant_id'],
                                 'vim_id': mes_info['vim_id'], 'attributes': {}}}
            meca_dict = meo_plugin.create_meca(context, meca_arg)
            mes_info['mes_mapping']['MECA'] = meca_dict['id']
        except Exception as e:
            LOG.error('Error while creating the MECAs: %s', e)
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
        nfv_driver = None
        if mesd_dict['imports'].get('nsds'):
            nfv_driver = mesd_dict['imports']['nsds']['nfv_driver']
            nfv_driver = nfv_driver.lower()
        if mesd_dict['imports'].get('vnffgds'):
            nfv_driver = mesd_dict['imports']['vnffgds']['nfv_driver']
            nfv_driver = nfv_driver.lower()

        ##########################################

        # vim_obj = meo_plugin.get_vim(context, mes['mes']['vim_id'], mask_password=False)
        # self._build_vim_auth(context, vim_obj)
        nsds = mesd['attributes'].get('nsds')
        if nsds:
          nsds_list = nsds.split('-')
          mes_info['mes_mapping']['NS'] = list()
          for nsd in nsds_list:
            ns_name = nsd + '-' + name + '-' + uuidutils.generate_uuid()
            nsd_instance = self._nfv_drivers.invoke(
                nfv_driver, # How to tell it is Tacker
                'nsd_get',
                nsd_name=nsd,
                auth_attr=vim_res['vim_auth'],)
            if nsd_instance:
                ns_arg = {'ns': {'nsd_id': nsd_instance, 'name': ns_name}}
                ns_id = self._nfv_drivers.invoke(
                    nfv_driver,  # How to tell it is Tacker
                    'ns_create',
                    ns_dict=ns_arg,
                    auth_attr=vim_res['vim_auth'], )
                mes_info['mes_mapping']['NS'].append(ns_id)
            # Call tacker client driver

        vnffgds = mesd['attributes'].get('vnffgds')
        if vnffgds:
          vnffgds_list = vnffgds.split('-')
          mes_info['mes_mapping']['VNFFG'] = list()
          for vnffgd in vnffgds_list:
            vnffg_name = vnffgds + '-' + name + '-' + uuidutils.generate_uuid()
            vnffgd_instance = self._nfv_drivers.invoke(
                nfv_driver,  # How to tell it is Tacker
                'vnffgd_get',
                nsd_name=vnffgd,
                auth_attr=vim_res['vim_auth'], )
            if vnffgd_instance:
                vnffg_arg = {'vnffg': {'vnffgd_id': vnffgd_instance, 'name': vnffg_name}}
                vnffg_id = self._nfv_drivers.invoke(
                    nfv_driver,  # How to tell it is Tacker
                    'vnffg_create',
                    vnffg_dict=vnffg_arg,
                    auth_attr=vim_res['vim_auth'], )
                mes_info['mes_mapping']['VNFFG'].append(vnffg_id)
            # Call Tacker client driver

        mes_dict = super(MesoPlugin, self).create_mes(context, mes)

        def _create_mes_wait(self_obj, mes_id):
            mes_status = "ACTIVE"
            ns_status = "PENDING_CREATE"
            vnffg_status = "PENDING_CREATE"
            mec_status = "PENDING_CREATE"
            ns_retries = NS_RETRIES
            mec_retries = MEC_RETRIES
            vnffg_retries = VNFFG_RETRIES
            mes_mapping = self.get_mes(context, mes_id)['mes_mapping']
            # Check MECA
            while mec_status == "PENDING_CREATE" and mec_retries > 0:
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
                while ns_status == "PENDING_CREATE" and ns_retries > 0:
                    time.sleep(NS_RETRY_WAIT)
                    ns_list = mes_mapping['NS']
                    # Todo: support multiple NSs
                    ns_instance = self._nfv_drivers.invoke(
                        nfv_driver,  # How to tell it is Tacker
                        'ns_get',
                        ns_id=ns_list[0],
                        auth_attr=vim_res['vim_auth'], )
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
                while vnffg_status == "PENDING_CREATE" and vnffg_retries > 0:
                    time.sleep(VNFFG_RETRY_WAIT)
                    vnffg_list = mes_mapping['VNFFG']
                    # Todo: support multiple VNFFGs
                    vnffg_instance = self._nfv_drivers.invoke(
                        nfv_driver,  # How to tell it is Tacker
                        'vnffg_get',
                        vnffg_id=vnffg_list[0],
                        auth_attr=vim_res['vim_auth'], )
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
        mesd = self.get_mesd(context, mes['mesd_id'])
        mesd_dict = yaml.safe_load(mesd['attributes']['mesd'])
        vim_res = self.vim_client.get_vim(context, mes['vim_id'])
        mes_mapping = mes['mes_mapping']
        meca_id = mes_mapping['MECA']
        meo_plugin = manager.ApmecManager.get_service_plugins()['MEO']
        try:
            meca_id = meo_plugin.delete_meca(context, meca_id)
        except Exception as e:
            LOG.error('Error while deleting the MECA(s): %s', e)

        if mes_mapping.get('NS'):
            # Todo: support multiple NSs
            ns_id = mes_mapping['NS'][0]
            nfv_driver = None
            if mesd_dict['imports'].get('nsds'):
                nfv_driver = mesd_dict['imports']['nsds']['nfv_driver']
                nfv_driver = nfv_driver.lower()
            if not nfv_driver:
                raise meso.NFVDriverNotFound(mesd_name=mesd_dict['name'])
            try:
                self._nfv_drivers.invoke(
                    nfv_driver,
                    'ns_delete',
                    ns_id=ns_id,
                    auth_attr=vim_res['vim_auth'])
            except Exception as e:
                LOG.error('Error while deleting the NS(s): %s', e)
        if mes_mapping.get('VNFFG'):
            # Todo: support multiple VNFFGs
            vnffg_id = mes_mapping['VNFFG'][0]
            nfv_driver = None
            if mesd_dict['imports'].get('vnffgds'):
                nfv_driver = mesd_dict['imports']['vnffgds']['nfv_driver']
                nfv_driver = nfv_driver.lower()
            if not nfv_driver:
                raise meso.NFVDriverNotFound(mesd_name=mesd_dict['name'])
            try:
                self._nfv_drivers.invoke(
                    nfv_driver,
                    'vnffg_delete',
                    vnffg_id=vnffg_id,
                    auth_attr=vim_res['vim_auth'])
            except Exception as e:
                LOG.error('Error while deleting the VNFFG(s): %s', e)

        super(MesoPlugin, self).delete_mes(context, mes_id)

        def _delete_mes_wait(mes_id):
            ns_status = "PENDING_DELETE"
            vnffg_status = "PENDING_DELETE"
            mec_status = "PENDING_DELETE"
            ns_retries = NS_RETRIES
            mec_retries = MEC_RETRIES
            vnffg_retries = VNFFG_RETRIES
            error_reason_meca = None
            error_reason_ns = None
            error_reason_vnffg = None
            # Check MECA
            while mec_status == "PENDING_DELETE" and mec_retries > 0:
                time.sleep(MEC_RETRY_WAIT)
                meca_id = mes_mapping['MECA']
                meca_list = meo_plugin.get_mecas(context)
                is_deleted = True
                for meca in meca_list:
                    if meca_id in meca['id']:
                        is_deleted = False
                if is_deleted:
                    break
                mec_status = meo_plugin.get_meca(context, meca_id)['status']
                LOG.debug('status: %s', mec_status)
                if mec_status == 'ERROR':
                    break
                mec_retries = mec_retries - 1
            if mec_retries == 0 and mec_status == 'PENDING_DELETE':
                error_reason_meca = _(
                    "MES deletion is not completed within"
                    " {wait} seconds as deletion of MECA").format(
                    wait=MEC_RETRIES * MEC_RETRY_WAIT)
            # Check NS/VNFFG status
            if mes_mapping.get('NS'):
                while ns_status == "PENDING_DELETE" and ns_retries > 0:
                    time.sleep(NS_RETRY_WAIT)
                    ns_list = mes_mapping['NS']
                    # Todo: support multiple NSs
                    is_existed = self._nfv_drivers.invoke(
                        nfv_driver,  # How to tell it is Tacker
                        'ns_check',
                        ns_id=ns_list[0],
                        auth_attr=vim_res['vim_auth'], )
                    if not is_existed:
                        break
                    ns_instance = self._nfv_drivers.invoke(
                        nfv_driver,  # How to tell it is Tacker
                        'ns_get',
                        ns_id=ns_list[0],
                        auth_attr=vim_res['vim_auth'], )
                    ns_status = ns_instance['status']
                    LOG.debug('status: %s', ns_status)
                    if ns_status == 'ERROR':
                        break
                    ns_retries = ns_retries - 1
                if ns_retries == 0 and ns_status == 'PENDING_DELETE':
                    error_reason_ns = _(
                        "MES deletion is not completed within"
                        " {wait} seconds as deletion of NS(s)").format(
                        wait=NS_RETRIES * NS_RETRY_WAIT)
            if mes_mapping.get('VNFFG'):
                while vnffg_status == "PENDING_DELETE" and vnffg_retries > 0:
                    time.sleep(VNFFG_RETRY_WAIT)
                    vnffg_list = mes_mapping['VNFFG']
                    # Todo: support multiple VNFFGs
                    is_existed = self._nfv_drivers.invoke(
                        nfv_driver,  # How to tell it is Tacker
                        'vnffg_check',
                        vnffg_id=vnffg_list[0],
                        auth_attr=vim_res['vim_auth'], )
                    if not is_existed:
                        break
                    vnffg_instance = self._nfv_drivers.invoke(
                        nfv_driver,  # How to tell it is Tacker
                        'vnffg_get',
                        vnffg_id=vnffg_list[0],
                        auth_attr=vim_res['vim_auth'], )
                    vnffg_status = vnffg_instance['status']
                    LOG.debug('status: %s', vnffg_status)
                    if vnffg_status == 'ERROR':
                        break
                    vnffg_retries = vnffg_retries - 1
                if vnffg_retries == 0 and vnffg_status == 'PENDING_DELETE':
                    error_reason_vnffg = _(
                        "MES deletion is not completed within"
                        " {wait} seconds as deletion of VNFFG(s)").format(
                        wait=VNFFG_RETRIES * VNFFG_RETRY_WAIT)
            error = False
            if mec_status == "ERROR" or ns_status == "ERROR" or vnffg_status == "ERROR":
                error = True
            error_reason = None
            for reason in [error_reason_meca, error_reason_ns, error_reason_vnffg]:
                error_reason = reason if reason else None

            super(MesoPlugin, self).delete_mes_post(
                context, mes_id, error_reason=error_reason, error=error)
        self.spawn_n(_delete_mes_wait, mes['id'])
        return mes['id']

    def update_mes(self, context, mes_id, mes):
        mes_info = mes['mes']
        old_mes = super(MesoPlugin, self).get_mes(context, mes_id)
        old_mesd = self.get_mesd(context, old_mes['mesd_id'])
        old_mesd_mapping = old_mesd['mesd_mapping']
        name = old_mes['name']
        # create inline mesd if given by user
        if mes_info.get('mesd_template'):
            mes_name = utils.generate_resource_name(name, 'inline')
            mesd = {'mesd': {'tenant_id': old_mes['tenant_id'],
                           'name': mes_name,
                           'attributes': {
                               'mesd': mes_info['mesd_template']},
                           'template_source': 'inline',
                           'description': old_mes['description']}}
            try:
                mes_info['mesd_id'] = \
                    self.create_mesd(context, mesd).get('id')
            except Exception:
                with excutils.save_and_reraise_exception():
                    super(MesoPlugin, self)._update_mes_status(context, mes_id, constants.ACTIVE)

        mesd = self.get_mesd(context, mes_info['mesd_id'])
        mesd_dict = yaml.safe_load(mesd['attributes']['mesd'])
        new_mesd_mapping = mesd['mesd_mapping']
        region_name = mes.setdefault('placement_attr', {}).get(
            'region_name', None)
        vim_res = self.vim_client.get_vim(context, old_mes['vim_id'],
                                          region_name)
        # Compare new_mesd_mapping and old_mesd_mapping to figure out which is updated
        if old_mesd_mapping['MECA'] != new_mesd_mapping['MECA']:
            # Update MECA
            meo_plugin = manager.ApmecManager.get_service_plugins()['MEO']
            # Build the MECA template here
            mecad_id = new_mesd_mapping['MECA']
            mecad = meo_plugin.get_mecad(context, mecad_id)
            mecad_template = yaml.safe_load(mecad['attributes']['mecad'])
            old_meca_id = old_mes['mes_mapping']['MECA']
            meca_id = meo_plugin.update_meca(context, old_meca_id, mecad_template)
        if old_mesd_mapping.get('NS') != new_mesd_mapping.get("NS"):
            # Todo: Support multiple NSs
            nfv_driver = None
            if mesd_dict['imports'].get('nsds'):
                nfv_driver = mesd_dict['imports']['nsds']['nfv_driver']
                nfv_driver = nfv_driver.lower()
            if not nfv_driver:
                raise meso.NFVDriverNotFound(mesd_name=mesd_dict['name'])
            nsd_id = new_mesd_mapping['NS'][0]
            nsd_dict = self._nfv_drivers.invoke(
                nfv_driver,  # How to tell it is Tacker
                'nsd_get',
                nsd_id=nsd_id,
                auth_attr=vim_res['vim_auth'], )
            nsd_template = yaml.safe_load(nsd_dict['attributes']['nsd'])
            old_ns_id = old_mes['mes_mapping']['NS'][0]
            ns_arg = {'ns': {'nsd_template': nsd_template}}
            ns_id = self._nfv_drivers.invoke(
                nfv_driver,  # How to tell it is Tacker
                'ns_update',
                ns_id=old_ns_id,
                ns_dict=ns_arg,
                auth_attr=vim_res['vim_auth'], )

        if old_mesd_mapping.get('VNFFG') != new_mesd_mapping.get("VNFFG"):
            # Todo: Support multiple VNFFGs
            nfv_driver = None
            if mesd_dict['imports'].get('vnffgds'):
                nfv_driver = mesd_dict['imports']['vnffgds']['nfv_driver']
                nfv_driver = nfv_driver.lower()
            if not nfv_driver:
                raise meso.NFVDriverNotFound(mesd_name=mesd_dict['name'])
            vnffgd_id = new_mesd_mapping['VNFFGD'][0]
            vnffgd_dict = self._nfv_drivers.invoke(
                nfv_driver,  # How to tell it is Tacker
                'vnffgd_get',
                vnffgd_id=vnffgd_id,
                auth_attr=vim_res['vim_auth'], )
            vnffgd_template = yaml.safe_load(vnffgd_dict['attributes']['vnffgd'])
            old_vnffg_id = old_mes['mes_mapping']['VNFFG'][0]
            vnffg_arg = {'vnffg': {'vnffgd_template': vnffgd_template}}
            ns_id = self._nfv_drivers.invoke(
                nfv_driver,  # How to tell it is Tacker
                'ns_update',
                vnffg_id=old_vnffg_id,
                vnffg_dict=vnffg_arg,
                auth_attr=vim_res['vim_auth'], )

        # Step-1
        param_values = dict()
        if 'get_input' in str(nsd_dict):
            self._process_parameterized_input(ns['ns']['attributes'],
                                              nsd_dict)

        # Step-2
        vnfds = nsd['vnfds']
        # vnfd_dict is used while generating workflow
        vnfd_dict = dict()
        for node_name, node_val in \
                (nsd_dict['topology_template']['node_templates']).items():
            if node_val.get('type') not in vnfds.keys():
                continue
            vnfd_name = vnfds[node_val.get('type')]
            if not vnfd_dict.get(vnfd_name):
                vnfd_dict[vnfd_name] = {
                    'id': self._get_vnfd_id(vnfd_name, onboarded_vnfds),
                    'instances': [node_name]
                }
            else:
                vnfd_dict[vnfd_name]['instances'].append(node_name)
            if not node_val.get('requirements'):
                continue
            if not param_values.get(vnfd_name):
                param_values[vnfd_name] = {}
            param_values[vnfd_name]['substitution_mappings'] = dict()
            req_dict = dict()
            requirements = node_val.get('requirements')
            for requirement in requirements:
                req_name = list(requirement.keys())[0]
                req_val = list(requirement.values())[0]
                res_name = req_val + ns['ns']['nsd_id'][:11]
                req_dict[req_name] = res_name
                if req_val in nsd_dict['topology_template']['node_templates']:
                    param_values[vnfd_name]['substitution_mappings'][
                        res_name] = nsd_dict['topology_template'][
                        'node_templates'][req_val]

            param_values[vnfd_name]['substitution_mappings'][
                'requirements'] = req_dict
        ns['vnfd_details'] = vnfd_dict
        # Step-3
        kwargs = {'ns': ns, 'params': param_values}

        # NOTE NoTasksException is raised if no tasks.
        workflow = self._vim_drivers.invoke(
            driver_type,
            'prepare_and_create_workflow',
            resource='vnf',
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
        ns_dict = super(NfvoPlugin, self)._update_ns_pre(context, ns_id)

        def _update_ns_wait(self_obj, ns_id, execution_id):
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
                    "NS update is not completed within"
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
            super(NfvoPlugin, self)._update_ns_post(context, ns_id, exec_obj,
                                                    vnfd_dict, error_reason)

        self.spawn_n(_update_ns_wait, self, ns_dict['id'],
                     mistral_execution.id)
        return mes_dict
