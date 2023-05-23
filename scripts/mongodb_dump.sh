#!/bin/bash

# Helper script to dump a subset of the mongodb running on lenanrt
# required to run CLL GENIE.
# Run as a part of cll_genie_mongo/build.sh

#mongodb_uri="mtlucmds1.lund.skane.se:27017"
mongodb_uri="localhost:27017"

# mongodb dump of dbs and collections required for running CMD

dbs_to_export="/databases_list.txt"
out_dir="/tmp/mongodump"
log_dir="/tmp/mongo_log"

echo "[START] Dumping CLL_GENIE-related dbs and collections from  $dbs_to_export to $out_dir"

echo "[INFO] Creating outdir: $out_dir"
mkdir -p "$out_dir"

echo "[INFO] Creating logdir: $log_dir"
mkdir -p "$log_dir"

cdm_dump() {
    db="$1"
    collection="$2"
    mongodump -h "$mongodb_uri" -d "$db" -c "$collection" --out "$out_dir"
}

while read line; do
    echo "[INFO] CMD: cdm_dump $line"
    cdm_dump $line
done <  $dbs_to_export

echo "[INFO] Restoring from $out_dir"

#mongod --fork --logpath "$log_dir"
mongorestore --verbose "$out_dir"
#mongod --shutdown

echo "[EXIT] Bye."