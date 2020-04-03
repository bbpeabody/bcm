#!/bin/bash

pushd 2> /dev/null

usage="usage: $0 [files]"
build_dir="/git/netxtreme/main/Cumulus/firmware/THOR"
PATH=/usr/bin:/usr/local/bin:/usr/local/bin:$PATH

cmd=" \
    cd $build_dir && \
    project_root=\`git rev-parse --show-toplevel\` && \
    echo \$project_root && \
    cov-run-desktop --scm-project-root \$project_root \
                    --set-new-defect-owner false \
                    --dir coverity \
                    --all \
                    --disable-parse-warnings \
                    --disable CONSTANT_EXPRESSION_RESULT \
                    --host cov-ccxsw.broadcom.net \
                    --user bp892475 \
                    --password 17diL3Bert5 \
                    --port 8080 \
                    --stream 'NXT-SUPER int_nxt thor-b0' $@"

# Make sure vagrant machine is up
cd ~/git/bcm/vagrant
vagrant status | grep running &> /dev/null || vagrant up

# SSH to vagrant machine and make THOR
cd ~/git/bcm/vagrant && vagrant ssh -- "$cmd"

popd 2> /dev/null
