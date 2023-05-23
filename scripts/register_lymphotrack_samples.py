import os
import re
import json
from copy import deepcopy
from pymongo import MongoClient
import datetime
import logging
import argparse
import colorlog



class RegisterLymphotrackSamples():

    DEFAULT_RUNDIR = "/data/lymphotrack/runs"
    DEFAULT_RESULTSDIR = "/data/lymphotrack/results/lymphotrack_dx"
    DEFAULT_REGISTERED_FILE_OUT_NAME = "lymphotrack_samples_registered"
    DEFAULT_QC_REGISTERED_FILE_OUT_NAME = "lymphotrack_qc_registered"
    SAMPLESHEET_KEYWORDS = ['lymphotrack', 'Lymphotrack', 'LYMPHOTRACK', 'SHM', 'shm', 'Shm', 'TRB', 'IGK', 'IGH']
    EXCLUDE_SAMPLE_TAGS = ['POS', 'NEG', 'IGHSHM']
    
    def __init__(self, RUNDIR=None, RUN=None, RESULTSDIR=None):
        if RUNDIR is None:
            self.RUNDIR = RegisterLymphotrackSamples.DEFAULT_RUNDIR
        else:
            self.RUNDIR = RUNDIR

        self.RUN = RUN
        if self.RUN is not None:
            self.run_folder_full_path = f"{self.RUNDIR}/{self.RUN}"
            self.lymphotrack_registered_file, self.lymphotrack_qc_registered_file, self.sample_sheet, self.demux_stats_json = self.get_filenames(self.run_folder_full_path)
        else:
            self.run_folder_full_path = self.lymphotrack_registered_file = self.lymphotrack_qc_registered_file = self.sample_sheet = self.demux_stats_json = None

        if RESULTSDIR is None:
            self.RESULTSDIR = RegisterLymphotrackSamples.DEFAULT_RESULTSDIR
        else:
            self.RESULTSDIR = RESULTSDIR

        
        self.db_connection = MongoDBConnection() # Create an instance of MongoDBConnection

        self.logger = logging.getLogger(__name__) # Create a logger instance
        

    def to_register(self) -> None|dict:

        is_lymphotrack_registered = RegisterLymphotrackSamples.get_file_exists_status(self.lymphotrack_registered_file)

        if not is_lymphotrack_registered:
            samplesheet_exits, is_samplesheet_valid = self.check_valid_file(self.sample_sheet)

        else:
            self.logger.warning(f"Samples are already registered for the runId {self.RUN}.")
            samplesheet_exits = is_samplesheet_valid = False

        if samplesheet_exits and is_samplesheet_valid:
            self.logger.info(f"Samples from the run {self.RUN} will be registered in the database")

            sample_sheet_data, sequencer = self.get_samplesheet_data(self.sample_sheet)
            self.logger.debug(f"Samples from the run {self.RUN}, samplesheet data: {sample_sheet_data}")
            self.logger.debug(f"Samples from the run {self.RUN}, sequencer Info: {sequencer}")

            sample_elements = self.extract_sample_elements(sample_sheet_data)
            self.logger.debug(f"Samples from the run {self.RUN}, sample elements data: {sample_elements}")

            demux_stats, run_number, flowcell = self.get_demux_stats()

            if demux_stats is not None:
                touch(self.lymphotrack_qc_registered_file)

            self.logger.debug(f"Samples from the run {self.RUN}, demux stats data: {demux_stats}")
            return self.get_documents_lists(demux_stats, sample_elements, self.RUN, self.run_folder_full_path, run_number, flowcell, sequencer)
        
        elif not is_lymphotrack_registered and not samplesheet_exits:
            self.logger.info(f"Sample Sheet does not exist for the runId {self.RUN}. Still waiting for the status..")
            return None
        
        elif samplesheet_exits and not is_samplesheet_valid:
            self.logger.info(f"This run is not valid: {self.RUN}")
            return None



    @staticmethod
    def get_runfolders(RUNDIR=DEFAULT_RUNDIR) -> list:
        run_folders = []
        for entry in os.scandir(RUNDIR):
            if entry.is_dir():
                run_folders.append(entry.name)
        return run_folders

    @staticmethod
    def get_excelfiles(RESULTS=DEFAULT_RESULTSDIR) -> list:
        files = {}
        for root, dirs, filenames in os.walk(RESULTS):
            for filename in filenames:
                if filename.endswith('.xlsm') and not os.path.exists(f"{filename}.registered"):
                    name = filename.replace('.xlsm', '')
                    if name not in files:
                        files[name] = {'excel': f"{root}/{filename}"}
                    else:
                        files[name]['excel'] = f"{root}/{filename}"
                elif filename.endswith('.fastq_indexQ30.tsv') and not os.path.exists(f"{filename}.registered"):
                    name = filename.split('_')[0]
                    if name not in files:
                        files[name] = {'qc': f"{root}/{filename}"}
                    else:
                        files[name]['qc'] = f"{root}/{filename}"
        return files            


    def get_filenames(self, dir) -> tuple:
        return tuple(
            (f"{dir}/{RegisterLymphotrackSamples.DEFAULT_REGISTERED_FILE_OUT_NAME}",
            (f"{dir}/{RegisterLymphotrackSamples.DEFAULT_QC_REGISTERED_FILE_OUT_NAME}"), 
            f"{dir}/SampleSheet.csv", 
            f"{dir}/Data/Intensities/BaseCalls/Stats/Stats.json")
          )


    @staticmethod
    def get_file_exists_status(check_file: str) -> bool:
        return os.path.exists(check_file)
    

    def check_valid_file(self, samplesheet: str) -> bool:
        if os.path.exists(samplesheet) and self.check_string_in_file(samplesheet):
            return True, True
        elif os.path.exists(samplesheet) and not self.check_string_in_file(samplesheet):
            return True, False
        elif not os.path.exists(samplesheet):
            return False, False


    def check_string_in_file(self, file_path):
        with open(file_path, 'r') as file:
            for line in file:
                if any(search_string in line for search_string in RegisterLymphotrackSamples.SAMPLESHEET_KEYWORDS):
                        return True
        return False
            
    def get_samplesheet_data(self, samplesheet: str) -> list:
        lines = []
        found_header = False
        instrument_type = None

        with open(samplesheet, 'r') as samplesheet_file:
            for line in samplesheet_file:
                if not found_header:
                    if line.startswith('Instrument Type'):
                        instrument_type = line.split(',')[1]
                    if line.startswith("Sample_ID,Sample_Name"):
                        found_header = True
                else:
                    lines.append(line.strip())
        return lines, instrument_type


    def extract_sample_elements(self, samplesheet_data: str) -> dict:

        sample_elements_dict = {}
        clarity_id_pattern = r"(?:.*[-_]|^)(CMD[A-Za-z0-9]+)([-_]?.*)" #it can start with any letters and not just CMD [A-Z]{3}\d+A\d+ 
        sample_id_pattern = r"\d+-\d+[-_]?.*"

        for sample_line in samplesheet_data:
            sample_line_list = sample_line.split(',')
            sample_id = sample_line_list[0]
            sample_id_match = re.match(sample_id_pattern, sample_id)
            sample_description = sample_line_list[9]

            consider_sample_line = False

            clarity_id = re.search(clarity_id_pattern, sample_description).group(1).rstrip('-_') if re.search(clarity_id_pattern, sample_description) else None 

            if any(tag in sample_id or tag in sample_description for tag in RegisterLymphotrackSamples.SAMPLESHEET_KEYWORDS) and clarity_id is not None:
                consider_sample_line = True

            if sample_description.lower().startswith("lymphotrack"):
                sample_description = sample_description[12:]
            elif sample_description.lower().endswith("lymphotrack"):
                sample_description = sample_description[:-12]       


            if consider_sample_line:
                if sample_id_match:
                    sample_name = sample_id
                elif not sample_id_match:
                    sample_name = sample_description.replace(clarity_id, '')
                    sample_name = sample_name.strip('_')
                    sample_name = sample_name.strip('-')

                if sample_name not in sample_elements_dict.keys():
                    sample_elements_dict[sample_name] =  [clarity_id]

        return sample_elements_dict


    def get_demux_stats(self):

        try:
            with open(self.demux_stats_json, 'r') as json_file:
                json_data = json.load(json_file)
        except FileNotFoundError:
            json_data = None
            
        if json_data is not None:
            _run_id = json_data['RunId']
            _run_number = json_data['RunNumber']
            _flowcell = json_data['Flowcell']
            _conversion_stats = json_data['ConversionResults']

            demux_stats_dict = {}
            for sample_lanes in _conversion_stats:
                for sample_stats in sample_lanes['DemuxResults']:
                    #{'SampleId': '1262-21-val3-230123_SHM', 'SampleName': '1262-21-val3-230123_SHM', 'IndexMetrics': [{'IndexSequence': 'CGATGT', 'MismatchCounts': {'0': 290403, '1': 3522}}], 'NumberReads': 293925, 'Yield': 176942850, 'ReadMetrics': [{'ReadNumber': 1, 'Yield': 88471425, 'YieldQ30': 81961040, 'QualityScoreSum': 3217198198, 'TrimmedBases': 360673}, {'ReadNumber': 2, 'Yield': 88471425, 'YieldQ30': 62979276, 'QualityScoreSum': 2809619087, 'TrimmedBases': 446846}]}
                    if sample_stats['SampleId'] not in demux_stats_dict.keys():
                        demux_stats_dict[sample_stats['SampleId']] = 0
                
                    demux_stats_dict[sample_stats['SampleId']] += sample_stats['Yield']
        else:
            demux_stats_dict = _run_number = _flowcell = None

        return demux_stats_dict, _run_number, _flowcell

    
    def get_documents_lists(self, stats_dict, clarity_ids_dict, runfolder, runfolder_path, run_number, flowcell, sequencer_type) -> list[dict]:

        merged_dict = deepcopy(clarity_ids_dict)
        for key, value in merged_dict.items():
            if stats_dict is not None and key in stats_dict.keys():
                merged_dict[key].append(stats_dict[key])
            else:
                merged_dict[key].append(0)
            
        to_be_registered_list_samples = [] 

        for key in merged_dict.keys():
            _dict_samples = {
                        'name': key.replace('_', '-').strip(), 
                        'clarity_id': merged_dict[key][0].strip(), 
                        'run_id': runfolder.strip(),
                        'run_number': run_number,
                        'run_path': runfolder_path.strip(),
                        'flowcell_id': flowcell.strip() if flowcell is not None else None,
                        'sequencer': sequencer_type.strip() if sequencer_type is not None else None,
                        'subtype': '', 
                        'assay': 'lymphotrack', 
                        'lymphotrack_excel': False,
                        'lymphotrack_excel_path': '', 
                        'lymphotrack_qc': False,
                        'lymphotrack_qc_path' : '',
                        'vquest': False, 
                        'report': False,
                        'total_raw_reads': merged_dict[key][1],  
                        'total_reads': '',
                        'q30_reads': '',
                        'q30_per': '',
                        'status': '',
            }

            to_be_registered_list_samples.append(_dict_samples)

        return to_be_registered_list_samples
    

    def register_to_db(self, sample_docs, db, collection_name, overwrite):

        self.db_connection.connect(db) # Create a MongoDB connection with default db
        # Get the client and database objects
        client = self.db_connection.get_client()
        db = self.db_connection.get_db()
        date_now = datetime.datetime.now()
        count = 0
        try:
            for sample_doc in sample_docs:
                sample_doc['date_added'] = date_now
                self.db_connection.insert_data(collection_name, sample_doc, overwrite)
                count += 1
            return True, count
        except:
            return False, count
        


    def update_qc_values(self, collection_name, docs, stats, runnumber):

        stats_copy = {}
        for sample in stats.keys():
            stats_copy[sample.replace('_', '-')] = stats[sample]
        
        self.logger.debug(f"Stats file for the run {self.RUN}: {stats_copy}\n")

        docs_count = len(docs)
        update_count = 0
        samples_not_match = []

        try:
            for doc in docs:
                if doc['name'] in stats_copy.keys():
                    target = {'_id': doc['_id']}
                    update_instructions = {"$set": {'total_raw_reads': stats_copy[doc['name']], 'run_number': runnumber}}
                    self.logger.debug(f"Update instrctions are: {target} {update_instructions}")                
                    self.db_connection.update_data(collection_name, target, update_instructions)

                    update_count += 1
                else:
                    samples_not_match.append(doc['name'])
            
            success = True                    
        except:
            success = False 
        
        if docs_count > update_count:
            self.logger.error("All the documents are not updated, there might be some sample names discrepancy")
            self.logger.debug(f"Samples which are not updated for some reason, {samples_not_match}")            
            self.logger.debug(f"Check the stats file for more information, {self.demux_stats_json}")
            success = False

        return success


    def update_files(self, collection_name, docs, files_dict, update_file):
        docs_count = len(docs)
        update_count = 0
        sample_not_updated = []
        try:
            for doc in docs:
                if doc['name'] in files_dict.keys():
                    if update_file == 'excel':
                        file = files_dict[doc['name']]['excel'] if 'excel' in files_dict[doc['name']].keys() else None
                        update_instructions = {"$set": {'lymphotrack_excel_path': file, 'lymphotrack_excel': True }}
                    elif update_file == 'qc':
                        file = files_dict[doc['name']]['qc'] if 'qc' in files_dict[doc['name']].keys() else None
                        update_instructions = {"$set": {'lymphotrack_qc_path': file, 'lymphotrack_qc': True }}
                    
                    target = {'_id': doc['_id']}
                    if file is not None:
                        self.db_connection.update_data(collection_name, target, update_instructions)
                        touch(f"{file}.registered")
                        self.logger.debug(f"File updating for the query {target}: {update_instructions}")
                        update_count += 1
                else:
                    sample_not_updated.append(doc['name'])
            
            success = True
        except:
            success = False
        
        if docs_count > update_count:
            self.logger.error(f"All the documents are not updated, there might be some result {update_file} files are not available... Will try again in after a while..")
            self.logger.debug(f"Samples which are not updated for unavailability result {update_file}, {sample_not_updated}")   
            success = False

        return success




class MongoDBConnection():

    def __init__(self, host='localhost', port=27017):
        self.host = host
        self.port = port
        self.client = None
        self.db = None
        self.logger = logging.getLogger(__name__)


    def connect(self, db):
        self.client = MongoClient(self.host, self.port)
        self.db = self.client[db]


    def get_client(self):
        return self.client
    

    def get_db(self):
        return self.db
    
    def get_docs(self, collection_name, query):
        collection = self.db[collection_name]
        cursor = collection.find(query)
        return list(cursor)
    

    def insert_data(self, collection_name, data, overwrite):
        collection = self.db[collection_name]
        data_find = {'name': data['name']}

        if self.is_existing(collection, data_find):
            self.logger.error(f"Data already exists for the sample {data_find['name']} in {collection_name}")
            if overwrite:
                existing_doc = collection.find_one(data_find)
                _id = existing_doc['_id']
                self.logger.warning(f'Overwrite is set to True, existing data will be replaced')
                self.drop_document(_id, collection)
                self.logger.info(existing_doc)
            else:
                return

        collection.insert_one(data)
        self.logger.debug("Data inserted successfully.")


    def update_data(self, collection_name, target, update_data):
        collection = self.db[collection_name]
        collection.find_one_and_update(target, update_data)


    def drop_document(self, _id, collection):
        collection.delete_one({'_id': _id})


    def is_existing(self, collection, doc_filter):
        return collection.find_one(doc_filter) is not None
    


class ColorfulFormatter(logging.Formatter):
    def format(self, record):
        log_fmt = '%(asctime)s - %(log_color)s%(levelname)-8s%(reset)s %(log_color)s%(message)s'
        colors = {
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white'
        }
        formatter = colorlog.ColoredFormatter(log_fmt, log_colors=colors)
        return formatter.format(record)


def configure_logging(log_level, log_file):
    log_format = "%(asctime)s - %(levelname)s - %(message)s"

    # Create a file handler with colorful formatter
    file_handler = logging.FileHandler(log_file)
    file_formatter = ColorfulFormatter(log_format)
    file_handler.setFormatter(file_formatter)

    # Create a stream handler with colorful formatter
    stream_handler = logging.StreamHandler()
    stream_formatter = ColorfulFormatter(log_format)
    stream_handler.setFormatter(stream_formatter)

    # Add both handlers to the logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger


def touch(file_path):
    try:
        os.mknod(file_path)
    except FileExistsError:
        pass


def parse_arguments():
    parser = argparse.ArgumentParser(description="Register Lymphotrack Samples")
    parser.add_argument("--base-runDir", default=RegisterLymphotrackSamples.DEFAULT_RUNDIR, help=f"Set the log file path (default: {RegisterLymphotrackSamples.DEFAULT_RUNDIR}")
    parser.add_argument("--base-resultsDir", default=RegisterLymphotrackSamples.DEFAULT_RESULTSDIR, help=f"Set the log file path (default: {RegisterLymphotrackSamples.DEFAULT_RUNDIR}")
    parser.add_argument("--db-host", default="localhost", help=f"set mongo db host (default: localhost)")
    parser.add_argument("--db-port", default="27017", help=f"set mongo db port (default: 27017)")
    parser.add_argument("--db-name", default="cll_genie", help=f"set mongo db name (default: cll_genie)")
    parser.add_argument("--collection-name", default="samples", help=f"set mongo db collection name (default: samples)")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        default="INFO", help="Set the log level (default: INFO)")
    parser.add_argument("--log-file", default=f"{os.path.dirname(os.path.abspath(__file__))}/logs.log", help=f"Set the log file path (default: {os.path.dirname(os.path.abspath(__file__))}/logs.log)")
    parser.add_argument("--overwrite-db", default=False, help=f"Will overwrite existing data in the database and register again as a fresh copy if set to True (default: False)")
    parser.add_argument("--update-excel", default=False, help=f"Will update the excel paths in the database if set to True (default: False)")

    return parser.parse_args()


if __name__ == '__main__':

    #get args
    args = parse_arguments()

    # Configure logging
    logger = configure_logging(args.log_level, args.log_file)


    if not args.update_excel:
        run_folders = RegisterLymphotrackSamples.get_runfolders(RUNDIR=args.base_runDir)

        for run in run_folders:
            run_instance = RegisterLymphotrackSamples(RUNDIR=args.base_runDir, RUN=run)
            logger.info(f"Processing {run_instance.run_folder_full_path} ...")
            samples_docs = run_instance.to_register()
            logger.debug(f"Samples from the run {run}, sample docs: {json.dumps(samples_docs)}")
            if samples_docs is not None:
                success, sample_count = run_instance.register_to_db(samples_docs, args.db_name, args.collection_name, args.overwrite_db)
                if success:
                    logger.info(f"Data inserted successfully from the run: {run}. Number of samples added: {sample_count}")
                    touch(f"{args.base_runDir}/{run}/{RegisterLymphotrackSamples.DEFAULT_REGISTERED_FILE_OUT_NAME}")
                else:
                    logger.error(f"Data insertion failed from the run: {run}. Number of samples added: {sample_count}")
            
            is_lymphotrack_qc_registered = run_instance.get_file_exists_status(f"{run_instance.lymphotrack_qc_registered_file}")
            is_lymphotrack_sample_registered = run_instance.get_file_exists_status(f"{run_instance.lymphotrack_registered_file}")
            demux_stats_json_exists = run_instance.get_file_exists_status(f"{run_instance.demux_stats_json}")
            if not is_lymphotrack_qc_registered and is_lymphotrack_sample_registered:
                logger.info(f"Raw data QC is not registered for the samples from the run: {run}. Attempting to update the qc values")
                if demux_stats_json_exists:
                    logger.info(f"Stats json for the run: {run} is available on the server now...")
                    demux_stats, run_number, flowcell = run_instance.get_demux_stats()
                    run_instance.db_connection.connect(args.db_name)
                    query = {'run_id': run}
                    db_docs = run_instance.db_connection.get_docs(args.collection_name, query)
                    update_status = run_instance.update_qc_values(args.collection_name, db_docs, demux_stats, run_number)
                    if update_status:
                        touch(run_instance.lymphotrack_qc_registered_file)
                else:
                    logger.error(f"Stats json for the run: {run} is not available on the server now... Will attempt to update after a while.")

            logger.info(f"Finished proccessing the run: {run}\n")
    
    else:
        results_instance = RegisterLymphotrackSamples(RESULTSDIR=args.base_resultsDir)
        print(results_instance.RESULTSDIR)
        files = RegisterLymphotrackSamples.get_excelfiles(RESULTS=args.base_resultsDir)
        #print(files)
        results_instance.db_connection.connect(args.db_name)

        excel_query = {'lymphotrack_excel': False}
        qc_query = {'lymphotrack_qc': False}

        samples_docs_excel = results_instance.db_connection.get_docs(args.collection_name, excel_query)
        update_status_excel = results_instance.update_files(args.collection_name, samples_docs_excel, files, 'excel')
        samples_docs_qc = results_instance.db_connection.get_docs(args.collection_name, qc_query)
        update_status_qc = results_instance.update_files(args.collection_name, samples_docs_qc, files, 'qc')

