# Things to do:
# Create a loop to:
# Call requests function
# Afterwards, the samples are created. Then execute 2 approaches:
# For coop, call only apmec api to create mes
# For sepa, call apmec api to create mea and call tacker api to create NSs


COUNT=20


# call source openrc admin admin


ostack=/home/ostack/tung-apmec/00-latest-eval/devstack
sample_dir=/opt/stack/apmec/samples/tosca-templates/evaluation/papers

cd $ostack
source openrc admin admin
cd $sample_dir

# get VNF info
tacker vnf-resource-list 48c5df99-e656-4120-afee-5293b1fd3bc2


# Create pp1
neutron port-pair-create pp1 --ingress 20136e5a-8c4f-49f9-98b3-de2b2a71974c --egress 20136e5a-8c4f-49f9-98b3-de2b2a71974c


# Create pp2 of the same VNF
neutron port-pair-create pp2 --ingress 9b8e5888-dd20-47fe-91cd-3381c3a27099 --egress 9b8e5888-dd20-47fe-91cd-3381c3a27099


# Create port-pair-group
neutron port-pair-group-create ppg1 --port-pairs pp1 pp2

# Create port chain without classifier:

neutron port-chain-create pc1  --port-pair-group ppg1


# get vnf_ids

ns_nname='ns1'

vnf_ids=$(tacker ns-show $ns_name | grep -w vnf_ids | awk -F'[{|}]' '{print $4}')