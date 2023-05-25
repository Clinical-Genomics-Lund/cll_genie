from flask import current_app as cll_app
import pymongo  # type: ignore
from pymongo.errors import PyMongoError
from bson.objectid import ObjectId  # type: ignore
from typing import Dict, Any, Optional
from pprint import pformat


class SampleHandler:
    """
    Get, count and update cll_genie sample data
    """

    def __init__(self):
        self.mongo_client = None
        self.db = None
        self.collection = None

    def initialize(self, mongo_client, db_name, collection_name) -> None:
        self.mongo_client = mongo_client
        self.db = db_name
        self.collection = collection_name

    def samples_collection(self) -> pymongo.MongoClient:
        return self.mongo_client[self.db][self.collection]

    @staticmethod
    def _query_id(_id: str) -> Dict[str, ObjectId]:
        return {"_id": ObjectId(_id)}

    def get_sample(self, _id: str) -> Optional[Dict[str, Any]]:
        query = SampleHandler._query_id(_id)
        return self.samples_collection().find_one(query)

    def sample_exists(self, _id: str) -> bool:
        return bool(self.get_sample(_id))

    def get_samples(self, query: Optional[dict] = None) -> pymongo.collection.Cursor:
        if query is None:
            query = {}
        return self.samples_collection().find(query)

    def get_samples_by_sample_id(self, sample_id: str) -> pymongo.collection.Cursor:
        return self.samples_collection().find({"name": sample_id})

    def get_sample_name(self, _id):
        return self.get_sample(_id).get("name")

    def get_vquest_status(self, _id):
        return self.get_sample(_id).get("vquest")

    def get_report_status(self, _id):
        return self.get_sample(_id).get("report")

    def get_q30_per(self, _id):
        return self.get_sample(_id).get("q30_per")

    def get_lymphotrack_excel_status(self, _id):
        return self.get_sample(_id).get("lymphotrack_excel")

    def get_lymphotrack_excel(self, _id):
        return self.get_sample(_id).get("lymphotrack_excel_path")

    def get_lymphotrack_qc(self, _id):
        return self.get_sample(_id).get("lymphotrack_qc_path")

    def get_lymphotrack_qc_status(self, _id):
        return self.get_sample(_id).get("lymphotrack_qc")

    def get_cll_reports(self, _id):
        return self.get_sample(_id).get("cll_reports", {})

    def get_negative_report(self, _id: str) -> dict | None:
        return self.get_sample(_id).get("negative_report", None)

    def negative_report_status(self, _id: str) -> bool:
        return bool(self.get_negative_report(_id))

    def update_document(self, _id, key, value) -> bool:
        """
        change the status or update any key with the new value of a document
        """
        target = SampleHandler._query_id(_id)
        update_instructions = {"$set": {key: value}}
        try:
            self.samples_collection().find_one_and_update(target, update_instructions)
            cll_app.logger.debug(
                f"Update successful for {pformat(update_instructions)}"
            )
            cll_app.logger.info(
                f"Update successful for the id {_id} and {pformat(update_instructions)} is successful"
            )
            return True
        except PyMongoError as e:
            cll_app.logger.error(f"Update FAILED due to error {str(e)}")
            cll_app.logger.debug(
                f"Update FAILED due to error {str(e)} and for the update instructions {pformat(update_instructions)}"
            )
            return False
