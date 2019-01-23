# Things to do:
# Create a loop to:
# Call requests function
# Afterwards, the samples are created. Then execute 2 approaches:
# For coop, call only apmec api to create mes
# For sepa, call apmec api to create mea and call tacker api to create NSs


COUNT=20

VDU1='VDU1'
VDU2='VDU2'
VDU3='VDU3'

CP1='CP11'
CP2='CP21'
CP3='CP31'

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

# Update port-chain

neutron port-chain-update pc1 --port-pair-group pp2

# get VNF resources

# get vnf_ids

ns_nname='ns1'


vnf_ids=$(tacker ns-show $ns_name | grep -w vnf_ids | awk -F'[][]' '{print $2, $4, $6}')

pp_list=""

for vnf_id in $vnf_ids; do
    #echo $vnf_id
    eval vnf_id=$vnf_id
    tacker vnf-resource-list  $vnf_id
    cp_names=$(tacker vnf-resource-list $vnf_id | grep CP | awk '{print $2}')
    # create port-pair-group here
    for cp_name in $cp_names; do
       cp_id=$(tacker vnf-resource-list $vnf_id | grep $cp_name | awk '{print $4}')
       #echo $cp_id
       pp_name=$cp_name"-"$vnf_id
       pp_list+=$pp_name" "
       neutron port-pair-create $pp_name --ingress $cp_id --egress $cp_id
    done
    # change the ppq since it is duplicated between NSs
    # should be attched to "ns1"
    neutron port-pair-group-create $vnf_id --port-pairs $pp_list
done


neutron port-chain-create pc1 --port-pair-group



