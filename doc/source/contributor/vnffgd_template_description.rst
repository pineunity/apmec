NFY Descriptor Template Guide
===============================
Overview
--------

This document explains NFYD template structure and its various fields based
on TOSCA standards `V1.0 CSD 03 <http://docs.oasis-open.org/tosca/tosca-mec/
v1.0/tosca-mec-v1.0.html>`_.

The behavioural and deployment information of a NFY in Apmec is defined in a
template known as NFY Descriptor (NFYD). The template is based on TOSCA
standards and is written in YAML. It is on-boarded in a NFY catalog.

Each NFYD template will have below fields:

::

    tosca_definitions_version:
       This defines the TOSCA definition version on which the template is based.
       The current version being tosca_simple_profile_for_mec_1_0_0.

    tosca_default_namespace:
       This is optional. It mentions default namespace which includes schema,
       types version etc.

    description:
       A short description about the template.

    metadata:
       template_name: A name to be given to the template.

    topology_template:
       Describes the topology of the NFY under node_template field.
       node_template:
           Describes node types of a NFY.
           FP:
               Describes properties and path of a Forwarding Path.
       groups:
           Describes groupings of nodes that have an implied relationship.
           NFY:
               Describes properties and members of a MEA Forwarding Graph.

For examples, please refer sample MEAD templates available at `GitHub <https:
//github.com/openstack/apmec/tree/master/samples/tosca-templates/NANYD>`_.

Node types
----------
For Apmec purposes a NFYD only includes **Forwarding Path**.  In a full
Network Services Descriptor (NSD), it would include information about each
MEAD as well.  However until that implementation, MEAD is described in a
separate template.  Only a single Forwarding Path is currently supported.
**node_templates** is a child of **topology_template**.

Forwarding Path
---------------
Forwarding Path is a required entry in a NFYD.  It describes the chain as
well as the classifier that will eventually be created to form a path
through a set of MEAs.

:type:
    tosca.nodes.mec.FP.Apmec
:properties:
    Describes the properties of a FP.  These include id (path ID), policy
    (traffic match policy to flow through the path), and path (chain of
    MEAs/Connection Points). A complete list of NFY properties currently
    supported by Apmec are listed `here <https://github
    .com/openstack/apmec/blob/master/apmec/
    tosca/lib/apmec_mec_defs.yaml>`_ under **properties** section of
    **tosca.nodes.mec.FP.Apmec** field.

Specifying FP properties
^^^^^^^^^^^^^^^^^^^^^^^^
An example FP shown below:

::

  node_templates:

    Forwarding_path1:
      type: tosca.nodes.mec.FP.Apmec
      description: creates path (CP11->CP12->CP32)
      properties:
        id: 51
        policy:
          type: ACL
          criteria:
            - network_src_port_id: 640dfd77-c92b-45a3-b8fc-22712de480e1
            - destination_port_range: 80-1024
            - ip_proto: 6
            - ip_dst_prefix: 192.168.1.2/24
        path:
          - forwarder: MEA1
            capability: CP1
          - forwarder: MEA2
            capability: CP2

id
""
ID from the above example is used to identify the path.  This path ID will
be used in future implementations of Network Service Header (NSH) to
identify paths via the Service Path Identifier (SPI) attribute.

policy
""""""
Policy defines the type of match policy that will be used to distinguish
which traffic should enter this Forwarding Path.  The only currently
supported type is ACL (access-list).
Please reference `tosca.mec.datatypes.aclType
<https://github.com/openstack/apmec/blob/master/apmec/tosca/lib/
apmec_mec_defs.yaml>`_ under **properties** section for more information on
supported match criteria.

path
""""
Path defines an ordered list of nodes to traverse in a Forwarding Path.  Each
node is really a logical port, which is defined in the path as a Connection
Point (CP) belonging to a specific MEAD.  It is not necessary at NFYD
creation time to have predefined these MEADs used in the path.  They may be
created later.  Up to 2 CPs may be listed (in order) per MEAD.  If 2 are
listed, the first will be considered the ingress port for traffic and the
second will be the egress.  If only one port is provided, then it will be
interpreted as both the ingress and egress port for traffic.


Groups
------
In Apmec and TOSCA, the NFY itself is described in this section.  There
may only be a single NFY described in each NFYD under this section.

NFY
-----
NFY maps the Forwarding Path to other node types defined in the properties
section.

:type:
    tosca.groups.mec.NFY
:properties:
    Describes the properties of a NFY.  These include vendor, version,
    dependent_virtual_link, connection_points, constituent_meas.
    . A complete list of NFY properties currently
    supported by Apmec are listed in `TOSCA <http://docs.oasis-open
    .org/tosca/tosca-mec/v1.0/csd03/tosca-mec-v1.0-csd03
    .html#_Toc447714727>`_.
:members:
    A list of Forwarding Paths which belong to this NFY.  At the moment
    only one is supported.

Specifying NFY properties and members
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
An example NFY shown below:

::

  groups:
    NFY1:
      type: tosca.groups.mec.NFY
      description: HTTP to Corporate Net
      properties:
        vendor: apmec
        version: 1.0
        number_of_endpoints: 2
        dependent_virtual_link: [VL1,VL2,VL3]
        connection_point: [CP1,CP2]
        constituent_meas: [MEA1,MEA2]
      members: [Forwarding_path1]

number_of_endpoints
"""""""""""""""""""
Number of CPs included in this NFY.

dependent_virtual_link
""""""""""""""""""""""
The Virtual Link Descriptors (VLD) that connect each MEA/CP in this
Forwarding Graph.

connection_point
""""""""""""""""
List of Connection Points defined in the Forwarding Path.

constituent_meas
""""""""""""""""
List of MEAD names used in this Forwarding Graph (also defined in Forwarding
Path).

Summary
-------
To summarize NFYD is written in YAML and describes a NFY topology. It is
composed of a Forwarding Path and a NFY.  A full NFYD is shown below:

::

  tosca_definitions_version: tosca_simple_profile_for_mec_1_0_0

  description: Sample NFY template

  topology_template:
    description: Sample NFY template

    node_templates:

      Forwarding_path1:
        type: tosca.nodes.mec.FP.Apmec
        description: creates path (CP12->CP22)
        properties:
          id: 51
          policy:
            type: ACL
            criteria:
              - network_src_port_id: 640dfd77-c92b-45a3-b8fc-22712de480e1
              - destination_port_range: 80-1024
              - ip_proto: 6
              - ip_dst_prefix: 192.168.1.2/24
          path:
            - forwarder: MEAD1
              capability: CP12
            - forwarder: MEAD2
              capability: CP22

    groups:
      NFY1:
        type: tosca.groups.mec.NFY
        description: HTTP to Corporate Net
        properties:
          vendor: apmec
          version: 1.0
          number_of_endpoints: 2
          dependent_virtual_link: [VL12,VL22]
          connection_point: [CP12,CP22]
          constituent_meas: [MEAD1,MEAD2]
        members: [Forwarding_path1]
