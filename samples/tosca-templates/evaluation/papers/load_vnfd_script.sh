
# call source openrc admin admin
ostack=/home/ostack/tung-apmec/apmec-eval/devstack
home=/home/ostack
edge1_dir=/opt/stack/apmec/samples/tosca-templates/evaluation/papers/edge1-load
edge2_dir=/opt/stack/apmec/samples/tosca-templates/evaluation/papers/edge2-load

vnfd_edge1=("vnfd11" "vnfd12" "vnfd13" "vnfd21" "vnfd22" "vnfd23" "vnfd31" "vnfd32" "vnfd33" "vnfd41" "vnfd42" "vnfd43" "vnfd51" "vnfd52" "vnfd53" "vnfd61" "vnfd62" "vnfd63")


vnfd_edge2=("vnfd11-edge2" "vnfd12-edge2" "vnfd13-edge2" "vnfd21-edge2" "vnfd22-edge2" "vnfd23-edge2" "vnfd31-edge2" "vnfd32-edge2" "vnfd33-edge2" "vnfd41-edge2" "vnfd42-edge2" "vnfd43-edge2" "vnfd51-edge2" "vnfd52-edge2" "vnfd53-edge2" "vnfd61-edge2" "vnfd62-edge2" "vnfd63-edge2")

cd $ostack
source userrc_early

cd $home

sudo nova-manage cell_v2 discover_hosts

glance image-create --name "ubuntu-xenial" --disk-format qcow2 --container-format bare --min-disk=3 --visibility public --file xenial-server-cloudimg-amd64-disk1.img --progress

openstack keypair create --public-key ~/.ssh/id_rsa.pub mykey

# Connect net0 with router

openstack router add subnet router1 subnet0

count=0
for sample in $edge1_dir/*
do
  vnfd_name=${vnfd_edge1[$count]}
  tacker vnfd-create --vnfd-file $sample $vnfd_name
  (( count++ ))

done

index=0
for sample_edge2 in $edge2_dir/*
do
  vnfd_name=${vnfd_edge2[$index]}
  tacker vnfd-create --vnfd-file $sample_edge2 $vnfd_name
  (( index++ ))

done

exit 1