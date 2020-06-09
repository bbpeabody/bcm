#!/bin/bash

rsync -r --exclude "__pycache__/" ~/git/aurora/au-common/aucommon/* root@domino:/root/au-common/aucommon
rsync -r --exclude "__pycache__/" ~/git/aurora/au-common/aucommon/* root@domino:/root/au-common/venv/lib/python3.6/site-packages/aucommon
rsync -r --exclude "__pycache__/" ~/git/aurora/au-common/aucommon/* root@shaper:/root/au-common/aucommon
rsync -r --exclude "__pycache__/" ~/git/aurora/au-common/aucommon/* root@shaper:/root/au-common/venv/lib/python3.6/site-packages/aucommon
ssh root@domino "/root/start_rpyc.sh" &
ssh root@shaper "/root/start_rpyc.sh" &
