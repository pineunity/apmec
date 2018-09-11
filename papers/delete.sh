ostack=/home/compute2/devstack

cd $ostack
source userrc_early

vnfd_id=$(tacker vnfd-list | grep vnfd | awk '{print $2}')


tacker vnfd-delete $vnfd_id

