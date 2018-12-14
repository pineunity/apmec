
mes_status="PEND_CREATE"

while [ "$mes_status"  != "ACTIVE" ]

do
mes_status=$(apmec mes-show $1 | grep status | awk '{print $4}')

if [[ "$mes_status" == "ACTIVE"  ]]; then
   echo $mes_status
fi

done

exit 1
