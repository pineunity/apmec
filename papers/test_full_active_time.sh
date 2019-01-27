ostack=/home/ostack/tung-apmec/00-latest-eval/devstack
sample_dir=/opt/stack/apmec/samples/tosca-templates/evaluation/papers

cd $ostack
source openrc admin admin

cd $sample_dir

apmec mes-create --mesd-template $sample_dir/coop-mesd.yaml mes1

check="False"
crd_check="False"
newly_crdNS=''
upd_check="False"
upd_NS=''

while [ "$check" == "False" ]

do
mes_status=$(apmec mes-list | grep mes | awk '{print $8}')

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
echo $ns_id

fi

fi

if [[ "$upd_check" == "False"  ]]; then

if [[ "$mes_status" == *"PENDING_UPDATE"*  ]]; then
mes_id=$(apmec mes-list | grep "PENDING_UPDATE" | awk '{print $2}')
ns_id=$(apmec mes-show $mes_id | grep mes_mapping | awk -F'[][]' '{print $2}')    # Find the updated NS
upd_NS=$ns_id
upd_check="True"
echo $ns_id

fi

fi

done

if [[ "$newly_crdNS" != ""  ]]; then

eval eval_ns_id=$newly_crdNS

bash newly_crd_chain_pros.sh $eval_ns_id

echo "SFC created is finished..."

fi


if [[ "$newly_crdNS" != ""  ]]; then

eval eval_ns_id=$upd_NS

bash upd_chain_pros.sh $eval_ns_id

echo "SFC created is finished..."
fi


exit 1