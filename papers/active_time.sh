
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

all_check="False"

crd_check='False'

newly_crdNS=''

while [ "$check" == "False" ]

do
mes_status=$(apmec mes-list | grep meso | awk '{print $8}')

if [[ "$mes_status" != *"PENDING"*  ]]; then
#echo "Right"
check="True"
fi

if [[ "crd_check" == "False"  ]]; then

if [[ "$mes_status" == *"PENDING_CREATE"*  ]]; then
crd_check="True"
fi

fi


done

echo "Done"

exit 1
