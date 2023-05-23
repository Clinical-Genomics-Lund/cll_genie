from flask import current_app as cll_app
import pymongo
from pymongo.errors import PyMongoError
from bson.objectid import ObjectId
from pprint import pformat
from copy import deepcopy


class ResultsHandler:
    """
    put results after the vquest analysis in to database and also fetch vquest results
    """

    def __init__(self):
        self.mongo_client = None
        self.db = None
        self.collection = None

    def initialize(self, mongo_client, db_name, collection_name) -> None:
        """
        Initialize the mongo client, database and collection
        """
        self.mongo_client = mongo_client
        self.db = db_name
        self.collection = collection_name

    def results_collection(self) -> pymongo.MongoClient:
        """
        Return the results collection object
        """
        return self.mongo_client[self.db][self.collection]

    @staticmethod
    def _query_id(_id):
        """
        Return a query object for a given id
        """
        return {"_id": ObjectId(_id)}

    def get_results(self, _id: str) -> dict | None:
        """
        Return the results document for a given id or None if not found
        """
        query = ResultsHandler._query_id(_id)
        return self.results_collection().find_one(query)

    def results_document_exists(self, _id: str) -> bool:
        """
        Return True if the results document exists for a given id or False otherwise
        """
        return bool(self.get_results(_id))

    def get_submission_results(self, _id: str, submission_id: str) -> dict | None:
        """
        Return the submission results for a given id and submission id or None if not found
        """
        try:
            return self.get_results(_id)["results"][submission_id]
        except (KeyError, TypeError):
            return None

    def submission_result_exists(self, _id: str, submission_id: str) -> bool:
        """
        Return True if the submission results exist for a given id and submission id or False otherwise
        """
        return bool(self.get_submission_results(_id, submission_id))

    def get_submission_count(self, _id: str) -> int:
        """
        Return the number of submissions for a given id or 0 if not found
        """
        try:
            return len(self.get_results(_id)["results"])
        except (KeyError, ValueError):
            return 0

    def delete_document(self, _id):
        """
        Delete the results document for a given id and return True if successful or False otherwise
        """
        target = ResultsHandler._query_id(_id)
        try:
            self.results_collection().delete_one(target)
            return True
        except PyMongoError as e:
            return False

    def get_submission_reports(self, _id: str, submission_id: str) -> list:
        """
        Return a list of submission reports for a given id and submission id or an empty list if not found
        """
        try:
            results = self.get_results(_id)
            if results is not None:
                report_docs = results["cll_reports"]
                reports = {} if report_docs is None else deepcopy(report_docs)
                submission_reports = [
                    report
                    for report in reports.keys()
                    if int(report.split("_")[1]) == int(submission_id.split("_")[-1])
                ]
                submission_reports.sort()
                return submission_reports
            else:
                return []
        except KeyError or ValueError or TypeError:
            return []

    def get_submission_report_counts(self, _id: str, submission_id: str) -> int:
        """
        Return the number of submission reports for a given id and submission id or 0 if not found
        """
        return len(self.get_submission_reports(_id, submission_id))

    def get_report_counts_per_submission(self, _id: str) -> dict:
        """
        Return the number of reports for all the submissions for a given id or None iff not found
        """
        submissions_counts = {}
        results = self.get_results(_id).get("results", {})

        if results is not None:
            for sid in results.keys():
                if sid not in submissions_counts:
                    submissions_counts[sid] = self.get_submission_report_counts(
                        _id, sid
                    )

        return submissions_counts

    def next_submission_report_id(self, _id: str, submission_id: str) -> int:
        submission_reports = self.get_submission_reports(_id, submission_id)
        if len(submission_reports) > 0:
            return int(submission_reports[-1].split("_")[-1]) + 1
        else:
            return 1

    def get_reports(self, _id: str) -> dict | None:
        """
        Return reports for a given id and submission id or None if not found
        """
        return self.get_results(_id).get("cll_reports", {})

    def get_report_summary(self, _id: str, report_id: str) -> str | None:
        """
        Return report summary for a given report_id or None if not found
        """
        return self.get_reports(_id)[report_id] or None

    def delete_submission_results(self, _id: str, submission_id: str) -> bool:
        """
        Delete the submission results for a given id and submission id and return True if successful or False otherwise
        """
        if self.submission_result_exists(_id, submission_id):
            results = self.get_results(_id)["results"]
            results.pop(submission_id)
            return self.update_document(_id, "results", results)
        else:
            return False

    def update_document(self, _id, key, value) -> bool:
        """
        change the status or update any key with the new value of a document
        """
        target = ResultsHandler._query_id(_id)
        update_instructions = {"$set": {key: value}}

        try:
            self.results_collection().find_one_and_update(target, update_instructions)
            cll_app.logger.debug(f"Update results: {pformat(update_instructions)}")
            cll_app.logger.info(f"Update results for the id {_id} is successful")
            return True
        except PyMongoError as e:
            cll_app.logger.error(f"Update results FAILED due to error {str(e)}")
            cll_app.logger.debug(
                f"Update results FAILED due to error {str(e)} and for the update instructions {pformat(update_instructions)}"
            )
            return False
