#!/bin/bash

pushd 2> /dev/null

usage="usage: $0 [thor|chimp] [files]"
thor_dir="/git/netxtreme/main/Cumulus/firmware/THOR"
chimp_dir="/git/netxtreme/main/Cumulus/firmware/ChiMP/bootcode"
cov_script=$thor_dir/cov

PATH=/usr/bin:/usr/local/bin:/usr/local/bin:$PATH
LOCAL_GIT=/Users/bpeabody/git/netxtreme/
REMOTE_GIT=/git/netxtreme/

case $1 in
     thor)
         build_dir=$thor_dir
         ;;
     chimp)
         build_dir=$chimp_dir
         ;;
     *)
         echo "Invalid argument $1"
         echo $usage
         exit 1
         ;;
esac
shift

cmd=" \
    cd $build_dir && \
    $cov_script da $@ | sed -e \"s|$REMOTE_GIT|$LOCAL_GIT|g\""
# Make sure vagrant machine is up
cd ~/git/bcm/vagrant
vagrant status | grep running &> /dev/null || vagrant up

# SSH to vagrant machine and make THOR
cd ~/git/bcm/vagrant && vagrant ssh -- "$cmd"

popd 2> /dev/null
