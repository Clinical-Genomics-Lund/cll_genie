#!/data/bnf/dev/ram/miniconda3/envs/python3.11/bin/python3.11

import os
import re
import json
from copy import deepcopy
from pymongo import MongoClient
import datetime
import logging
import argparse
import colorlog


class LymphotrackRegister:
    """
    Class for registering samples from a Lymphotrack run.

    Attributes:
        DEFAULT_RUN_STATUS_LOG (str): Default path to the run status log file.
        DEFAULT_RUNDIR (str): Default path to the run directory.
        DEFAULT_RESULTSDIR (str): Default path to the results directory.
        DEFAULT_LOGDIR (str): Default path to the log directory.
        DEFAULT_LOGFILE (str): Default log file name.
        RUN_COMPLETED_FILE (str): Name of the file indicating run completion.
        SAMPLESHEET_NAME (str): Name of the sample sheet file.
        SAMPLESHEET_KEYWORDS (list): List of keywords to identify relevant samples.
        EXCLUDE_SAMPLE_TAGS (list): List of sample tags to exclude.
        DEAFAULT_JSON_STATS_FILE (str): Default path to the demux stats JSON file.

    Methods:
        __init__(self, RUNDIR=None, RUN=None, RESULTSDIR=None): Initializes the LymphotrackRegister object.
        get_docs_to_register(self) -> None | dict: Retrieves the documents to register.
        get_runfolders(RUNDIR=DEFAULT_RUNDIR) -> list: Retrieves the list of run folders.
        get_excelfiles(RESULTS=DEFAULT_RESULTSDIR) -> list: Retrieves the list of Excel files.
        get_file_exists_status(check_file: str) -> bool: Checks if a file exists.
        check_valid_file(self, samplesheet: str) -> bool: Checks if a file is valid.
        get_runs_log(logs_file) -> dict: Retrieves the log of runs.
        check_string_in_file(self, file_path) -> bool: Checks if a string is present in a file.
        get_samplesheet_data(self, samplesheet: str) -> list: Retrieves the data from the sample sheet.
        extract_sample_elements(self, samplesheet_data: str) -> dict: Extracts sample elements from the sample sheet data.
        get_demux_stats(self): Retrieves the demux stats.
        get_documents_lists(self, stats_dict, clarity_ids_dict, runfolder_path, run_number, flowcell, sequencer_type) -> list: Retrieves the list of documents to register.
    """

    DEFAULT_RUN_STATUS_LOG = "/data/lymphotrack/logs/register_logs/MiSeq.run_status.log"
    DEFAULT_RUNDIR = "/data/lymphotrack/runs/CLL_Test/runs"
    DEFAULT_RESULTSDIR = "/data/lymphotrack/results/lymphotrack_dx/CLLgenietest_231222"
    DEFAULT_LOGDIR = "/data/lymphotrack/logs/register_logs"
    DEFAULT_LOGFILE = f"cll_genie.{datetime.datetime.now():%Y%m%d%H%M%s}.log"
    RUN_COMPLETED_FILE = "RTAComplete.txt"
    SAMPLESHEET_NAME = "SampleSheet.csv"
    SAMPLESHEET_KEYWORDS = [
        "lymphotrack",
        "Lymphotrack",
        "LYMPHOTRACK",
        "SHM",
        "shm",
        "Shm",
        "TRB",
        "IGK",
        "IGH",
    ]
    EXCLUDE_SAMPLE_TAGS = ["POS", "NEG", "IGHSHM"]
    DEAFAULT_JSON_STATS_FILE = "/Data/Intensities/BaseCalls/Stats/Stats.json"

    def __init__(self, RUNDIR=None, RUN=None, RESULTSDIR=None):
        if RUNDIR:
            self.RUNDIR = RUNDIR
        else:
            self.RUNDIR = LymphotrackRegister.DEFAULT_RUNDIR

        if RUN:
            self.RUN = RUN
        else:
            self.RUN = None

        if self.RUN:
            self.sample_sheet = f"{self.RUN}/{LymphotrackRegister.SAMPLESHEET_NAME}"
            self.demux_stats_json = (
                f"{self.RUN}/{LymphotrackRegister.DEAFAULT_JSON_STATS_FILE}"
            )
        else:
            self.sample_sheet = self.demux_stats_json = None

        if RESULTSDIR:
            self.RESULTSDIR = RESULTSDIR
        else:
            self.RESULTSDIR = LymphotrackRegister.DEFAULT_RESULTSDIR

        self.db_connection = (
            MongoDBConnection()
        )  # Create an instance of MongoDBConnection

        self.logger = logging.getLogger(__name__)  # Create a logger instance

    def get_docs_to_register(self) -> None | dict:
        self.logger.info(
            f"Registering samples from the run {self.RUN} with the sample sheet {self.sample_sheet}"
        )

        sample_sheet_data, sequencer = self.get_samplesheet_data(self.sample_sheet)
        self.logger.debug(
            f"Samples from the run {self.RUN}, samplesheet data: {sample_sheet_data}"
        )
        self.logger.debug(
            f"Samples from the run {self.RUN}, sequencer Info: {sequencer}"
        )

        sample_elements = self.extract_sample_elements(sample_sheet_data)
        self.logger.debug(
            f"Samples from the run {self.RUN}, sample elements data: {sample_elements}"
        )

        demux_stats, run_number, flowcell = self.get_demux_stats()

        self.logger.debug(
            f"Samples from the run {self.RUN}, demux stats data: {demux_stats}"
        )
        return self.get_documents_lists(
            demux_stats,
            sample_elements,
            self.RUN,
            run_number,
            flowcell,
            sequencer,
        )

    @staticmethod
    def get_runfolders(RUNDIR=DEFAULT_RUNDIR) -> list:
        run_folders = []
        for dir in os.scandir(RUNDIR):
            if dir.is_dir():
                # print(dir.path)
                # print(dir.name)
                run_folders.append(dir.path)
        return run_folders

    @staticmethod
    def get_excelfiles(RESULTS=DEFAULT_RESULTSDIR) -> list:
        files = {}
        for root, dirs, filenames in os.walk(RESULTS):
            for filename in filenames:
                if filename.endswith(".xlsm") and not os.path.exists(
                    f"{root}/{filename}.registered"
                ):
                    name = filename.replace(".xlsm", "")
                    if name not in files:
                        files[name] = {"excel": f"{root}/{filename}"}
                    else:
                        files[name]["excel"] = f"{root}/{filename}"
                elif filename.endswith(".fastq_indexQ30.tsv") and not os.path.exists(
                    f"{root}/{filename}.registered"
                ):
                    name = filename.split("_")[0]
                    if name not in files:
                        files[name] = {"qc": f"{root}/{filename}"}
                    else:
                        files[name]["qc"] = f"{root}/{filename}"
        return files

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

    @staticmethod
    def get_runs_log(logs_file) -> dict:
        runs_log = {}
        if not os.path.exists(logs_file):
            touch(logs_file)

        with open(logs_file, "r") as log_file:
            for line in log_file:
                runs_log[line.split("\t")[1]] = line.split("\t")[2:]
        return runs_log

    def check_string_in_file(self, file_path):
        with open(file_path, "r") as file:
            for line in file:
                if any(
                    search_string in line
                    for search_string in LymphotrackRegister.SAMPLESHEET_KEYWORDS
                ):
                    return True
        return False

    def get_samplesheet_data(self, samplesheet: str) -> list:
        lines = []
        found_header = False
        instrument_type = None

        with open(samplesheet, "r") as samplesheet_file:
            for line in samplesheet_file:
                if not found_header:
                    if line.startswith("Instrument Type"):
                        instrument_type = line.split(",")[1]
                    if line.startswith("Sample_ID,Sample_Name"):
                        found_header = True
                else:
                    lines.append(line.strip())
        return lines, instrument_type

    def extract_sample_elements(self, samplesheet_data: str) -> dict:
        sample_elements_dict = {}
        clarity_id_pattern = r"(?:.*[-_]|^)(CMD[A-Za-z0-9]+)([-_]?.*)"  # it can start with any letters and not just CMD [A-Z]{3}\d+A\d+
        sample_id_pattern = r"\d{2}[A-Z]{2}\d{5}-?.*$"  # 22MD02148-SHM

        for sample_line in samplesheet_data:
            sample_line_list = sample_line.split(",")
            sample_id = sample_line_list[0]
            sample_id_match = re.match(sample_id_pattern, sample_id)
            sample_description = sample_line_list[9]

            consider_sample_line = False

            clarity_id = (
                re.search(clarity_id_pattern, sample_description).group(1).rstrip("-_")
                if re.search(clarity_id_pattern, sample_description)
                else None
            )

            if (
                any(
                    tag in sample_id for tag in LymphotrackRegister.SAMPLESHEET_KEYWORDS
                )
                and clarity_id is not None
            ):
                consider_sample_line = True

            if sample_description.lower().startswith("lymphotrack"):
                sample_description = sample_description[12:]
            elif sample_description.lower().endswith("lymphotrack"):
                sample_description = sample_description[:-12]

            if consider_sample_line:
                if sample_id_match:
                    sample_name = sample_id
                elif not sample_id_match:
                    sample_name = sample_description.replace(clarity_id, "")
                    sample_name = sample_name.strip("_")
                    sample_name = sample_name.strip("-")

                if sample_name not in sample_elements_dict.keys():
                    sample_elements_dict[sample_name] = [clarity_id]

        return sample_elements_dict

    def get_demux_stats(self):
        try:
            with open(self.demux_stats_json, "r") as json_file:
                json_data = json.load(json_file)
        except FileNotFoundError:
            json_data = None

        if json_data:
            _run_id = json_data["RunId"]
            _run_number = json_data["RunNumber"]
            _flowcell = json_data["Flowcell"]
            _conversion_stats = json_data["ConversionResults"]

            demux_stats_dict = {}
            for sample_lanes in _conversion_stats:
                for sample_stats in sample_lanes["DemuxResults"]:
                    # {'SampleId': '1262-21-val3-230123_SHM', 'SampleName': '1262-21-val3-230123_SHM', 'IndexMetrics': [{'IndexSequence': 'CGATGT', 'MismatchCounts': {'0': 290403, '1': 3522}}], 'NumberReads': 293925, 'Yield': 176942850, 'ReadMetrics': [{'ReadNumber': 1, 'Yield': 88471425, 'YieldQ30': 81961040, 'QualityScoreSum': 3217198198, 'TrimmedBases': 360673}, {'ReadNumber': 2, 'Yield': 88471425, 'YieldQ30': 62979276, 'QualityScoreSum': 2809619087, 'TrimmedBases': 446846}]}
                    if sample_stats["SampleId"] not in demux_stats_dict.keys():
                        demux_stats_dict[sample_stats["SampleId"]] = 0

                    demux_stats_dict[sample_stats["SampleId"]] += sample_stats["Yield"]
        else:
            demux_stats_dict = _run_number = _flowcell = None

        return demux_stats_dict, _run_number, _flowcell

    def get_documents_lists(
        self,
        stats_dict,
        clarity_ids_dict,
        runfolder_path,
        run_number,
        flowcell,
        sequencer_type,
    ) -> list[dict]:
        runfolder = os.path.basename(runfolder_path)
        merged_dict = deepcopy(clarity_ids_dict)
        for key, value in merged_dict.items():
            if stats_dict is not None and key in stats_dict.keys():
                merged_dict[key].append(stats_dict[key])
            else:
                merged_dict[key].append(0)

        to_register = []

        for key in merged_dict.keys():
            _dict_samples = {
                "name": key.strip(),  # key.replace("_", "-").strip(),
                "clarity_id": merged_dict[key][0].strip(),
                "run_id": runfolder.strip(),
                "run_number": run_number,
                "run_path": runfolder_path.strip(),
                "flowcell_id": flowcell.strip() if flowcell is not None else None,
                "sequencer": sequencer_type.strip()
                if sequencer_type is not None
                else None,
                "assay": "lymphotrack",
                "lymphotrack_excel": False,
                "lymphotrack_excel_path": "",
                "lymphotrack_qc": False,
                "lymphotrack_qc_path": "",
                "vquest": False,
                "report": False,
                "total_raw_reads": merged_dict[key][1],
                "total_reads": "",
                "q30_reads": "",
                "q30_per": "",
            }

            to_register.append(_dict_samples)

        return to_register

    def register_to_db(self, sample_docs, db, collection_name, overwrite):
        self.db_connection.connect(db)  # Create a MongoDB connection with default db
        # Get the client and database objects
        client = self.db_connection.get_client()
        db = self.db_connection.get_db()
        date_now = datetime.datetime.now()
        count = 0
        try:
            for sample_doc in sample_docs:
                sample_doc["date_added"] = date_now
                self.db_connection.insert_data(collection_name, sample_doc, overwrite)
                count += 1
            return True, count
        except:
            return False, count

    def update_files(self, collection_name, docs, files_dict, update_file):
        docs_count = len(docs)
        update_count = 0
        sample_not_updated = []
        for doc in docs:
            try:
                if doc["name"] in files_dict.keys():
                    if update_file == "excel":
                        file = (
                            files_dict[doc["name"]]["excel"]
                            if "excel" in files_dict[doc["name"]].keys()
                            else None
                        )
                        update_instructions = {
                            "$set": {
                                "lymphotrack_excel_path": file,
                                "lymphotrack_excel": True,
                            }
                        }
                    elif update_file == "qc":
                        file = (
                            files_dict[doc["name"]]["qc"]
                            if "qc" in files_dict[doc["name"]].keys()
                            else None
                        )
                        q30_values = self.get_q30_values(file)
                        update_instructions = {
                            "$set": {
                                "lymphotrack_qc_path": file,
                                "lymphotrack_qc": True,
                                "total_reads": q30_values[0],
                                "q30_reads": q30_values[1],
                                "q30_per": q30_values[2],
                            }
                        }
                    target = {"_id": doc["_id"]}
                    if file:
                        self.db_connection.update_data(
                            collection_name, target, update_instructions
                        )
                        touch(f"{file}.registered")
                        self.logger.debug(
                            f"File updating for the query {target}: {update_instructions}"
                        )
                        self.logger.info(
                            f"{update_file} {file} is updated successfully for the sample {doc['name']}"
                        )
                        update_count += 1
                else:
                    sample_not_updated.append(doc["name"])
            except:
                pass

        if docs_count > update_count:
            self.logger.error(
                f"All the documents are not updated, there might be some result {update_file} files are not available... Will try again in after a while.."
            )
            self.logger.debug(
                f"Samples which are not updated for unavailability result {update_file}, {sample_not_updated}"
            )
            success = False
        else:
            success = True

        del docs_count, update_count, sample_not_updated
        return success

    def get_q30_values(self, filename):
        total_reads = q30_reads = q30_per = ""
        if filename:
            with open(filename, "r") as qc_file:
                lines = qc_file.readlines()
                total_reads = int(lines[0].split("\t")[1].strip())
                q30_reads = int(lines[1].split("\t")[1].strip())
                q30_per = float(lines[2].split("\t")[1].strip().replace(",", "."))
        return (total_reads, q30_reads, q30_per)

    def update_run_status_log(self, log_file, data):
        with open(log_file, "a") as log:
            log.write("\t".join(run_to_log) + "\n")


class MongoDBConnection:
    """
    A class representing a connection to a MongoDB database.

    Attributes:
        host (str): The hostname of the MongoDB server.
        port (int): The port number of the MongoDB server.
        client: The MongoClient object representing the connection to the MongoDB server.
        db: The database object representing the connected database.
        logger: The logger object for logging messages.

    Methods:
        connect(db): Connects to the specified database.
        get_client(): Returns the MongoClient object.
        get_db(): Returns the database object.
        get_docs(collection_name, query): Retrieves documents from the specified collection based on the given query.
        insert_data(collection_name, data, overwrite): Inserts data into the specified collection.
        update_data(collection_name, target, update_data): Updates documents in the specified collection based on the given target and update data.
        drop_document(_id, collection): Deletes a document from the specified collection based on the given document ID.
        is_existing(collection, doc_filter): Checks if a document exists in the specified collection based on the given filter.
    """

    def __init__(self, host="localhost", port=27017):
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
        data_find = {"name": data["name"]}

        if self.is_existing(collection, data_find):
            self.logger.error(
                f"Data already exists for the sample {data_find['name']} in {collection_name}"
            )
            if overwrite:
                existing_doc = collection.find_one(data_find)
                _id = existing_doc["_id"]
                self.logger.warning(
                    f"Overwrite is set to True, existing data will be replaced"
                )
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
        collection.delete_one({"_id": _id})

    def is_existing(self, collection, doc_filter):
        return collection.find_one(doc_filter) is not None


class ColorfulFormatter(logging.Formatter):
    def format(self, record):
        log_fmt = "%(asctime)s - %(log_color)s%(levelname)-8s%(reset)s %(log_color)s%(message)s"
        colors = {
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
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
    parser.add_argument(
        "--base-runDir",
        default=LymphotrackRegister.DEFAULT_RUNDIR,
        help=f"Set the Run dir path (default: {LymphotrackRegister.DEFAULT_RUNDIR}",
    )
    parser.add_argument(
        "--base-resultsDir",
        default=LymphotrackRegister.DEFAULT_RESULTSDIR,
        help=f"Set the Lymphotrack results folder path (default: {LymphotrackRegister.DEFAULT_RESULTSDIR}",
    )
    parser.add_argument(
        "--db-host", default="localhost", help=f"set mongo db host (default: localhost)"
    )
    parser.add_argument(
        "--db-port", default="27017", help=f"set mongo db port (default: 27017)"
    )
    parser.add_argument(
        "--db-name", default="cll_genie", help=f"set mongo db name (default: cll_genie)"
    )
    parser.add_argument(
        "--collection-name",
        default="samples",
        help=f"set mongo db collection name (default: samples)",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the log level (default: INFO)",
    )
    parser.add_argument(
        "--log-dir",
        default=LymphotrackRegister.DEFAULT_LOGDIR,
        help=f"Set the log dir path (default: {LymphotrackRegister.DEFAULT_LOGDIR})",
    )
    parser.add_argument(
        "--log-file",
        default=LymphotrackRegister.DEFAULT_LOGFILE,
        help=f"Set the log file name (default: {LymphotrackRegister.DEFAULT_LOGFILE})",
    )
    parser.add_argument(
        "--overwrite-db",
        default=False,
        help=f"Will overwrite existing data in the database and register again as a fresh copy if set to True (default: False)",
    )
    parser.add_argument(
        "--update-excel",
        default=False,
        help=f"Will update the excel paths in the database if set to True (default: False)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    # get args
    args = parse_arguments()

    # Configure logging

    logger = configure_logging(args.log_level, f"{args.log_dir}/{args.log_file}")

    if not args.update_excel:
        run_folders = LymphotrackRegister.get_runfolders(RUNDIR=args.base_runDir)
        run_register_status_dict = LymphotrackRegister.get_runs_log(
            LymphotrackRegister.DEFAULT_RUN_STATUS_LOG
        )

        for run in run_folders:
            run_basename = os.path.basename(run)
            run_basename_len = len(run_basename)
            if not run_basename_len == 34:
                continue

            try:
                run_register_status = run_register_status_dict[run][0]
                log_info = run_register_status_dict[run][1].strip()
            except KeyError:
                run_register_status = log_info = None

            run_to_log = [
                f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}",
                run,
                run_register_status,
                log_info,
            ]

            if not os.path.exists(f"{run}/{LymphotrackRegister.RUN_COMPLETED_FILE}"):
                logger.info(
                    f"Run {run_basename} is still running. Will try again after a while..."
                )
                continue

            if run_register_status != "OK":
                # Create an instance of LymphotrackRegister
                run_instance = LymphotrackRegister(RUNDIR=args.base_runDir, RUN=run)
                run_instance.samples_docs = None

                logger.info(f"Processing {run_instance.RUN} ...")

                (
                    run_instance.sample_sheet_exists,
                    run_instance.is_valid,
                ) = run_instance.check_valid_file(f"{run_instance.sample_sheet}")

                if run_instance.sample_sheet_exists and run_instance.is_valid:
                    run_instance.samples_docs = run_instance.get_docs_to_register()
                    logger.debug(
                        f"Samples from the run {run_instance.RUN}, sample docs: {json.dumps(run_instance.samples_docs)}"
                    )
                elif run_instance.sample_sheet_exists and not run_instance.is_valid:
                    run_to_log[2] = "OK"
                    run_to_log[3] = "Not Valid"
                    logger.info(
                        f"Sample Sheet is not valid for the runId {run_instance.RUN}. Skipping it.."
                    )
                    continue
                elif not run_instance.sample_sheet_exists:
                    run_to_log[2] = "WAIT"
                    run_to_log[3] = "NO_SAMPLESHEET"
                    logger.info(
                        f"Sample Sheet does not exist for the runId {run_instance.RUN}. Still waiting for the status.."
                    )
                    continue
                if not run_instance.samples_docs:
                    logger.info(
                        f"No samples to register for the runId {run_instance.RUN}. Skipping it.."
                    )
                    run_to_log[2] = "OK"
                    run_to_log[3] = "NO_SAMPLES"
                    continue

                (
                    run_instance.success,
                    run_instance.sample_count,
                ) = run_instance.register_to_db(
                    run_instance.samples_docs,
                    args.db_name,
                    args.collection_name,
                    args.overwrite_db,
                )
                if run_instance.success:
                    logger.info(
                        f"Data inserted successfully from the run: {run}. Number of samples added: {run_instance.sample_count}"
                    )
                    run_to_log[2] = "OK"
                    run_to_log[3] = "SAMPLES_DONE"
                else:
                    run_to_log[2] = "FAIL"
                    run_to_log[3] = "SAMPLES_FAILED"
                    logger.error(
                        f"Data insertion failed from the run: {run}. Number of samples added: {run_instance.sample_count}"
                    )

                run_instance.update_run_status_log(
                    LymphotrackRegister.DEFAULT_RUN_STATUS_LOG, run_to_log
                )
            else:
                logger.warning(f"Samples were already registered for the runId {run}.")
                run_instance.sample_sheet_exists = run_instance.is_valid = False

    else:
        # Create an instance of LymphotrackRegister results
        results_instance = LymphotrackRegister(RESULTSDIR=args.base_resultsDir)
        logger.info(f"Looking for excel/qc files in {results_instance.RESULTSDIR}")
        results_instance.files = LymphotrackRegister.get_excelfiles(
            RESULTS=args.base_resultsDir
        )
        results_instance.db_connection.connect(args.db_name)

        results_instance.excel_query = {"lymphotrack_excel": False}
        results_instance.qc_query = {"lymphotrack_qc": False}

        results_instance.samples_docs_excel = results_instance.db_connection.get_docs(
            args.collection_name, results_instance.excel_query
        )

        results_instance.samples_docs_qc = results_instance.db_connection.get_docs(
            args.collection_name, results_instance.qc_query
        )

        results_instance.update_status_qc = results_instance.update_files(
            args.collection_name,
            results_instance.samples_docs_qc,
            results_instance.files,
            "qc",
        )

        results_instance.update_status_excel = results_instance.update_files(
            args.collection_name,
            results_instance.samples_docs_excel,
            results_instance.files,
            "excel",
        )
