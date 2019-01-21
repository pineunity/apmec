# Things to do:
# Create a loop to:
# Call requests function
# Afterwards, the samples are created. Then execute 2 approaches:
# For coop, call only apmec api to create mes
# For sepa, call apmec api to create mea and call tacker api to create NSs


COUNT=20


# call source openrc admin admin


ostack=/home/ostack/tung-apmec/00-latest-eval/devstack
sample_dir=/opt/stack/apmec/samples/tosca-templates/evaluation/papers

cd $ostack
source openrc admin admin
cd $sample_dir


count=1
while [ $count -le $COUNT ]

do
  # call request function
  sudo python requests.py
  mes_name="meso"
  mes_name+=$count
  ns_name="nso"
  ns_name+=$count
  mea_name="meao"
  mea_name+=$count
  # determine the execution time
  starting_time=$(date +%s%N)
  #apmec mes-create --mesd-template $sample_dir/coop-mesd.yaml $mes_name
  mes_id=$(apmec mes-create --mesd-template $sample_dir/coop-mesd.yaml $mes_name | grep -w id | awk '{print $4}')
  exec_time=$((($(date +%s%N) - $starting_time)/1000000))
  echo $exec_time
  echo $mes_id
  pros_starting_time=$(date +%s%N)
  #bash pros_time.sh $mes_id
  bash active_time.sh
  service_time=$((($(date +%s%N) - $pros_starting_time)/1000000))
  echo $service_time
  # check whether the MES is active
  sleep 10
  count=$(( $count+1 ))
done

exit 1

