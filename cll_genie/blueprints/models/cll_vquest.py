from flask import current_app as cll_app
import pymongo
from pymongo.errors import PyMongoError
from bson.objectid import ObjectId
from pprint import pformat
from copy import deepcopy
import os
import shutil


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
        except (KeyError, ValueError, TypeError):
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

    def delete_submission_results(self, _id: str, submission_id: str) -> bool:
        """
        Delete the submission results for a given id and submission id and return True if successful or False otherwise
        """
        if self.submission_result_exists(_id, submission_id):
            results = self.get_results(_id)["results"]
            local_results_path = os.path.dirname(
                results[submission_id]["results_zip_file"]
            )[: -len("/vquest")]
            self.delete_submission_results_locally(local_results_path)
            results.pop(submission_id)
            return self.update_document(_id, "results", results)
        else:
            return False

    def delete_submission_results_locally(self, local_path: str) -> bool:
        """
        Delete the submission results for a given id and submission id and return True if successful or False otherwise
        """
        if local_path and os.path.exists(local_path):
            try:
                # Check if it's a file or directory and delete accordingly
                if os.path.isfile(local_path):
                    os.remove(local_path)
                elif os.path.isdir(local_path):
                    shutil.rmtree(local_path)
                return True
            except OSError as e:
                cll_app.logger.error(
                    f"Deletion os submission results at {local_path} failed with exception: {e}"
                )
                return False
        else:
            cll_app.logger.error("Invalid path provided or path does not exist.")
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

    def update_comments(self, _id, submission_id, key, value) -> bool:
        target = ResultsHandler._query_id(_id)

        results = self.get_results(_id)["results"]
        results[submission_id][key] = value

        update_instructions = {"$set": {"results": results}}

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
