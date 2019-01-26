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

# get VNF resources

# get vnf_ids

# How to decide to create chain. Following modes:

compare vnfd info between the old one and the new request

- Create new chain. Inputs: chain name
- Update the old chain: chain name and


starting_time=$(date +%s%N)

#ns_name='ns1'

# Make NS name like an input
vnf_ids=$(tacker ns-show $1 | grep -w vnf_ids | awk -F'[][]' '{print $2, $4, $6}')

ppg_list=""

for vnf_id in $vnf_ids; do
    #echo $vnf_id
    pp_list=""
    eval vnf_id=$vnf_id
    tacker vnf-resource-list  $vnf_id
    cp_names=$(tacker vnf-resource-list $vnf_id | grep CP | awk '{print $2}')
    # create port-pair-group here
    for cp_name in $cp_names; do
       cp_id=$(tacker vnf-resource-list $vnf_id | grep $cp_name | awk '{print $4}')
       echo "Create port pair.."
       pp_name="pp-"$cp_name"-"$vnf_id
       pp_list+=$pp_name" "
       neutron port-pair-create $pp_name --ingress $cp_id --egress $cp_id
    done
    # change the ppq since it is duplicated between NSs
    # should be attched to "ns1"
    ppg_name="ppg-"$vnf_id
    ppg_list+=$ppg_name" "

    echo "Create port pair group..."
    ppg_creation="neutron port-pair-group-create "
    prefix=" --port-pair"
    params=""
    for pp_name in $pp_list; do
        params+=$prefix" "$pp_name
    done
    ppg_creation+=$ppg_name$params
    eval $ppg_creation
done

echo $ppg_list

echo "Create port chain..."
#neutron port-chain-create pc1 --port-pair-groups $ppg_list

pc_creation="neutron port-chain-create "
pc_name="pc1"
prefix=" --port-pair-group"
params=""
for ppg_name in $ppg_list; do
    params+=$prefix" "$ppg_name
done
pc_creation+=$pc_name$params
eval $pc_creation

exec_time=$((($(date +%s%N) - $starting_time)/1000000))
echo $exec_time