.. -*- rst -*-

================================================
Virtualized Network Function Descriptors (MEADs)
================================================

Manages Virtualized Network Function Descriptors (MEADs).

The MEAD is a template which describes information about deployment
and behavior of Virtualized Network Functions (VNFs). For more information, see
`VNF Descriptor Template Guide
<https://docs.openstack.org/apmec/latest/contributor/mead_template_description.html>`_.

Create MEAD
===========

.. rest_method::  POST /v1.0/meads

Creates a MEAD.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 201

.. rest_status_code:: error status.yaml

  - 400
  - 401
  - 500

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - tenant_id: tenant_id_opt
  - name: name
  - description: description_opt
  - service_types: service_types
  - attributes: mead_attributes

Request Example
---------------

.. literalinclude:: samples/meads/meads-create-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - mead: mead
  - service_types: service_types
  - description: description
  - tenant_id: tenant_id
  - created_at: created_at
  - updated_at: updated_at
  - attributes: mead_attributes
  - id: mead_id
  - name: name

Response Example
----------------

.. literalinclude:: samples/meads/meads-create-response.json
   :language: javascript

List MEADs
==========

.. rest_method::  GET /v1.0/meads

Lists MEADs.

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

  - meads: meads
  - service_types: service_types
  - description: description
  - tenant_id: tenant_id
  - created_at: created_at
  - updated_at: updated_at
  - attributes: mead_attributes
  - id: mead_id
  - name: name
  - template_source: mead_template_source


Response Example
----------------

.. literalinclude:: samples/meads/meads-list-response.json
   :language: javascript

Show MEAD
=========

.. rest_method::  GET /v1.0/meads/{mead_id}

Shows information of a given MEAD.

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

  - mead_id: mead_id_path

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - mead: mead
  - service_types: service_types
  - description: description
  - tenant_id: tenant_id
  - created_at: created_at
  - updated_at: updated_at
  - attributes: mead_attributes
  - id: mead_id
  - name: name
  - template_source: mead_template_source

Response Example
----------------

.. literalinclude:: samples/meads/meads-show-response.json
   :language: javascript

Update MEAD
===========

.. rest_method::  PUT /v1.0/meads/{mead_id}

Updates a given MEAD.

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

  - mead_id: mead_id_path
  - name: name_opt
  - description: description_opt

Request Example
---------------

.. literalinclude:: samples/meads/meads-update-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - mead: mead
  - service_types: service_types
  - description: description
  - tenant_id: tenant_id
  - created_at: created_at
  - updated_at: updated_at
  - attributes: mead_attributes
  - id: mead_id
  - name: name

Response Example
----------------

.. literalinclude:: samples/meads/meads-update-response.json
   :language: javascript

Delete MEAD
===========

.. rest_method::  DELETE /v1.0/meads/{mead_id}

Deletes a given MEAD.
Only a MEAD without any associated VNFs can be deleted.

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

  - mead_id: mead_id_path
