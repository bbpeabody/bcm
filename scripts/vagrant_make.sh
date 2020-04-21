#!/bin/bash

usage="usage: $0 {-c|--cov-build} {-s|--signed} [thor|chimp] [debug|release|all|clean]"
thor_dir='/git/netxtreme/main/Cumulus/firmware/THOR'
chimp_dir='/git/netxtreme/main/Cumulus/firmware/ChiMP/bootcode'
cov_script=$thor_dir/cov
PATH=/usr/bin:/usr/local/bin:/usr/local/bin:$PATH

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
        cmd="./make_thor_pkg.sh RV=B"
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
    cmd="$cmd CRID=0001"
fi

case $2 in
    debug)
        cmd="$cmd debug"
        ;;
    release)
        cmd="$cmd release"
        ;;
    all)
        case $1 in
            thor)
                # Default Thor to release if 'all' option used
                cmd="$cmd release"
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
        cmd="$cov_script clean"
        ;;
    *)
        echo "Invalid second argument $2"
        echo $usage
        exit 1
        ;;
esac

if [ "$cov" = true ] ; then
    # Do a build and generate coverity meta-data
    cmd="cd $build_dir && $cov_script build '$cmd'"
else
    cmd="cd $build_dir && $cmd"
fi
if [ "$signed" = true ] ; then
    cmd="$cmd < ~/sign.txt"
fi
cmd="time sh -c \"${cmd}\""

# Make sure vagrant machine is up
echo "Running \"$cmd\" on vagrant VM..."
pushd ~/git/bcm/vagrant 1> /dev/null
vagrant status | grep running &> /dev/null || vagrant up

# SSH to vagrant machine and make THOR
vagrant ssh -- "$cmd"

popd 1>/dev/null
