
check="False"

while [ "$check" == "False" ]

do
mes_status=$(apmec mes-list | grep meso | awk '{print $8}')

if [[ "$mes_status" != *"PENDING"*  ]]; then
#echo "Right"
check="True"
fi

done

echo "Done"

exit 1


############################## Test ################################

check="False"

newly_crdNS=""

while [ "$check" == "False" ]

do
mes_status=$(apmec mes-list | grep meso | awk '{print $8}')

if [[ "$mes_status" != *"PENDING"*  ]]; then
#echo "Right"
check="True"
fi

if [[ "$mes_status" == *"PENDING_CREATE"*  ]]; then

mes_id=$(apmec mes-list | grep "PENDING_CREATE" | awk '{print $2}')
ns_id=$(apmec mes-show $mes_id | grep mes_mapping | awk -F'[][]' '{print $2}')
newly_crdNS=$ns_id
echo $ns_id

fi

done

if [[ "$newly_crdNS" != ""  ]]; then

eval eval_ns_id=$newly_crdNS

bash chain_pros.sh $eval_ns_id

fi

echo "Done"

exit 1
