#!/bin/bash

pushd 2> /dev/null

usage="usage: $0 {-c|--cov-build} [debug|release|signed-debug|signed-release|clean]"
build_dir='/git/netxtreme/main/Cumulus/firmware/THOR'
cov=false
PATH=/usr/bin:/usr/local/bin:/usr/local/bin:$PATH

PARAMS=""
while (( "$#" )); do
  case "$1" in
    -c|--cov-build)
      cov=true
      shift 1
      ;;
    --) # end argument parsing
      shift
      break
      ;;
    -*|--*=) # unsupported flags
      echo $usage
      echo "Error: Unsupported flag $1" >&2
      exit 1
      ;;
    *) # preserve positional arguments
      PARAMS="$PARAMS $1"
      shift
      ;;
  esac
done

eval set -- "$PARAMS"

case $1 in
    debug)
        cmd="'./make_thor_pkg.sh RV=B debug'"
        ;;
    release)
        cmd="'./make_thor_pkg.sh RV=B release'"
        ;;
    signed-debug)
        cmd="'./make_thor_pkg.sh CRID=0001 RV=B debug' < ~/sign.txt"
        ;;
    signed-release)
        cmd="'./make_thor_pkg.sh CRID=0001 RV=B release' < ~/sign.txt"
        ;;
    clean)
        if [ "$cov" = true ] ; then
            echo $usage
            echo "Error: -c|--cov-build not valid with clean" >&2
            exit 1
        fi
        cmd="./cov clean"
        #cmd="rm -rf obj THOR* coverity; make clobber"
        ;;
    *)
        echo "Invalid build target: $1"
        echo $usage
        exit 1
        ;;
esac


if [ "$cov" = true ] ; then
    # Do a build and generate coverity meta-data
    #cmd="cd $build_dir && cov-configure --config coverity/coverity_config.xml --compiler arm-none-eabi-gcc --template && cov-build --preprocess-next --dir coverity --config ./coverity/coverity_config.xml $cmd"
    cmd="cd $build_dir && ./cov build $cmd"
else
    cmd="cd $build_dir && $cmd"
fi

cmd="time sh -c \"${cmd}\""

# Make sure vagrant machine is up
cd ~/git/bcm/vagrant
vagrant status | grep running &> /dev/null || vagrant up

# SSH to vagrant machine and make THOR
cd ~/git/bcm/vagrant && vagrant ssh -- "$cmd"

popd 2> /dev/null
