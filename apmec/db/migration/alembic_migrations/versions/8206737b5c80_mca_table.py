# Copyright 2018 OpenStack Foundation
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

"""mca-table

Revision ID: 8206737b5c80
Revises: e9a1e47fb0b5
Create Date: 2018-06-08 15:58:43.286238

"""

# revision identifiers, used by Alembic.
revision = '8206737b5c80'
down_revision = 'e9a1e47fb0b5'

from alembic import op
import sqlalchemy as sa


from apmec.db import migration


def upgrade(active_plugins=None, options=None):
    pass
