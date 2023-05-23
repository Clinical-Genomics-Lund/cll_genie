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

    @staticmethod
    def get_parameters_for_report(_id: str, submission_id: str) -> dict | None:
        """
        Fetch the parameters from the database and process the parameters for the report
        """
        try:
            return ReportController.results_handler.get_results(_id)["results"][
                submission_id
            ]["vquest_parameters"]
        except KeyError:
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
                        cll_app.config["REPORT_SUMMARY_COLUMNS"],
                    )
                )
                summary_results[seq_id].update(
                    subset_dict(
                        detailed_results[seq_id]["junction"],
                        cll_app.config["REPORT_JUNCTION_COLUMNS"],
                    )
                )
                summary_results[seq_id].update(detailed_results[seq_id]["messages"])

            return summary_results
        else:
            return None

    @staticmethod
    def get_pdf_filename(_id: str, submission_id: str) -> str:
        """
        Return a pdf filename for a given submission id and create auto report id
        """
        sample_name = ReportController.sample_handler.get_sample_name(_id)
        reports_dir = cll_app.config["REPORT_OUTDIR"]
        submission_id = submission_id.replace("submission_", "")
        if not os.path.exists(reports_dir):
            os.makedirs(reports_dir)

        report_num = ReportController.results_handler.next_submission_report_id(
            _id, submission_id
        )
        report_id = f"{sample_name}_{submission_id}_{report_num}"
        return f"{reports_dir}/{report_id}.pdf"

    @staticmethod
    def get_latest_report_summary_text(_id: str, submission_id: str) -> str:
        """
        Return a report summary for the last report if there is or None otherwise
        """

        submission_reports = ReportController.results_handler.get_submission_reports(
            _id, submission_id
        )
        if len(submission_reports) > 0:
            report_id = submission_reports[-1]
            report_summary = ReportController.results_handler.get_report_summary(
                _id, report_id
            )
        else:
            report_summary = ReportController.generate_report_summary_text(
                _id, submission_id
            )

        return report_summary

    @staticmethod
    def generate_report_summary_text(_id: str, submission_id: str) -> str:
        """
        Build report summary for pdf reports
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
        if results_summary is not None:
            # Common comment
            summary_string = "Analysen innefattar amplifiering och sekvensering av klonalt IGH-gen rearrangemang för identifiering av somatisk hypermutationsstatus dvs. muterad (M-CLL) eller icke muterad (U-CLL). Dessutom undersöks eventuell subsettillhörighet (subset #1, #2, #4 eller #8).\n\n"

            if number_of_submitted_seqs == 0:
                summary_string += "I aktuellt KLL prov kan ett funktionellt IGH-gen rearrangemang inte identifieras.\nDå vidare analys av somatisk hypermutationsstatus och subset-tillhörighet ej är utförbart hänvisas aktuellt provet för analys vid avd. för Molekylärpatologi, Uppsala Akademiska Sjukhus.\n\n"
            elif number_of_submitted_seqs == 1:
                summary_string += "I aktuellt KLL prov kan ett funktionellt IGH-gen rearrangemang identifieras.\n\n"
            elif number_of_submitted_seqs == 2:
                summary_string += "I aktuellt KLL prov kan två funktionella IGH-gen rearrangemang identifieras.\n\n"
            elif number_of_submitted_seqs == 3:
                summary_string += "I aktuellt KLL prov kan tre funktionella IGH-gen rearrangemang identifieras.\n\n"

            # Hyper mutation status comment
            summary_string += (
                f"{ReportController.get_hypermutation_string(results_summary)}\n\n"
            )

            # Subset comment
            summary_string += (
                f"{ReportController.get_subset_string(results_summary)}\n\n"
            )

            # Clinical Comments
            # YET TO COME
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

        swedish_number_string = [
            "",
            "ett",
            "två",
            "tre",
            "fyra",
            "Fem",
            "sex",
            "sju",
            "åtta",
            "nio",
            "tio",
        ]

        if all(
            float(v_identity_per)
            > cll_app.config["HYPER_MUTATION_BORDERLINE_UPPER_CUTOFF"]
            for v_identity_per in v_identity
        ):
            return_string = f"Analysen av den {swedish_number_string[seq_count]} produktiva IGH-gensekvenserna i IMGT/V-QUEST påvisar ingen förekomst av somatisk hypermutation (U-CLL) i det aktuella provet ({v_identity_string}% identitet mot IGHV-genen)."

        elif all(
            float(v_identity_per)
            < cll_app.config["HYPER_MUTATION_BORDERLINE_LOWER_CUTOFF"]
            for v_identity_per in v_identity
        ):
            return_string = f"Analysen av den {swedish_number_string[seq_count]} produktiva IGH-gensekvenserna i IMGT/V-QUEST påvisar förekomst av somatisk hypermutation (M-CLL) i det aktuella provet ({v_identity_string}% identitet mot IGHV-genen)"

        elif all(
            float(v_identity_per)
            >= cll_app.config["HYPER_MUTATION_BORDERLINE_LOWER_CUTOFF"]
            and float(v_identity_per)
            <= cll_app.config["HYPER_MUTATION_BORDERLINE_UPPER_CUTOFF"]
            for v_identity_per in v_identity
        ):
            return_string = f"Analysen av den {swedish_number_string[seq_count]} produktiva IGH-gensekvenserna i IMGT/V-QUEST påvisar borderline-resultat i det aktuella provet (97-97.98% identitet mot IGHV-genen). Det är således omöjligt att säkerställa mutationsstatus för aktuellt prov"

        else:
            return_string = f"Analysen av de {swedish_number_string[seq_count]} produktiva IGH-gensekvenserna i IMGT/V-QUEST påvisar motsägelsefulla resultat med avseende på förekomst av somatisk hypermutation ({v_identity_string}% identitet mot IGHV-genen) i det aktuella provet. Det är således inte möjligt att säkerställa mutationsstatus för aktuellt prov."

        return return_string

    @staticmethod
    def get_subset_string(results_dict):
        seqs = list(results_dict.keys())
        return_string = ""
        subset_ids = list(
            set([results_dict[seq_id]["summary"]["CLL subset"] for seq_id in seqs])
        )
        subset_count = len(subset_ids)

        if subset_count == 1 and subset_ids[0] is not None:
            return_string = f"Vidare påvisar subset-analysen att det aktuella provet tillhör subset {subset_ids[0]}"

        elif subset_count == 1 and subset_ids[0] is None:
            return_string = f"Vidare påvisar subset-analysen ingen subsettillhörighet med avseende på subset #1 #2, #4 eller #8 i det aktuella provet"

        elif subset_count > 1:
            return_string = f"Dessutom visar delmängdsanalysen motsägelsefullt delmängdsmedlemskap med avseende på delmängd #1 #2, #4 eller #8 i det aktuella urvalet. Någon avgörande delmängdstilldelning kan därför inte göras."

        return return_string

    @staticmethod
    def delete_cll_report(_id: str, report_id: str) -> bool:
        """
        Delete Cll Report for a given ID from results and sample collection
        """
        update_instructions = {"$unset": {f"cll_reports.{report_id}": ""}}

        try:
            ReportController.results_handler.results_collection().find_one_and_update(
                ReportController.results_handler._query_id(_id), update_instructions
            )
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
