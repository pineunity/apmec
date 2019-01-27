ostack=/home/ostack/tung-apmec/00-latest-eval/devstack
sample_dir=/opt/stack/apmec/samples/tosca-templates/evaluation/papers

cd $ostack
source openrc admin admin

cd $sample_dir

check="False"
crd_check="False"
newly_crdNS=''

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

done

if [[ "$newly_crdNS" != ""  ]]; then

eval eval_ns_id=$newly_crdNS

bash chain_pros.sh $eval_ns_id

fi

echo "NS created is finished..."

eval eval_ns_id=$newly_crdNS

bash chain_pros.sh $eval_ns_id

echo "SFC created is finished..."

exit 1