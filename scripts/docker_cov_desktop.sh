#!/bin/bash

pushd 2> /dev/null

usage="usage: $0 [thor|chimp] [files]"
thor_dir="/root/git/netxtreme/main/Cumulus/firmware/THOR"
chimp_dir="/root/git/netxtreme/main/Cumulus/firmware/ChiMP/bootcode"
cov_script=$thor_dir/cov
docker_container="bldr"

PATH=/usr/bin:/usr/local/bin:/usr/local/bin:$PATH
LOCAL_GIT=/Users/bpeabody/git/netxtreme/
REMOTE_GIT=/root/git/netxtreme/

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

cmd=$cov_script
args="da $@ | sed -e \"s|$REMOTE_GIT|$LOCAL_GIT|g\""

eval \
    time \
    docker run --volume ~:/root:delegated \
               --workdir $build_dir \
               --entrypoint $cmd \
               -i \
               --hostname $docker_container \
               $docker_container \
               $args
