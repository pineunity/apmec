ostack=/home/ostack/tung-apmec/apmec-eval/devstack

cd $ostack
source userrc_early

pc_id=$(neutron port-chain-list | grep pc | awk '{print $2}')

neutron port-chain-delete $pc_id


ppg_id=$(neutron port-pair-group-list | grep ppg | awk '{print $2}')

neutron port-pair-group-delete $ppg_id


pp_id=$(neutron port-pair-list | grep pp | awk '{print $2}')

neutron port-pair-delete $pp_id
