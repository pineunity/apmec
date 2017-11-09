# Copyright 2016 Red Hat Inc
# All Rights Reserved.
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

from apmec.services import service_base


@six.add_metaclass(abc.ABCMeta)
class VNFFGPluginBase(service_base.NFVPluginBase):

    @abc.abstractmethod
    def create_NANYD(self, context, NANYD):
        pass

    @abc.abstractmethod
    def delete_NANYD(self, context, NANYD_id):
        pass

    @abc.abstractmethod
    def get_NANYD(self, context, NANYD_id, fields=None):
        pass

    @abc.abstractmethod
    def get_NANYDs(self, context, filters=None, fields=None):
        pass

    @abc.abstractmethod
    def create_NANY(self, context, NANY):
        pass

    @abc.abstractmethod
    def get_NANYs(self, context, filters=None, fields=None):
        pass

    @abc.abstractmethod
    def get_NANY(self, context, NANY_id, fields=None):
        pass

    @abc.abstractmethod
    def update_NANY(self, context, NANY_id, NANY):
        pass

    @abc.abstractmethod
    def delete_NANY(self, context, NANY_id):
        pass

    @abc.abstractmethod
    def get_nfp(self, context, nfp_id, fields=None):
        pass

    @abc.abstractmethod
    def get_nfps(self, context, filters=None, fields=None):
        pass

    @abc.abstractmethod
    def get_sfcs(self, context, filters=None, fields=None):
        pass

    @abc.abstractmethod
    def get_sfc(self, context, sfc_id, fields=None):
        pass

    @abc.abstractmethod
    def get_classifiers(self, context, filters=None, fields=None):
        pass

    @abc.abstractmethod
    def get_classifier(self, context, classifier_id, fields=None):
        pass
