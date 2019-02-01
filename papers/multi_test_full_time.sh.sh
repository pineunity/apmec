ostack=/home/ostack/tung-apmec/00-latest-eval/devstack
sample_dir=/opt/stack/apmec/samples/tosca-templates/evaluation/papers

cd $ostack
source openrc admin admin

cd $sample_dir

#apmec mes-create --mesd-template $sample_dir/coop-mesd.yaml mes1

starting_time=$(date +%s%N)

declare -A ns_id_array

check="False"
crd_check="False"
newly_crdNS=''
upd_check="False"
upd_NS=''
pre_vnf_ids=''

while [ "$check" == "False" ]

do
mes_status=$(apmec mes-list | grep meso | awk '{print $8}')

if [[ "$mes_status" != *"PENDING"*  ]]; then
#echo "Right"
check="True"
fi

if [[ "$crd_check" == "False"  ]]; then

if [[ "$mes_status" == *"PENDING_CREATE"*  ]]; then
#echo "Right"
mes_id=$(apmec mes-list | grep "PENDING_CREATE" | awk '{print $2}')
ns_id=$(apmec mes-show $mes_id | grep mes_mapping | awk -F'[][]' '{print $2}')
newly_crdNS=$ns_id
#eval ns_id=$ns_id
#bash chain_pros.sh $ns_id
crd_check="True"
#echo $ns_id

fi

fi

if [[ "$upd_check" == "False"  ]]; then

if [[ "$mes_status" == *"PENDING_UPDATE"*  ]]; then
mes_id=$(apmec mes-list | grep "PENDING_UPDATE" | awk '{print $2}')
ns_ids=$(apmec mes-show $mes_id | grep mes_mapping | awk -F'[][]' '{print $2}')    # Find the updated NS

#declare -A ns_id_array
for raw_ns_id in $ns_ids; do
   eval ns_id=$raw_ns_id
   pre_vnf_ids=$(tacker ns-show $ns_id | grep -w vnf_ids | awk -F'[][]' '{print $2, $4, $6}')
   ns_is_array[$raw_ns_id]=$pre_vnf_id
done
upd_check="True"
#echo $ns_id

fi

fi

if [[ "$upd_check" == "False"  ]]; then

if [[ "$mes_status" == *"PENDING_UPDATE"*  ]]; then
mes_id=$(apmec mes-list | grep "PENDING_UPDATE" | awk '{print $2}')
ns_ids=$(apmec mes-show $mes_id | grep mes_mapping | awk -F'[][]' '{print $2}')    # Find the updated NS

#declare -A ns_id_array
for raw_ns_id in $ns_ids; do
   eval ns_id=$raw_ns_id
   pre_vnf_ids=$(tacker ns-show $ns_id | grep -w vnf_ids | awk -F'[][]' '{print $2, $4, $6}')
   ns_is_array[raw_ns_id]=$pre_vnf_id
done
upd_check="True"
#echo $ns_id

fi

fi

done

ns_creation_time=$((($(date +%s%N) - $starting_time)/1000000))

#echo "NS created is finished..."

if [[ "$crd_check" != "False"  ]]; then

  starting_crd_time=$(date +%s%N)

  for ns_id in $newly_crdNS; do
     echo $ns_id
     eval eval_ns_id=$ns_id
     bash newly_crd_chain_pros.sh $eval_ns_id
  done

  echo "SFC created is finished..."
  sfc_crd_time=$((($(date +%s%N) - $starting_crd_time)/1000000))
  echo $sfc_crd_time
fi


if [[ "$upd_check" != "False"  ]]; then

  starting_upd_time=$(date +%s%N)

  for ns_id in "${!ns_id_array[@]}"; do
       pre_vnf_id=${ns_id_array[$ns_id]}
       eval ns_id=$ns_id
       vnf_ids=$(tacker ns-show $ns_id | grep -w vnf_ids | awk -F'[][]' '{print $2, $4, $6}')

       output_vnf_ids=${vnf_ids//[,]/}

       # Find the origin VNF that can be used to updatet he ppg

       for vnf_id in $output_vnf_ids; do
          if [[ "$pre_vnf_ids" != *"$vnf_id"*  ]]; then
             echo $vnf_id
             eval vnf_id=$vnf_id
             #tacker vnf-show $vnf_id
             bash upd_chain_pros.sh $vnf_id $upd_NS
          fi
       done
  done
  echo "SFC updated is finished..."
  sfc_upd_time=$((($(date +%s%N) - $starting_upd_time)/1000000))
  echo $sfc_upd_time

fi

echo "NS created is finished..."

echo $ns_creation_time

exit 1
