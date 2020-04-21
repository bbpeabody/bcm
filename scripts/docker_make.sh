#!/bin/bash

usage="usage: $0 {-c|--cov-build} {-s|--signed} [thor] [debug|release|all|clean]"

docker_container="bldr"
thor_dir='/root/git/netxtreme/main/Cumulus/firmware/THOR'
#chimp_dir='/git/netxtreme/main/Cumulus/firmware/ChiMP/bootcode'
cov_script=$thor_dir/cov
PATH=/usr/bin:/usr/local/bin:/usr/local/bin:$PATH
signed_user=bp892475

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
    #chimp)
    #    build_dir=$chimp_dir
    #    cmd="./make_cmba_afm_pkg.sh"
    #    ;;
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
            #chimp)
            #    cmd="        ./make_cmba_afm_pkg.sh release nvram_lkup_index qos_cfg_profiles"
            #    cmd="$cmd && ./make_stratus_afm_pkg.sh release nvram_lkup_index qos_cfg_profiles"
            #    cmd="$cmd && ./make_sr_afm_pkg.sh release nvram_lkup_index qos_cfg_profiles"
            #    cmd="$cmd && ./make_ns3_pkg.sh release nvram_lkup_index qos_cfg_profiles"
            #    ;;
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
    signed_input='cat ~/sign.txt | '
else
    signed_input=""
fi

eval time \
     $signed_input \
     docker run --volume ~:/root:delegated \
                --workdir $build_dir \
                --entrypoint $cmd \
                --env USER=$signed_user \
                -i \
                --hostname $docker_container \
                $docker_container \
                $args
