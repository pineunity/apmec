# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import ast
from datetime import datetime

from oslo_db.exception import DBDuplicateEntry
from oslo_log import log as logging
from oslo_utils import timeutils
from oslo_utils import uuidutils
from six import iteritems

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.orm import exc as orm_exc
from sqlalchemy import schema

from apmec.common import exceptions
from apmec.db.common_services import common_services_db_plugin
from apmec.db import db_base
from apmec.db import model_base
from apmec.db import models_v1
from apmec.db import types
from apmec.extensions import meo
from apmec.plugins.common import constants

LOG = logging.getLogger(__name__)
_ACTIVE_UPDATE = (constants.ACTIVE, constants.PENDING_UPDATE)
_ACTIVE_UPDATE_ERROR_DEAD = (
    constants.PENDING_CREATE, constants.ACTIVE, constants.PENDING_UPDATE,
    constants.ERROR, constants.DEAD)
CREATE_STATES = (constants.PENDING_CREATE, constants.DEAD)


###########################################################################
# db tables

class MCAD(model_base.BASE, models_v1.HasId, models_v1.HasTenant,
        models_v1.Audit):
    """Represents MCAD to create MCA."""

    __tablename__ = 'mcad'
    # Descriptive name
    name = sa.Column(sa.String(255), nullable=False)
    description = sa.Column(sa.Text)
    meads = sa.Column(types.Json, nullable=True)

    # Mcad template source - onboarded
    template_source = sa.Column(sa.String(255), server_default='onboarded')

    # (key, value) pair to spin up
    attributes = orm.relationship('MCADAttribute',
                                  backref='mcad')

    __table_args__ = (
        schema.UniqueConstraint(
            "tenant_id",
            "name",
            name="uniq_mcad0tenant_id0name"),
    )


class MCADAttribute(model_base.BASE, models_v1.HasId):
    """Represents attributes necessary for creation of mca in (key, value) pair

    """

    __tablename__ = 'mcad_attribute'
    mcad_id = sa.Column(types.Uuid, sa.ForeignKey('mcad.id'),
            nullable=False)
    key = sa.Column(sa.String(255), nullable=False)
    value = sa.Column(sa.TEXT(65535), nullable=True)


class MCA(model_base.BASE, models_v1.HasId, models_v1.HasTenant,
        models_v1.Audit):
    """Represents network services that deploys services.

    """

    __tablename__ = 'mca'
    mcad_id = sa.Column(types.Uuid, sa.ForeignKey('mcad.id'))
    mcad = orm.relationship('MCAD')

    name = sa.Column(sa.String(255), nullable=False)
    description = sa.Column(sa.Text, nullable=True)

    # Dict of MEA details that network service launches
    mea_ids = sa.Column(sa.TEXT(65535), nullable=True)

    # Dict of mgmt urls that network servic launches
    mgmt_urls = sa.Column(sa.TEXT(65535), nullable=True)

    status = sa.Column(sa.String(64), nullable=False)
    vim_id = sa.Column(types.Uuid, sa.ForeignKey('vims.id'), nullable=False)
    error_reason = sa.Column(sa.Text, nullable=True)

    __table_args__ = (
        schema.UniqueConstraint(
            "tenant_id",
            "name",
            name="uniq_mca0tenant_id0name"),
    )


class MCAPluginDb(meo.MCAPluginBase, db_base.CommonDbMixin):

    def __init__(self):
        super(MCAPluginDb, self).__init__()
        self._cos_db_plg = common_services_db_plugin.CommonServicesPluginDb()

    def _get_resource(self, context, model, id):
        try:
            return self._get_by_id(context, model, id)
        except orm_exc.NoResultFound:
            if issubclass(model, MCAD):
                raise meo.MCADNotFound(mcad_id=id)
            if issubclass(model, MCA):
                raise meo.MCANotFound(mca_id=id)
            else:
                raise

    def _get_mca_db(self, context, mca_id, current_statuses, new_status):
        try:
            mca_db = (
                self._model_query(context, MCA).
                filter(MCA.id == mca_id).
                filter(MCA.status.in_(current_statuses)).
                with_lockmode('update').one())
        except orm_exc.NoResultFound:
            raise meo.MCANotFound(mca_id=mca_id)
        mca_db.update({'status': new_status})
        return mca_db

    def _make_attributes_dict(self, attributes_db):
        return dict((attr.key, attr.value) for attr in attributes_db)

    def _make_mcad_dict(self, mcad, fields=None):
        res = {
            'attributes': self._make_attributes_dict(mcad['attributes']),
        }
        key_list = ('id', 'tenant_id', 'name', 'description',
                    'created_at', 'updated_at', 'meads', 'template_source')
        res.update((key, mcad[key]) for key in key_list)
        return self._fields(res, fields)

    def _make_dev_attrs_dict(self, dev_attrs_db):
        return dict((arg.key, arg.value) for arg in dev_attrs_db)

    def _make_mca_dict(self, mca_db, fields=None):
        LOG.debug('mca_db %s', mca_db)
        res = {}
        key_list = ('id', 'tenant_id', 'mcad_id', 'name', 'description',
                    'mea_ids', 'status', 'mgmt_urls', 'error_reason',
                    'vim_id', 'created_at', 'updated_at')
        res.update((key, mca_db[key]) for key in key_list)
        return self._fields(res, fields)

    def create_mcad(self, context, mcad):
        meads = mcad['meads']
        mcad = mcad['mcad']
        LOG.debug('mcad %s', mcad)
        tenant_id = self._get_tenant_id_for_create(context, mcad)
        template_source = mcad.get('template_source')

        try:
            with context.session.begin(subtransactions=True):
                mcad_id = uuidutils.generate_uuid()
                mcad_db = MCAD(
                    id=mcad_id,
                    tenant_id=tenant_id,
                    name=mcad.get('name'),
                    meads=meads,
                    description=mcad.get('description'),
                    deleted_at=datetime.min,
                    template_source=template_source)
                context.session.add(mcad_db)
                for (key, value) in mcad.get('attributes', {}).items():
                    attribute_db = MCADAttribute(
                        id=uuidutils.generate_uuid(),
                        mcad_id=mcad_id,
                        key=key,
                        value=value)
                    context.session.add(attribute_db)
        except DBDuplicateEntry as e:
            raise exceptions.DuplicateEntity(
                _type="mcad",
                entry=e.columns)
        LOG.debug('mcad_db %(mcad_db)s %(attributes)s ',
                  {'mcad_db': mcad_db,
                   'attributes': mcad_db.attributes})
        mcad_dict = self._make_mcad_dict(mcad_db)
        LOG.debug('mcad_dict %s', mcad_dict)
        self._cos_db_plg.create_event(
            context, res_id=mcad_dict['id'],
            res_type=constants.RES_TYPE_MCAD,
            res_state=constants.RES_EVT_ONBOARDED,
            evt_type=constants.RES_EVT_CREATE,
            tstamp=mcad_dict[constants.RES_EVT_CREATED_FLD])
        return mcad_dict

    def delete_mcad(self,
            context,
            mcad_id,
            soft_delete=True):
        with context.session.begin(subtransactions=True):
            mcas_db = context.session.query(MCA).filter_by(
                mcad_id=mcad_id).first()
            if mcas_db is not None and mcas_db.deleted_at is None:
                raise meo.MCADInUse(mcad_id=mcad_id)

            mcad_db = self._get_resource(context, MCAD,
                                        mcad_id)
            if soft_delete:
                mcad_db.update({'deleted_at': timeutils.utcnow()})
                self._cos_db_plg.create_event(
                    context, res_id=mcad_db['id'],
                    res_type=constants.RES_TYPE_MCAD,
                    res_state=constants.RES_EVT_NA_STATE,
                    evt_type=constants.RES_EVT_DELETE,
                    tstamp=mcad_db[constants.RES_EVT_DELETED_FLD])
            else:
                context.session.query(MCADAttribute).filter_by(
                    mcad_id=mcad_id).delete()
                context.session.delete(mcad_db)

    def get_mcad(self, context, mcad_id, fields=None):
        mcad_db = self._get_resource(context, MCAD, mcad_id)
        return self._make_mcad_dict(mcad_db)

    def get_mcads(self, context, filters, fields=None):
        if ('template_source' in filters) and \
                (filters['template_source'][0] == 'all'):
            filters.pop('template_source')
        return self._get_collection(context, MCAD,
                                    self._make_mcad_dict,
                                    filters=filters, fields=fields)

    # reference implementation. needs to be overrided by subclass
    def create_mca(self, context, mca):
        LOG.debug('mca %s', mca)
        mca = mca['mca']
        tenant_id = self._get_tenant_id_for_create(context, mca)
        mcad_id = mca['mcad_id']
        vim_id = mca['vim_id']
        name = mca.get('name')
        mca_id = uuidutils.generate_uuid()
        try:
            with context.session.begin(subtransactions=True):
                mcad_db = self._get_resource(context, MCAD,
                                            mcad_id)
                mca_db = MCA(id=mca_id,
                           tenant_id=tenant_id,
                           name=name,
                           description=mcad_db.description,
                           mea_ids=None,
                           status=constants.PENDING_CREATE,
                           mgmt_urls=None,
                           mcad_id=mcad_id,
                           vim_id=vim_id,
                           error_reason=None,
                           deleted_at=datetime.min)
                context.session.add(mca_db)
        except DBDuplicateEntry as e:
            raise exceptions.DuplicateEntity(
                _type="mca",
                entry=e.columns)
        evt_details = "MCA UUID assigned."
        self._cos_db_plg.create_event(
            context, res_id=mca_id,
            res_type=constants.RES_TYPE_mca,
            res_state=constants.PENDING_CREATE,
            evt_type=constants.RES_EVT_CREATE,
            tstamp=mca_db[constants.RES_EVT_CREATED_FLD],
            details=evt_details)
        return self._make_mca_dict(mca_db)

    def create_mca_post(self, context, mca_id, mistral_obj,
            mead_dict, error_reason):
        LOG.debug('mca ID %s', mca_id)
        output = ast.literal_eval(mistral_obj.output)
        mgmt_urls = dict()
        mea_ids = dict()
        if len(output) > 0:
            for mead_name, mead_val in iteritems(mead_dict):
                for instance in mead_val['instances']:
                    if 'mgmt_url_' + instance in output:
                        mgmt_urls[instance] = ast.literal_eval(
                            output['mgmt_url_' + instance].strip())
                        mea_ids[instance] = output['mea_id_' + instance]
            mea_ids = str(mea_ids)
            mgmt_urls = str(mgmt_urls)

        if not mea_ids:
            mea_ids = None
        if not mgmt_urls:
            mgmt_urls = None
        status = constants.ACTIVE if mistral_obj.state == 'SUCCESS' \
            else constants.ERROR
        with context.session.begin(subtransactions=True):
            mca_db = self._get_resource(context, MCA,
                                       mca_id)
            mca_db.update({'mea_ids': mea_ids})
            mca_db.update({'mgmt_urls': mgmt_urls})
            mca_db.update({'status': status})
            mca_db.update({'error_reason': error_reason})
            mca_db.update({'updated_at': timeutils.utcnow()})
            mca_dict = self._make_mca_dict(mca_db)
            self._cos_db_plg.create_event(
                context, res_id=mca_dict['id'],
                res_type=constants.RES_TYPE_mca,
                res_state=constants.RES_EVT_NA_STATE,
                evt_type=constants.RES_EVT_UPDATE,
                tstamp=mca_dict[constants.RES_EVT_UPDATED_FLD])
        return mca_dict

    # reference implementation. needs to be overrided by subclass
    def delete_mca(self, context, mca_id):
        with context.session.begin(subtransactions=True):
            mca_db = self._get_mca_db(
                context, mca_id, _ACTIVE_UPDATE_ERROR_DEAD,
                constants.PENDING_DELETE)
        deleted_mca_db = self._make_mca_dict(mca_db)
        self._cos_db_plg.create_event(
            context, res_id=mca_id,
            res_type=constants.RES_TYPE_mca,
            res_state=deleted_mca_db['status'],
            evt_type=constants.RES_EVT_DELETE,
            tstamp=timeutils.utcnow(), details="MCA delete initiated")
        return deleted_mca_db

    def delete_mca_post(self, context, mca_id, mistral_obj,
                       error_reason, soft_delete=True):
        mca = self.get_mca(context, mca_id)
        mcad_id = mca.get('mcad_id')
        with context.session.begin(subtransactions=True):
            query = (
                self._model_query(context, MCA).
                filter(MCA.id == mca_id).
                filter(MCA.status == constants.PENDING_DELETE))
            if mistral_obj and mistral_obj.state == 'ERROR':
                query.update({'status': constants.ERROR})
                self._cos_db_plg.create_event(
                    context, res_id=mca_id,
                    res_type=constants.RES_TYPE_mca,
                    res_state=constants.ERROR,
                    evt_type=constants.RES_EVT_DELETE,
                    tstamp=timeutils.utcnow(),
                    details="MCA Delete ERROR")
            else:
                if soft_delete:
                    deleted_time_stamp = timeutils.utcnow()
                    query.update({'deleted_at': deleted_time_stamp})
                    self._cos_db_plg.create_event(
                        context, res_id=mca_id,
                        res_type=constants.RES_TYPE_mca,
                        res_state=constants.PENDING_DELETE,
                        evt_type=constants.RES_EVT_DELETE,
                        tstamp=deleted_time_stamp,
                        details="mca Delete Complete")
                else:
                    query.delete()
            template_db = self._get_resource(context, MCAD, mcad_id)
            if template_db.get('template_source') == 'inline':
                self.delete_mcad(context, mcad_id)

    def get_mca(self, context, mca_id, fields=None):
        mca_db = self._get_resource(context, MCA, mca_id)
        return self._make_mca_dict(mca_db)

    def get_mcas(self, context, filters=None, fields=None):
        return self._get_collection(context, MCA,
                                    self._make_mca_dict,
                                    filters=filters, fields=fields)
