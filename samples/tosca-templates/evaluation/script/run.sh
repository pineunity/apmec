# call source openrc admin admin
ostack=/home/tung/openstack/devstack

cd $ostack
source admin-src.sh
count=0
avail="True"
while [ "$avail" == "True" ]

do
  # call request function
  echo "VM is:"
  echo $count
  vm_name="vm"
  vm_name+=$count
  # vm_name="vm1"
  vm_id=$(openstack server create --flavor m1.large --image cirros-0.5.2-x86_64-disk --nic net-id=ba93e8a6-92f7-4633-81f5-e6b2feddecff $vm_name | grep -w id | awk '{print $4}')
  # vm_status=$(openstack server show $vm_name | grep status | awk '{print $4}')
  # echo "Start to sleep"
  sleep 60
  vm_status=$(openstack server show $vm_name | grep status | awk '{print $4}')
  # echo "Why sleep skip"
  if [[ "$vm_status" != *"ACTIVE"*  ]]; then
  avail="False"
  fi
  count=$(( $count+1 ))
done

echo "Number of VMs:"
count=$(( $count-1 ))
echo $count

exit 1

