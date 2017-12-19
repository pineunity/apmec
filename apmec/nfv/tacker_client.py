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

class TackerClient(object):
    """Tacker Client class for VNFM and NFVO negotiation"""

    def __init__(self, auth_attr):
        auth = identity.Password(**auth_attr)
        sess = session.Session(auth=auth)
        self.client = tacker_client.Client(session=sess)
