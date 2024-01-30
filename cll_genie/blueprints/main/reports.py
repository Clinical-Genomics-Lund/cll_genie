from copy import deepcopy
from pprint import pformat
from flask import current_app as cll_app
import os
from pymongo.errors import PyMongoError
from cll_genie.extensions import sample_handler
from cll_genie.extensions import results_handler


class ReportController:
    """
    Get, validate and process sample data into report data for scanb report template
    """

    sample_handler = sample_handler
    results_handler = results_handler
    swedish_number_string = [
        "",
        "ett",
        "två",
        "tre",
        "fyra",
        "fem",
        "sex",
        "sju",
        "åtta",
        "nio",
        "tio",
    ]

    REPORT_SUMMARY_COLUMNS = [  # DO NOT CHANGE THIS UNLESS YOU KNOW WHAT YOU ARE DOING
        "V-DOMAIN Functionality",
        "V-GENE and allele",
        "V-REGION score",
        "V-REGION identity %",
        "V-REGION identity nt",
        "V-REGION identity % (with ins/del events)",
        "V-REGION identity nt (with ins/del events)",
        "V-REGION potential ins/del",
        "J-GENE and allele",
        "J-REGION score",
        "J-REGION identity %",
        "J-REGION identity nt",
        "D-GENE and allele",
        "D-REGION reading frame",
        "CDR-IMGT lengths",
        "FR-IMGT lengths",
        "AA JUNCTION",
        "V-DOMAIN Functionality comment",
        "V-REGION insertions",
        "V-REGION deletions",
        "Analysed sequence length",
        "Sequence analysis category",
        "CLL subset",
        "Merge Count",
        "Total Reads Per",
    ]

    REPORT_JUNCTION_COLUMNS = [
        "JUNCTION-nt nb",
        "JUNCTION decryption",
    ]

    @staticmethod
    def get_parameters_for_report(_id: str, submission_id: str) -> dict | None:
        """
        Fetch the parameters from the database and process the parameters for the report
        """
        try:
            return ReportController.results_handler.get_results(_id)["results"][
                submission_id
            ]["vquest_parameters"]
        except:
            return None

    @staticmethod
    def get_summary_for_report(_id: str, submission_id: str) -> dict | None:
        """
        Fetch the results from the database and process the summary for the report
        """

        def subset_dict(d: dict, l: list) -> dict:
            return {k: d[k] for k in l if k in d}

        if ReportController.results_handler.results_document_exists(_id):
            detailed_results = ReportController.results_handler.get_results(_id)[
                "results"
            ][submission_id]["vquest_results"]
            summary_results = {}

            for seq_id in detailed_results.keys():
                summary_results[seq_id] = {}
                summary_results[seq_id].update(
                    subset_dict(
                        detailed_results[seq_id]["summary"],
                        ReportController.REPORT_SUMMARY_COLUMNS,
                    )
                )
                summary_results[seq_id].update(
                    subset_dict(
                        detailed_results[seq_id]["junction"],
                        ReportController.REPORT_JUNCTION_COLUMNS,
                    )
                )

            return summary_results
        else:
            return None

    @staticmethod
    def get_comments_for_report(_id: str, submission_id: str) -> dict | None:
        """
        Fetch the results comments from the database and process the comments for the report
        """

        if ReportController.results_handler.results_document_exists(_id):
            comments = ReportController.results_handler.get_results(_id)["results"][
                submission_id
            ]["submission_comments"]
            return comments
        else:
            return None

    @staticmethod
    def get_submission_report_counts(_id: str, submission_id: str) -> int:
        """
        Return the number of submission reports for a given id and submission id or 0 if not found
        """
        return len(
            ReportController.sample_handler.get_submission_reports(_id, submission_id)
        )

    @staticmethod
    def get_report_counts_per_submission(_id: str, results: dict = None) -> dict:
        """
        Return the number of reports for all the submissions for a given id or None iff not found
        """
        submissions_counts = {}

        if results is None:
            results = ReportController.results_handler.get_results(_id).get(
                "results", {}
            )

        if results:
            for sid in results.keys():
                if sid not in submissions_counts:
                    submissions_counts[
                        sid
                    ] = ReportController.get_submission_report_counts(_id, sid)

        return submissions_counts

    @staticmethod
    def next_submission_report_id(_id: str, submission_id: str) -> int:
        submission_reports = ReportController.sample_handler.get_submission_reports(
            _id, submission_id
        )
        if len(submission_reports) > 0:
            return int(submission_reports[-1].split("_")[-1]) + 1
        else:
            return 1

    @staticmethod
    def get_html_filename(_id: str, submission_id: str, neg=False) -> str:
        """
        Return a html filename for a given submission id and create auto report id
        """
        sample_name = ReportController.sample_handler.get_sample_name(_id)
        reports_dir = cll_app.config["REPORT_OUTDIR"]
        if not os.path.exists(reports_dir):
            os.makedirs(reports_dir)

        if neg:
            report_id = f"{sample_name}_NR"
            return f"{reports_dir}/{report_id}.html"
        else:
            submission_id = submission_id.replace("submission_", "")
            report_num = ReportController.next_submission_report_id(_id, submission_id)
            report_id = f"{sample_name}_{submission_id}_{report_num}"
            return f"{reports_dir}/{report_id}.html"

    @staticmethod
    def generate_report_summary_text(_id: str, submission_id: str) -> str:
        """
        Build report summary for html reports
        """
        try:
            results_summary = ReportController.results_handler.get_results(_id)[
                "results"
            ][submission_id]["vquest_results"]
            number_of_submitted_seqs = int(
                ReportController.get_parameters_for_report(_id, submission_id)[
                    "Number of submitted sequences"
                ]
            )
        except:
            number_of_submitted_seqs = 0
            results_summary = None

        # Rearrangement comment
        if results_summary:
            # Common comment
            summary_string = "DNA har extraherats från insänt prov och analyserats med massiv parallell sekvensering (MPS, även kallat NGS). Analysen omfattar detektion av klonalt IGHV-D-J genrearrangemang, somatisk hypermutationsstatus (muterad, M-CLL eller icke muterad, U-CLL), samt subsettillhörighet (subset #2 eller #8). \n\n"

            if number_of_submitted_seqs == 0:
                summary_string += "Vid analysen påvisas ingen förekomst av klonal IGH-sekvens, varpå analys av IG-genrearrangemang och mutationsstatus inte är möjlig att utföra. Provet skickas till Göteborg för att utföra analys av RNA. \n\n"
            elif number_of_submitted_seqs == 1:
                summary_string += "Vid analysen finner man en klonal sekvens med ett funktionellt IGH-gen rearrangemang (se tabell Seq1).\n\n"
            elif number_of_submitted_seqs > 1:
                summary_string += f"Vid analysen finner man {ReportController.swedish_number_string[number_of_submitted_seqs]} klonala sekvenser, båda med funktionella IGH-gen rearrangemang. (se tabeller; Seq1, Seq2,..) \n\n"

            # Hyper mutation status comment
            summary_string += (
                f"{ReportController.get_hypermutation_string(results_summary)}\n\n"
            )

            # Subset comment
            (
                subset_string,
                subset_id,
            ) = ReportController.get_subset_string(results_summary)
            summary_string += f"{subset_string}\n\n"

            # Clinical Comments
            # STILL NEED TO BE MODIFIED
            # TODO
            if subset_id == "#2":
                summary_string += "Subset #2 är riskstratifierande oberoende av mutationsstatus (Nationellt vårdprogram 2022, ERIC Guidelines 2022). \n\n"
            elif subset_id == "#8":
                summary_string += " Subset #8 är riskstratifierande och associerad Richerstransformation (Nationellt vårdprogram 2022, ERIC Guidelines 2022). \n\n"
            else:
                summary_string += "Mutationsstatus är riskstratifierande samt vägledande vid behandlingsval av KLL (Nationellt vårdprogram 2022, ERIC Guidelines 2022).\n\n"

        else:
            summary_string = None

        return summary_string

    @staticmethod
    def get_hypermutation_string(results_dict):
        seqs = list(results_dict.keys())
        seq_count = len(seqs)
        return_string = ""
        v_identity = [
            round(float(results_dict[seq_id]["summary"]["V-REGION identity %"]), 2)
            for seq_id in seqs
        ]

        v_identity_string = "%, ".join(str(x) for x in deepcopy(v_identity))

        if all(
            float(v_identity_per)
            > cll_app.config["HYPER_MUTATION_BORDERLINE_UPPER_CUTOFF"]
            for v_identity_per in v_identity
        ):
            if seq_count == 1:
                return_string = f"Analysen påvisar ingen somatisk hypermutation (U-CLL) ({v_identity_string}% identitet mot IGHV-genen)."
            elif seq_count > 1:
                return_string = f"Analysen av de {ReportController.swedish_number_string[seq_count]} produktiva IGH-gensekvenserna påvisar ingen somatisk hypermutation (U-CLL) ({v_identity_string}% identitet mot IGHV-genen)."

        elif all(
            float(v_identity_per)
            < cll_app.config["HYPER_MUTATION_BORDERLINE_LOWER_CUTOFF"]
            for v_identity_per in v_identity
        ):
            if seq_count == 1:
                return_string = f"Analysen påvisar somatisk hypermutation (M-CLL) ({v_identity_string}% identitet mot IGHV-genen)"
            elif seq_count > 1:
                return_string = f"Analysen av de {ReportController.swedish_number_string[seq_count]} produktiva IGH-gensekvenserna påvisar förekomst av somatisk hypermutation (M-CLL) ({v_identity_string}% identitet mot IGHV-genen)."

        elif all(
            float(v_identity_per)
            >= cll_app.config["HYPER_MUTATION_BORDERLINE_LOWER_CUTOFF"]
            and float(v_identity_per)
            <= cll_app.config["HYPER_MUTATION_BORDERLINE_UPPER_CUTOFF"]
            for v_identity_per in v_identity
        ):
            if seq_count == 1:
                return_string = f"Analysen påvisar ett borderline-resultat ({v_identity_string}% identitet mot IGHV-genen)."
            elif seq_count > 1:
                return_string = f"Analysen av den {ReportController.swedish_number_string[seq_count]} produktiva IGH-gensekvenserna påvisar ett borderline-resultat ({v_identity_string}% identitet mot IGHV-genen)."

        else:
            return_string = f"Analysen av de {ReportController.swedish_number_string[seq_count]} produktiva IGH-gensekvenserna påvisar ett icke-konklusivt resultat av somatisk hypermutation ({v_identity_string}% identitet mot IGHV-genen). Det är således inte möjligt att säkerställa mutationsstatus för aktuellt prov. Provet skickas till Göteborg för att utföra analys av RNA. Provet skickas till Göteborg för att utföra analys av RNA."

        return return_string

    @staticmethod
    def get_subset_string(results_dict):
        seqs = list(results_dict.keys())
        return_string = ""
        return_subset = None
        subset_ids = list(
            set(
                [
                    results_dict[seq_id]["summary"]["CLL subset"]
                    for seq_id in seqs
                    if results_dict[seq_id]["summary"]["CLL subset"] is not None
                ]
            )
        )
        subset_count = len(subset_ids)

        if subset_count == 1 and subset_ids[0] is not None:
            return_string = (
                f"Vidare påvisas subsettillhörighet till subset {subset_ids[0]}"
            )
            return_subset = subset_ids[0]

        elif (subset_count == 1 and subset_ids[0] is None) or subset_count == 0:
            return_string = f"Analysen påvisar ingen subsettillhörighet."

        elif subset_count > 1:
            return_string = f"Dessutom visar delmängdsanalysen motsägelsefullt delmängdsmedlemskap med avseende på delmängd #2 eller #8 i det aktuella urvalet. Någon avgörande delmängdstilldelning kan därför inte göras."

        return return_string, return_subset

    @staticmethod
    def delete_cll_report(_id: str, report_id: str) -> bool:
        """
        Delete Cll Report for a given ID from sample collection
        """
        update_instructions = {"$unset": {f"cll_reports.{report_id}": ""}}

        try:
            ReportController.sample_handler.samples_collection().find_one_and_update(
                ReportController.sample_handler._query_id(_id), update_instructions
            )
            cll_app.logger.info(
                f"Report deletion for the report id {report_id} is SUCCESSFUL"
            )
            return True
        except PyMongoError as e:
            cll_app.logger.error(
                f"Report deletion for the report id {report_id} FAILED due to error {str(e)}"
            )
            cll_app.logger.debug(
                f"Report deletion for the report id {report_id} FAILED due to error {str(e)} and for the update instructions {pformat(update_instructions)}"
            )
            return False

    @staticmethod
    def delete_cll_report_local(_id: str, report_id: str) -> bool:
        """
        Delete Cll Report for a given ID from local path
        """
        sample = ReportController.sample_handler.get_sample(_id)
        report = sample.get("cll_reports").get(report_id)

        if report is None:
            cll_app.logger.error(
                f"Report deletion for the report id {report_id} FAILED as the file does not exist locally"
            )
            return False

        report_path = os.path.abspath(report.get("path"))

        try:
            os.remove(report_path)
            cll_app.logger.info(
                f"Report deletion for the report id {report_id} is SUCCESSFUL"
            )
            return True
        except Exception as e:
            cll_app.logger.error(
                f"Report deletion for the report id {report_id} at {report_path} FAILED due to error {str(e)}"
            )
            return False

    @staticmethod
    def delete_cll_negative_report(_id: str) -> bool:
        """
        Delete Cll Report for a given ID from results and sample collection
        """
        update_instructions = {"$unset": {f"negative_report": ""}}
        sample = ReportController.sample_handler.get_sample(_id)

        ReportController.delete_cll_negative_report_local(sample)

        try:
            ReportController.sample_handler.samples_collection().find_one_and_update(
                ReportController.sample_handler._query_id(_id), update_instructions
            )
            cll_app.logger.info(
                f"No Results Report deletion for the report id {sample['name']} is SUCCESSFUL"
            )
            return True
        except PyMongoError as e:
            cll_app.logger.error(
                f"Report deletion for the report id {sample['name']} FAILED due to error {str(e)}"
            )
            cll_app.logger.debug(
                f"Report deletion for the report id {sample['name']} FAILED due to error {str(e)} and for the update instructions {pformat(update_instructions)}"
            )
            return False

    @staticmethod
    def delete_cll_negative_report_local(sample: dict) -> bool:
        """
        Delete Cll Report for a given ID from local path
        """
        negative_report = sample.get("negative_report")

        if negative_report is None:
            cll_app.logger.error(
                f"No Results Report deletion for the report id {sample['name']} FAILED as the file does not exist locally"
            )
            return False

        report_path = os.path.abspath(negative_report.get("path"))

        try:
            os.remove(report_path)
            cll_app.logger.info(
                f"No Results Report deletion for the report id {sample['name']} is SUCCESSFUL"
            )
            return True
        except Exception as e:
            cll_app.logger.error(
                f"No Results Report deletion for the report id {sample['name']} at {report_path} FAILED due to error {str(e)}"
            )
            return False

    @staticmethod
    def update_report_status(_id: str) -> bool:
        """
        Update the report to true or false based on the reports avaliable in the sample collections
        """
        sample = ReportController.sample_handler.get_sample(_id)
        reports = sample.get("cll_reports")
        negative_reports = sample.get("negative_report")
        neg_report_counts = unhidden_report_counts = 0
        report_status = sample.get("report")

        if reports:
            unhidden_report_counts = len(
                [report for report in reports if not reports[report]["hidden"]]
            )

        if negative_reports:
            neg_report_counts = len(negative_reports)

        if unhidden_report_counts < 1 and neg_report_counts < 1:
            if ReportController.sample_handler.update_document(_id, "report", False):
                cll_app.logger.info(
                    f"Report status updated to False for the sample {sample['name']}"
                )
            else:
                cll_app.logger.error(
                    f"Report status updated to False for the sample {sample['name']} is not sucessful due to some error"
                )
                return False

        if unhidden_report_counts >= 1 or neg_report_counts >= 1 and not report_status:
            if ReportController.sample_handler.update_document(_id, "report", True):
                cll_app.logger.info(
                    f"Report status updated to True for the sample {sample['name']}"
                )
            else:
                cll_app.logger.error(
                    f"Report status updated to True for the sample {sample['name']} is not sucessful due to some error"
                )
                return False

        return True

    @staticmethod
    def get_latest_report(_id: str, report_id: str) -> None | str:
        """
        Get the latest report from the database if it exists
        """

        report_docs = ReportController.sample_handler.get_cll_reports(_id)
        neg_report_docs = ReportController.sample_handler.get_negative_report(_id)
        unhidden_reports_ids = [
            report for report in report_docs.keys() if not report_docs[report]["hidden"]
        ]
        unhidden_reports_ids.sort()

        if unhidden_reports_ids:
            if report_id is None or report_id == "":
                report_id_show = unhidden_reports_ids[-1]
            elif (
                report_id is not None
                or report_id != ""
                and report_id in unhidden_reports_ids
            ):
                report_id_show = report_id
            else:
                report_id_show = None

            if report_id_show is not None:
                filepath = os.path.abspath(report_docs[report_id_show]["path"])
            else:
                filepath = None

        else:
            if (
                neg_report_docs is None
                or neg_report_docs["path"] == ""
                or not os.path.exists(os.path.abspath(neg_report_docs["path"]))
            ):
                filepath = None
            else:
                filepath = os.path.abspath(neg_report_docs["path"])
        return filepath
