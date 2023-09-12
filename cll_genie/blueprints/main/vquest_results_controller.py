from pymongo.errors import PyMongoError
from datetime import datetime
from bson import ObjectId
from cll_genie.extensions import results_handler
from cll_genie.extensions import sample_handler
from flask import current_app as cll_app
from cll_genie.blueprints.main.reports import ReportController
from copy import deepcopy
from flask_login import current_user


class ResultsController:

    """
    save results to the database cll_genie for main.views
    """

    results_handler = results_handler
    sample_handler = sample_handler
    now = datetime.now()

    @staticmethod
    def save_results_to_db(
        _id: str,
        results_data: dict,
        submission_id: str,
        zip_file_name: str,
        text_file_name: str,
    ) -> bool:
        collection = ResultsController.results_handler.results_collection()
        sample_name = ResultsController.sample_handler.get_sample_name(_id)

        params = results_data[sample_name]["parameters"]
        sequence_results = results_data[sample_name]
        sequence_results.pop("parameters")

        _doc = {
            "vquest_results": sequence_results,
            "vquest_parameters": params,
            "data_added": datetime.now(),
            "results_zip_file": zip_file_name,
            "detailed_text_file": text_file_name,
            "submission_comments": None,
        }

        if int(submission_id.split("_")[-1]) == 1:
            results = {submission_id: _doc}
            query_insert = {
                "_id": ObjectId(_id),
                "name": sample_name,
                "results": results,
                "cll_reports": None,
            }
            try:
                result = collection.insert_one(query_insert)
                if result.acknowledged:
                    cll_app.logger.info(
                        f"Results inserted into the database for {sample_name}"
                    )
                    status = True
                else:
                    cll_app.logger.error(f"Results insertion failed for {sample_name}")
                    status = False
            except PyMongoError as e:
                cll_app.logger.error(f"Insertion failed with exception: {e}")
                status = False
        else:
            results = ResultsController.results_handler.get_results(_id)["results"]
            results[submission_id] = _doc
            return ResultsController.results_handler.update_document(
                _id, "results", results
            )

        if status:
            return True
        else:
            ResultsController.results_handler.delete_cll_results(_id, submission_id)
            return False

    @staticmethod
    def get_submission_id(_id: str, num=None) -> str:
        if ResultsController.results_handler.results_document_exists(_id):
            detailed_results_submissions = (
                ResultsController.results_handler.get_results(_id)["results"].keys()
            )
            print(detailed_results_submissions)
            if num is None:
                submission_id = (
                    int(list(detailed_results_submissions)[-1].split("_")[1]) + 1
                )
            if num is not None and int(num) > 0:
                submission_id = list(detailed_results_submissions)[int(num) - 1].split(
                    "_"
                )[1]

            elif num is not None and int(num) <= 0:
                submission_id = list(detailed_results_submissions)[int(num)].split("_")[
                    1
                ]

            return f"submission_{submission_id}"
        else:
            return "submission_1"

    @staticmethod
    def save_comments(_id, submission_id, comment):
        old_comments = ReportController.get_comments_for_report(_id, submission_id)
        new_comments = deepcopy(old_comments) if old_comments is not None else []
        new_comments.append(comment)
        status = results_handler.update_comments(
            _id,
            submission_id,
            "submission_comments",
            new_comments,
        )
        return status

    @staticmethod
    def update_submission_comments_status(_id, submission_id, comment_id, query_type):
        old_comments = ReportController.get_comments_for_report(_id, submission_id)

        if comment_id is None:
            status = False
        else:
            new_comments = deepcopy(old_comments)
            for index, comment in enumerate(new_comments):
                if comment["id"] == ObjectId(comment_id):
                    new_comments[index]["hidden_by"] = current_user.get_fullname()
                    new_comments[index]["time_hidden"] = datetime.now()
                    if query_type == "hide":
                        new_comments[index]["hidden"] = True
                    elif query_type == "unhide":
                        new_comments[index]["hidden"] = False

        status = results_handler.update_comments(
            _id,
            submission_id,
            "submission_comments",
            new_comments,
        )
        return status

    @staticmethod
    def delete_cll_results(_id: str, submission_id: str) -> bool:
        """
        Delete Cll results and reports for a given submission id and object id
        """
        submission_results_count = (
            ResultsController.results_handler.get_submission_count(_id)
        )
        cll_submission_reports = (
            ResultsController.sample_handler.get_submission_reports(_id, submission_id)
        )
        try:
            if submission_results_count > 1:
                ResultsController.results_handler.delete_submission_results(
                    _id, submission_id
                )
            else:
                ResultsController.results_handler.delete_document(_id)

            if cll_submission_reports is not None or cll_submission_reports is not []:
                for report_id in cll_submission_reports:
                    ReportController.delete_cll_report(_id, report_id)
            return True
        except PyMongoError as e:
            cll_app.logger.error(
                f"Deletion of the results FAILED due to error {str(e)}"
            )
            return False

    @staticmethod
    def update_vquest_status(_id):
        """
        Update the vquest status to true or false based on the analysis results in the results collections
        """

        try:
            result_counts = len(
                ResultsController.results_handler.get_results(_id).get("results", "")
            )
        except AttributeError:
            result_counts = 0
        if result_counts < 1:
            ResultsController.sample_handler.update_document(id, "vquest", False)
