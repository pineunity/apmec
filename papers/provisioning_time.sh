# Things to do:
# Create a loop to:
# Call requests function
# Afterwards, the samples are created. Then execute 2 approaches:
# For coop, call only apmec api to create mes
# For sepa, call apmec api to create mea and call tacker api to create NSs


COUNT=50


# call source openrc admin admin
ostack=/home/ostack/tung-apmec/apmec-eval/devstack
sample_dir=/opt/stack/apmec/samples/tosca-templates/evaluation/papers

cd $ostack
source openrc admin admin
cd $sample_dir

count=1
while [ $count -le $COUNT ]

do
  # call request function
  sudo python requests.py
  mes_name="mes"
  mes_name+=$count
  ns_name="ns"
  ns_name+=$count
  mea_name="mea"
  mea_name+=$count
  # determine the execution time
  starting_time = $(date +%s%N)
  apmec mes-create --mesd-template $sample_dir/coop-mesd.yaml $mes_name
  exec_time = $((($(date +%s%N) - $starting_time)/1000000))
  echo $exec_time
  count=$(( $count+1 ))
done

exit 1

