#!/bin/bash

rsync -r --exclude "__pycache__/" ~/git/aurora/au-common/aucommon/* root@rail:/root/au-common/aucommon
rsync -r --exclude "__pycache__/" ~/git/aurora/au-common/aucommon/* root@rail:/root/au-common/venv/lib/python3.6/site-packages/aucommon
rsync -r --exclude "__pycache__/" ~/git/aurora/au-common/aucommon/* root@stile:/root/au-common/aucommon
rsync -r --exclude "__pycache__/" ~/git/aurora/au-common/aucommon/* root@stile:/root/au-common/venv/lib/python3.6/site-packages/aucommon
ssh root@rail "/root/start_rpyc.sh" &
ssh root@stile "/root/start_rpyc.sh" &
