#!/bin/bash

pushd 2> /dev/null

usage="usage: $0 [thor|chimp] [files]"
my_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
docker_dir="$my_dir/../docker"
docker_home="/home/$(id -un)"
thor_dir="$docker_home/git/netxtreme/main/Cumulus/firmware/THOR"
chimp_dir="$docker_home/git/netxtreme/main/Cumulus/firmware/ChiMP/bootcode"
cov_script=$thor_dir/cov
local_nxt="$HOME/git/netxtreme/"
docker_nxt="$docker_home/git/netxtreme/"


PATH=/usr/bin:/usr/local/bin:/usr/local/bin:$PATH

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

# Translate filenames from local filesystem to docker filesystem
files=""
for file in $@; do
    docker_file=`realpath $file | sed -e "s|^$local_nxt|$docker_nxt|"`
    files="$files $docker_file"
done

# Command 'cov da'. Translate Coverity results from docker filesystem to local filesystem
cmd=$cov_script
args="da $files | sed -e \"s|$docker_nxt|$local_nxt|g\""

pushd $docker_dir
time \
./run \
    --cmd /bin/bash \
    -- \
    -c "cd $build_dir && $cmd $args"
popd
