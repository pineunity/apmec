ostack=/home/tung/openstack/devstack

cd $ostack

source admin-src.sh

vm_name="vm1"

#vm_id=$(openstack server create --flavor m1.large --image cirros-0.5.2-x86_64-disk --nic net-id=ba93e8a6-92f7-4633-81f5-e6b2feddecff $vm_name | grep -w id | awk '{print $4}')

#echo $vm_id

vm_status=$(openstack server show $vm_name | grep status | awk '{print $4}')

echo $vm_status

if [[ "$vm_status" != *"ACTIVE"*  ]]; then
echo "Right"
fi
