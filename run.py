from cll_genie import create_app
from version import __version__

cll_app = create_app()
if cll_app.config["APP_VERSION"] is None:
    cll_app.config["APP_VERSION"] = __version__

if __name__ == "__main__":
    # cll_app.run() # Main
    cll_app.run(debug=True, host="0.0.0.0", port=5000)  # Dev


""" docker network error

docker stop $(docker ps -a -q); docker rm $(docker ps -a -q); docker volume rm $(docker volume ls -qf dangling=true)

docker network rm $(docker network ls -q)

sudo lsof -nP | grep LISTEN

sudo kill -9 1548

6428-22-val3-230123-SHM_S6_L001_001_combined.fastq_indexQ30.tsv
mongoimport --db='cll_genie' --collection='samples' --file='/home/ramsainanduri/Pipelines/Web_Developement/Main/cll_genie/data/Excelfile_post_analysis/sample_data.json'
mongo cll_genie --eval 'db.samples.find().forEach(function(doc){doc.date_added = new Date(); db.samples.save(doc);});'
"""
