#!/bin/bash

# Check number of args
usage="usage: $0 [debug|release|signed-debug|signed-release|clean]"

if [ "$#" -ne 1 ]; then
    echo "$0 expects exactly 1 parameter"
    echo $usage
    exit 1
fi

cmd='cd /git/netxtreme/main/Cumulus/firmware/THOR'

case $1 in
    debug)
        cmd="${cmd} && time ./make_thor_pkg.sh RV=B debug"
        ;;
    release)
        cmd="${cmd} && time ./make_thor_pkg.sh RV=B release"
        ;;
    signed-debug)
        cmd="${cmd} && time ./make_thor_pkg.sh CRID=0001 RV=B debug < ~/sign.txt"
        ;;
    signed-release)
        cmd="${cmd} && time ./make_thor_pkg.sh CRID=0001 RV=B release < ~/sign.txt"
        ;;
    clean)
        cmd="${cmd} && rm -rf obj THOR* && make clobber"
        ;;
    *)
        echo "Invalid parameter: $1"
        echo $usage
        exit 1
        ;;
esac

pushd 2> /dev/null

PATH=/usr/local/bin:/usr/local/bin:$PATH

# Make sure vagrant machine is up
cd ~/git/bcm/vagrant
vagrant status | grep running &> /dev/null || vagrant up

# SSH to vagrant machine and make THOR
ssh -p 2222 -i ~/git/bcm/vagrant/.vagrant/machines/bldr/virtualbox/private_key vagrant@localhost "$cmd"

popd 2> /dev/null
