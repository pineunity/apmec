# Things to do:
# Create a loop to:
# Call requests function
# Afterwards, the samples are created. Then execute 2 approaches:
# For coop, call only apmec api to create mes
# For sepa, call apmec api to create mea and call tacker api to create NSs

COUNT=2



# call source openrc admin admin

count=1
while [ $count -le $COUNT ]

do
  # call request function
  sudo python requests.py
  count=$(( $count+1 ))
  mes_name="mes"
  mes_name+=$count
  ns_name="ns"
  ns_name+=$count
  mea_name="mea"
  mea_name+=$count
  # initiate the mes using apmec api
  apmec mes-create --mesd-template sepa-mesd.yaml $mes_name &

  # Initiate the nss and mea using tacker api and apmec api
  apmec mea-create --mead_template sepa-mead.yaml $mea_name &
  tacker ns-create --nsd_template sepa-nsd.yaml $ns_name &



