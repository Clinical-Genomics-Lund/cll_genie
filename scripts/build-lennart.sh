#!/bin/bash

# Subpath at which cll_genie_app is hosted:
SCRIPT_NAME='/cll_genie' # For production use only


# Build CDM docker image and start on lennart
version="0.0.1"
# version=$(python -c "import cll_genie_app.__version__; print(__version__.__version__)")

docker build --no-cache --network host --target cll_genie_app -t cll_genie:$version .

set -o allexport; source .env; set +o allexport

docker run \
       -e CLARITY_USER=$CLARITY_USER \
       -e CLARITY_PASSWORD=$CLARITY_PASSWORD \
       -e CLARITY_HOST=$CLARITY_HOST \
       -e DB_HOST=$DB_HOST \
       -e DB_PORT=$DB_PORT \
       -e FLASK_DEBUG=0 \
       -e SCRIPT_NAME=$SCRIPT_NAME \
       -e LOG_LEVEL="INFO" \
       -p 5813:5000 \
       --dns "10.212.226.10" \
       --name cll_genie_app \
       -v /data/lymphotrack/cll_results/:/cll_genie/results/ \
       -v /data/lymphotrack/cll_results_dev/:/cll_genie/results_dev/ \
       -v /data/lymphotrack/results/lymphotrack_dx/:/data/lymphotrack/results/lymphotrack_dx/ \
       -v /data/lymphotrack/logs:/cll_genie/logs \
       -d \
       "cll_genie:$version"


#docker run -e DB_HOST='172.17.0.1' -e CLARITY_USER=$CLARITY_USER -e CLARITY_PASSWORD=$CLARITY_PASSWORD -e CLARITY_HOST=$CLARITY_HOST -e DB_HOST=$DB_HOST -e DB_PORT=$DB_PORT -e FLASK_DEBUG=1 -e SCRIPT_NAME=$SCRIPT_NAME -e LOG_LEVEL="DEBUG" -p 5813:5000 --name cll_genie_app -v /data/lymphotrack/cll_results/:/cll_genie/results/  -v /data/lymphotrack/cll_results_dev/:/cll_genie/results_dev/ -v /data/lymphotrack/results/lymphotrack_dx/:/data/lymphotrack/results/lymphotrack_dx/ -v /data/lymphotrack/logs:/cll_genie/logs "cll_genie:1.0.0"