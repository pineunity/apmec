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
#

from oslo_log import log as logging
from oslo_utils import timeutils

from tacker.db.common_services import common_services_db_plugin
from tacker.plugins.common import constants
from tacker.vnfm.policy_actions import abstract_action

LOG = logging.getLogger(__name__)


def _log_monitor_events(context, vnf_dict, evt_details):
    _cos_db_plg = common_services_db_plugin.CommonServicesPluginDb()
    _cos_db_plg.create_event(context, res_id=vnf_dict['id'],
                             res_type=constants.RES_TYPE_VNF,
                             res_state=vnf_dict['status'],
                             evt_type=constants.RES_EVT_MONITOR,
                             tstamp=timeutils.utcnow(),
                             details=evt_details)


class VNFActionLog(abstract_action.AbstractPolicyAction):
    def get_type(self):
        return 'log'

    def get_name(self):
        return 'log'

    def get_description(self):
        return 'Tacker VNF logging policy'

    def execute_action(self, plugin, context, vnf_dict, args):
        vnf_id = vnf_dict['id']
        LOG.error('vnf %s dead', vnf_id)
        _log_monitor_events(context,
                            vnf_dict,
                            "ActionLogOnly invoked")


class VNFActionLogAndKill(abstract_action.AbstractPolicyAction):
    def get_type(self):
        return 'log_and_kill'

    def get_name(self):
        return 'log_and_kill'

    def get_description(self):
        return 'Tacker VNF log_and_kill policy'

    def execute_action(self, plugin, context, vnf_dict, args):
        _log_monitor_events(context,
                            vnf_dict,
                            "ActionLogAndKill invoked")
        vnf_id = vnf_dict['id']
        if plugin._mark_vnf_dead(vnf_dict['id']):
            if vnf_dict['attributes'].get('monitoring_policy'):
                plugin._vnf_monitor.mark_dead(vnf_dict['id'])
            plugin.delete_vnf(context, vnf_id)
        LOG.error('vnf %s dead', vnf_id)
