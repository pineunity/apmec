..
      Copyright 2014-2015 OpenStack Foundation
      All Rights Reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

======================
VNF Manager User Guide
======================

Apmec VNF Manager (VNFM) component manages the life-cycle of a Virtual Network
Function (VNF). VNFM takes care of deployment, monitoring, scaling and removal
of VNFs on a Virtual Infrastructure Manager (VIM).


Onboarding VNF
==============

TOSCA VNFD templates can be onboarded to Apmec VNFD Catalog using following
command:

.. code-block:: console

   apmec mead-create --mead-file <yaml file path> <VNFD-NAME>

.. note::

   Users can find various sample TOSCA templates at https://github.com/openstack/apmec/tree/master/samples/tosca-templates/mead

Deploying VNF
=============

There are two ways to create a VNF in Apmec.

#. Using Apmec Catalog
#. Direct VNF Instantiation

Using Apmec Catalog
--------------------

In this method, a TOSCA VNFD template is first onboarded into Apmec VNFD
catalog. This VNFD is then used to create VNF. This is most common way of
creating VNFs in Apmec.

   i). Onboard a TOSCA VNFD template.

.. code-block:: console

   apmec mead-create --mead-file <yaml file path> <VNFD-NAME>
..

  ii). Create a VNF.

.. code-block:: console

   apmec vnf-create --mead-name <VNFD-FILE-NAME> <VNF-NAME>


Example
~~~~~~~

.. code-block:: console

    apmec mead-create --mead-file sample-mead-hello-world.yaml hello-world-mead
    apmec vnf-create --mead-name hello-world-mead hw-vnf

Direct VNF Instantiation
------------------------

In this method, VNF is created directly from the TOSCA template without
onboarding the template into Apmec VNFD Catalog.

.. code-block:: console

   apmec vnf-create --mead-template <VNFD-FILE-NAME> <VNF-NAME>

This method is recommended when NFV Catalog is maintained outside Apmec and
Apmec is primarily used as a NFV workflow engine.

Example
~~~~~~~

.. code-block:: console

    apmec vnf-create --mead-template sample-mead-hello-world.yaml hw-vnf

.. note ::

    mead-list command will show only the onboarded VNFDs. To list the VNFDs
    created internally for direct VNF instantiation, use
    '--template-source inline' flag. To list both onboarded and inline VNFDs,
    use '--template-source all' flag. The default flag for mead-list command
    is '--template-source onboarded'.

    .. code-block:: console

      apmec mead-list --template-source inline
      apmec mead-list --template-source all

Finding VNFM Status
===================

Status of various VNFM resources can be checked by following commands.

.. code-block:: console

   apmec vim-list
   apmec mead-list
   apmec vnf-list
   apmec vnf-show <VNF_ID>
   apmec mead-show <VNFD_ID>

..

Deleting VNF and VNFD
=====================

VNFs and VNFDs can be deleted as shown below.

.. code-block:: console

   apmec vnf-delete <VNF_ID/NAME>
   apmec mead-delete <VNFD_ID/NAME>
..
