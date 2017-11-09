.. -*- rst -*-

==========================================
VNF Forwarding Graph Descriptors (VNFFGDs)
==========================================

Manages VNF Forwarding Graph Descriptors (VNFFGDs).

The VNFFGD is a template which describes information about deployment and
behavior of VNF Forwarding Graphs (VNFFGs). For more information, see
`VNFFG Descriptor Template Guide
<https://docs.openstack.org/apmec/latest/contributor/NANYD_template_description.html>`_.


Create VNFFGD
=============

.. rest_method::  POST /v1.0/NANYDs

Creates a VNFFGD.

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
  - template: NANYD_template
  - description: description_opt

Request Example
---------------

.. literalinclude:: samples/NANYDs/NANYDs-create-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - NANYD: NANYD
  - tenant_id: tenant_id
  - name: name
  - template: NANYD_template
  - description: description

Response Example
----------------

.. literalinclude:: samples/NANYDs/NANYDs-create-response.json
   :language: javascript

List VNFFGDs
============

.. rest_method::  GET /v1.0/NANYDs

Lists VNFFGDs.

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

  - NANYDs: NANYDs
  - description: description
  - tenant_id: tenant_id
  - id: NANYD_id
  - name: name


Response Example
----------------

.. literalinclude:: samples/NANYDs/NANYDs-list-response.json
   :language: javascript

Show VNFFGD
===========

.. rest_method::  GET /v1.0/NANYDs/{NANYD_id}

Shows information of a given VNFFGD.

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

  - NANYD_id: NANYD_id_path

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - NANYD: NANYD
  - description: description
  - tenant_id: tenant_id
  - id: NANYD_id
  - name: name

Response Example
----------------

.. literalinclude:: samples/NANYDs/NANYDs-show-response.json
   :language: javascript

Delete VNFFGD
=============

.. rest_method::  DELETE /v1.0/NANYDs/{NANYD_id}

Deletes a given VNFFGD.
Only a VNFFGD without any associated VNFFGs can be deleted.

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

  - NANYD_id: NANYD_id_path
