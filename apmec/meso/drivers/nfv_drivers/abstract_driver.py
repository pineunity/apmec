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

import abc

import six

from apmec.api import extensions


@six.add_metaclass(abc.ABCMeta)
class NfvAbstractDriver(extensions.PluginInterface):

    @abc.abstractmethod
    def get_type(self):
        """Get NFV Driver type

        Return one of predefined types of NFV drivers.
        """
        pass

    @abc.abstractmethod
    def get_name(self):
        """Get NFV driver name

        Return a symbolic name for the NFV driver.
        """
        pass

    @abc.abstractmethod
    def get_description(self):
        pass

    @abc.abstractmethod
    def get_vim_resource_id(self, vim_obj, resource_type, resource_name):
        """Parses a VIM resource ID from a given type and name

        :param vim_obj: VIM information
        :param resource_type: type of resource, such as network, compute
        :param resource_name: name of resource, such at "test-network"
        :return: ID of resource
        """
        pass