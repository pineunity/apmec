.. -*- rst -*-

====================================
Virtualized Network Functions (VNFs)
====================================

Manages Virtualized Network Functions (VNFs) and their resources.

The VNF takes on the responsibility for handling specific network functions.

Create VNF
==========

.. rest_method::  POST /v1.0/meas

Creates a VNF.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 201

.. rest_status_code:: error status.yaml

  - 400
  - 401
  - 404
  - 500

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - mea: mea
  - tenant_id: tenant_id_opt
  - mead_id: mead_id
  - vim_id: vim_id_opt
  - name: name
  - description: description_opt
  - attributes: mea_attributes_opt
  - config: mea_config_opt
  - param_values: mea_param_values_opt
  - placement_attr: mea_placement_attr_opt
  - mead_template: mead_template

Request Example
---------------

.. literalinclude:: samples/meas/meas-create-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - mea: mea
  - status: mea_status
  - description: description
  - mead_id: mead_id
  - tenant_id: tenant_id
  - created_at: mea_created_at
  - updated_at: mea_updated_at
  - instance_id: mea_instance_id
  - mgmt_url: mea_mgmt_url
  - vim_id: vim_id
  - placement_attr: mea_placement_attr
  - error_reason: mea_error_reason
  - attributes: mea_attributes
  - config: mea_config
  - param_values: mea_param_values
  - monitoring_policy: mea_monitoring_policy
  - heat_template: mea_heat_template
  - id: mea_id
  - name: name

Response Example
----------------

.. literalinclude:: samples/meas/meas-create-response.json
   :language: javascript

List VNFs
=========

.. rest_method::  GET /v1.0/meas

Lists VNFs.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 200

.. rest_status_code:: error status.yaml

  - 401
  - 500

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - meas: meas
  - status: mea_status
  - description: description
  - mead_id: mead_id
  - tenant_id: tenant_id
  - created_at: mea_created_at
  - updated_at: mea_updated_at
  - instance_id: mea_instance_id
  - mgmt_url: mea_mgmt_url
  - vim_id: vim_id
  - placement_attr: mea_placement_attr
  - error_reason: mea_error_reason
  - attributes: mea_attributes
  - config: mea_config
  - param_values: mea_param_values
  - monitoring_policy: mea_monitoring_policy
  - heat_template: mea_heat_template
  - id: mea_id
  - name: name

Response Example
----------------

.. literalinclude:: samples/meas/meas-list-response.json
   :language: javascript

Show VNF
========

.. rest_method::  GET /v1.0/meas/{mea_id}

Shows information of a given VNF.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 200

.. rest_status_code:: error status.yaml

  - 401
  - 404
  - 500

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - mea_id: mea_id_path

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - mea: mea
  - status: mea_status
  - description: description
  - mead_id: mead_id
  - tenant_id: tenant_id
  - created_at: mea_created_at
  - updated_at: mea_updated_at
  - instance_id: mea_instance_id
  - mgmt_url: mea_mgmt_url
  - vim_id: vim_id
  - placement_attr: mea_placement_attr
  - error_reason: mea_error_reason
  - attributes: mea_attributes
  - config: mea_config
  - param_values: mea_param_values
  - monitoring_policy: mea_monitoring_policy
  - heat_template: mea_heat_template
  - id: mea_id
  - name: name

Response Example
----------------

.. literalinclude:: samples/meas/meas-show-response.json
   :language: javascript

Update VNF
===========

.. rest_method::  PUT /v1.0/meas/{mea_id}

Updates a given VNF.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 200

.. rest_status_code:: error status.yaml

  - 400
  - 401
  - 404
  - 409
  - 500

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - mea_id: mea_id_path
  - attributes: mea_attributes_put
  - config: mea_config_opt

Request Example
---------------

.. literalinclude:: samples/meas/meas-update-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - mea: mea
  - status: mea_status
  - description: description
  - mead_id: mead_id
  - tenant_id: tenant_id
  - created_at: mea_created_at
  - updated_at: mea_updated_at
  - instance_id: mea_instance_id
  - mgmt_url: mea_mgmt_url
  - vim_id: vim_id
  - placement_attr: mea_placement_attr
  - error_reason: mea_error_reason
  - attributes: mea_attributes
  - config: mea_config
  - param_values: mea_param_values
  - monitoring_policy: mea_monitoring_policy
  - heat_template: mea_heat_template
  - id: mea_id
  - name: name

Response Example
----------------

.. literalinclude:: samples/meas/meas-update-response.json
   :language: javascript

Delete VNF
==========

.. rest_method::  DELETE /v1.0/meas/{mea_id}

Deletes a given VNF.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 204

.. rest_status_code:: error status.yaml

  - 401
  - 404
  - 409
  - 500

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - mea_id: mea_id_path

List VNF resources
==================

.. rest_method::  GET /v1.0/meas/{mea_id}/resources

Lists resources, such as VDU/CP, of a given VNF.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 200

.. rest_status_code:: error status.yaml

  - 401
  - 404
  - 500

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - mea_id: mea_id_path

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - resources: mea_resources
  - type: mea_resource_type
  - name: mea_resource_name
  - id: mea_resource_id

Response Example
----------------

.. literalinclude:: samples/meas/meas-resources-list-response.json
   :language: javascript

Trigger VNF scaling
===================

.. rest_method::  POST /v1.0/meas/{mea_id}/actions

Triggers VNF scaling action.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 201

.. rest_status_code:: error status.yaml

  - 400
  - 401
  - 404
  - 500

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - mea_id: mea_id_path
  - scale: mea_scale
  - policy: mea_scale_policy
  - type: mea_scale_type

Request Example
---------------

.. literalinclude:: samples/meas/meas-actions-create-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - scale: mea_scale
  - policy: mea_scale_policy
  - type: mea_scale_type

Response Example
----------------

.. literalinclude:: samples/meas/meas-actions-create-response.json
   :language: javascript
