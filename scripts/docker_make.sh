#!/bin/bash

usage="usage: $0 {-d [netxtreme_dir]} {-c|--cov-build} {-s|--signed} {--single} [thor|chimp] [debug|release|all|clean]"
my_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
docker_dir="$my_dir/../docker"
repo_dir='/home/$(id -un)/git/netxtreme'

cov=false
signed=false
single=false
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
    -d|--directory)
      repo_dir=$2
      shift 2
      ;;
    --single)
      single=true
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

thor_dir="$repo_dir/main/Cumulus/firmware/THOR"
chimp_dir="$repo_dir/main/Cumulus/firmware/ChiMP/bootcode"
cov_script=$thor_dir/cov
signed_user=bp892475
signed_pwd="$HOME/sign.txt"

case $1 in
    thor)
        build_dir=$thor_dir
        if [ "$single" = true ]; then
            cmd="./make_thor_pkg.sh"
        else
            cmd="./make_thor_dual_pkg.sh"
        fi
        args="RV=B TRUFLOW=yes ENABLE_FWCLI=1"
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

# Temporary hack to disable SPDM
#args="$args SUPPORT_SPDM=0"

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

if [ "$signed" = true ] ; then
    args="$args < /sign.txt"
fi
if [ "$cov" = true ] ; then
    # Do a build and generate coverity meta-data
    args="build '$cmd $args'"
    cmd="$cov_script"
fi

pushd $docker_dir &> /dev/null
time \
  ./run \
    --vdiuser $signed_user \
    --cmd /bin/bash \
    -- \
    -c "cd $build_dir && $cmd $args"
popd &> /dev/null
