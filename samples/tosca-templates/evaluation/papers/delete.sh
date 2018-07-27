ostack=/home/ostack/tung-apmec/apmec-eval/devstack

cd $ostack
source userrc_early

mea_id=$(apmec mea-list | grep mea | awk '{print $2}')


apmec mea-delete $mea_id
