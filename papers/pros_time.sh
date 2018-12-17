
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
