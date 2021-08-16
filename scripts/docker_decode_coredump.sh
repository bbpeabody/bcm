#!/bin/bash
docker_dir=~/git/bcm/docker
local_decode_coredump_dir=~/git/netxtreme/main/Cumulus/util/corefile_decode
remote_decode_coredump_dir=/home/bpeabody/git/netxtreme/main/Cumulus/util/corefile_decode
cmd="cd $remote_decode_coredump_dir && make && ./decode_coredump"
file=$1
if [ -f "$file" ]; then
    tmp_file="$local_decode_coredump_dir/`basename $file`"
    cp "$file" "$tmp_file"
    shift
    cmd="$cmd `basename $file` $@"
else
    cmd="$cmd $@"
fi
pushd $docker_dir &> /dev/null
./run \
    --cmd /bin/bash \
    -- \
    -c "$cmd"
popd &> /dev/null
if [ -f "$file" ]; then
    rm $tmp_file
fi

if [ -f "$local_decode_coredump_dir/nvram.data" ]; then
    cp "$local_decode_coredump_dir/nvram.data" .
fi
