#!/bin/bash

usage="usage: $0 {-c|--cov-build} {-s|--signed} [thor|chimp] [debug|release|all|clean]"
my_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
docker_dir="$my_dir/../docker"
thor_dir='/home/$(id -un)/git/netxtreme/main/Cumulus/firmware/THOR'
chimp_dir='/home/$(id -un)/git/netxtreme/main/Cumulus/firmware/ChiMP/bootcode'
cov_script=$thor_dir/cov
signed_user=bp892475
signed_pwd="$HOME/sign.txt"

cov=false
signed=false
PARAMS=""
while (( "$#" )); do
  case "$1" in
    -c|--cov-build)
      cov=true
      shift 1
      ;;
    -s|--signed)
      signed=true
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
    thor)
        build_dir=$thor_dir
        cmd="./make_thor_pkg.sh"
        args="RV=B"
        ;;
    chimp)
        build_dir=$chimp_dir
        cmd="./make_cmba_afm_pkg.sh"
        ;;
    *)
        echo "Invalid build target: $1"
        echo $usage
        exit 1
        ;;
esac

if [ "$signed" = true ]; then
    args="$args CRID=0001"
fi

case $2 in
    debug)
        args="$args debug"
        ;;
    release)
        args="$args release"
        ;;
    all)
        case $1 in
            thor)
                # Default Thor to release if 'all' option used
                args="$args release"
                ;;
            chimp)
                cmd="        ./make_cmba_afm_pkg.sh release nvram_lkup_index qos_cfg_profiles"
                cmd="$cmd && ./make_stratus_afm_pkg.sh release nvram_lkup_index qos_cfg_profiles"
                cmd="$cmd && ./make_sr_afm_pkg.sh release nvram_lkup_index qos_cfg_profiles"
                cmd="$cmd && ./make_ns3_pkg.sh release nvram_lkup_index qos_cfg_profiles"
                ;;
        esac
        ;;
    clean)
        if [ "$cov" = true ] ; then
            echo $usage
            echo "Error: -c|--cov-build not valid with clean" >&2
            exit 1
        fi
        cmd="$cov_script"
        args="clean"
        ;;
    *)
        echo "Invalid second argument $2"
        echo $usage
        exit 1
        ;;
esac

if [ "$cov" = true ] ; then
    # Do a build and generate coverity meta-data
    args="build '$cmd $args'"
    cmd="$cov_script"
fi
if [ "$signed" = true ] ; then
    signed_input="cat $signed_pwd"
else
    signed_input="cat /dev/null"
fi

pushd $docker_dir
time \
$signed_input | \
     ./run \
         --vdiuser $signed_user \
         --cmd /usr/bin/bash \
         -- \
         -c "source /etc/profile.d/env.sh && cd $build_dir && $cmd $args"
popd
