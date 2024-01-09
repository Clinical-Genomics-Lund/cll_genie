import os
import tempfile
import pandas as pd
from flask import current_app as cll_app
from flask import (
    render_template,
    redirect,
    url_for,
    request,
    flash,
    jsonify,
    session,
    abort,
    send_from_directory,
    send_file,
    make_response,
)
from flask_login import login_required, current_user
from cll_genie.blueprints.main.data_processing import ProcessExcel
from cll_genie.blueprints.main.vquest import VQuest
from cll_genie.blueprints.main.util import add_search_query, create_base64_logo
from cll_genie.blueprints.main.samplelists import SampleListController
from cll_genie.blueprints.main import main_bp
from cll_genie.blueprints.main.vquest_results_controller import ResultsController
from cll_genie.blueprints.main.reports import ReportController
from urllib.parse import urlencode
import ast
import shutil
from bson import ObjectId
from datetime import datetime


@main_bp.route("/")
def cll_genie():
    page_size = cll_app.config["PAGE_SIZE"]
    n_skip = int(request.args.get("skip", 0))
    search_string = request.args.get("search", "")
    query = {}
    if search_string:
        query = add_search_query(query, search_string)

    samples_false, sample_false_count = SampleListController.get_unanalyzed_sample_list(
        query, n_skip, page_size
    )

    query["report"] = True
    samples_true = SampleListController.get_sample_list(query, n_skip, page_size)

    return render_template(
        "cll_genie.html",
        samples_true=samples_true,
        samples_false=samples_false,
        search=search_string,
        page_size=page_size,
        n_skip=n_skip,
        sample_false_count=sample_false_count,
    )


@main_bp.route("/download/excel/<string:id>")
@login_required
def download_excel(id):
    sample_id = SampleListController.sample_handler.get_sample_name(id)
    excel_file = os.path.abspath(
        SampleListController.sample_handler.get_lymphotrack_excel(id)
    )
    try:
        return send_file(excel_file, as_attachment=True)
    except Exception as e:
        return render_template(
            "errors.html",
            errors=[
                f"Excel file does not exits in the path: {excel_file}",
                f"Error Caused: {str(e)}",
            ],
            sample_id=sample_id,
            _id=id,
        )


@main_bp.route("/download/qc_file/<string:id>")
@login_required
def download_qc_file(id):
    sample_id = SampleListController.sample_handler.get_sample_name(id)
    qc_file = os.path.abspath(
        SampleListController.sample_handler.get_lymphotrack_qc(id)
    )
    try:
        return send_file(qc_file, as_attachment=True)
    except Exception as e:
        return render_template(
            "errors.html",
            errors=[
                f"QC file does not exits in the path: {qc_file}",
                f"Error Caused: {str(e)}",
            ],
            sample_id=sample_id,
            _id=id,
        )


@main_bp.route("/download/results/<string:filetype>/<string:id>")
@login_required
def download_results(filetype: str, id: str):
    sample_id = SampleListController.sample_handler.get_sample_name(id)
    submission_id = request.args.get("sub_id")
    submission_results = ResultsController.results_handler.get_submission_results(
        id, submission_id
    )

    if filetype == "zip":
        attachment_file = os.path.abspath(submission_results["results_zip_file"])
        attachment_filename_to_download = f"{os.path.basename(attachment_file).replace('.zip', '')}_{submission_id}.zip"

    elif filetype == "text":
        attachment_file = os.path.abspath(submission_results["detailed_text_file"])
        attachment_filename_to_download = f"{os.path.basename(attachment_file).replace('.txt', '')}_{submission_id}.txt"

    try:
        response = make_response(send_file(attachment_file))
        response.headers.set(
            "Content-Disposition",
            "attachment",
            filename=attachment_filename_to_download,
        )
        return response
    except Exception as e:
        return render_template(
            "errors.html",
            errors=[
                f"Results file for the submission_id: {submission_id} does not exits in the path: {attachment_filename_to_download}",
                f"Error Caused: {str(e)}",
            ],
            sample_id=sample_id,
            _id=id,
        )


@main_bp.route("/sample/<string:sample_id>", methods=["GET"])
@login_required
def sample(sample_id: str):
    _id = request.args.get("_id")
    sample = SampleListController.sample_handler.get_sample(_id)
    results_submissions = None
    report_counts_per_submission = None

    results = ResultsController.results_handler.get_results(_id)
    if results is not None:
        results_submissions = results.get("results", {})
        report_counts_per_submission = (
            ReportController.get_report_counts_per_submission(
                _id, results=results_submissions
            )
        )

    if (
        sample["total_reads"] == ""
        or sample["q30_reads"] == ""
        or sample["q30_per"] == ""
    ):
        try:
            qc_values = load_qc(sample_id, sample["lymphotrack_qc_path"])
            sample["total_reads"] = int(qc_values["totalCount"])
            sample["q30_reads"] = int(qc_values["countQ30"])
            sample["q30_per"] = round(float(qc_values["indexQ30"].replace(",", ".")), 2)

            SampleListController.sample_handler.update_document(
                _id, "total_reads", sample["total_reads"]
            )
            SampleListController.sample_handler.update_document(
                _id, "q30_reads", sample["q30_reads"]
            )
            SampleListController.sample_handler.update_document(
                _id, "q30_per", sample["q30_per"]
            )
            cll_app.logger.info(f"QC data updated for the sample: {sample_id}")
        except:
            cll_app.logger.error(f"QC values not loaded for the sample: {sample_id}")

    return render_template(
        "sample.html",
        sample=sample,
        results_submissions=results_submissions,
        report_counts_per_submission=report_counts_per_submission,
    )


def load_qc(sample_id: str, lymphotrack_qc_file: str) -> dict:
    try:
        with open(lymphotrack_qc_file, "r") as qc_data:
            qc = qc_data.read().strip().split("\n")

        qc_values = {"totalCount": None, "countQ30": None, "indexQ30": None}
        for i in qc:
            qc_values[i.split("\t")[0]] = i.split("\t")[1]
        return qc_values
    except FileNotFoundError:
        cll_app.logger.error(
            f"Could not load qc data into the database for the sample id: {sample_id}"
        )
        flash(
            f"Could not load qc data into the database for the sample id: {sample_id}",
            "warning",
        )
        return {"totalCount": None, "countQ30": None, "indexQ30": None}


@main_bp.route("/get_sequences/<string:sample_id>", methods=["GET", "POST"])
@login_required
def get_sequences(sample_id: str):
    results_dir = cll_app.config["ANALYSIS_OUTDIR"]

    html_table = None
    meta_info = None
    filter_message = "No sequences passed the filtration threshold! Modify the filters and rerun or proceed with negative report creation"
    _id = request.args.get("_id")
    sample = SampleListController.sample_handler.get_sample(_id)

    if sample["lymphotrack_excel"]:
        excel_file = os.path.abspath(sample["lymphotrack_excel_path"])
        excel_name = os.path.basename(excel_file)
    else:
        excel_file = excel_name = None

    if request.method == "POST":
        filtration_cutoff = request.form.get("merged_per_cutoff")
        is_in_frame = request.form.get("is_inframe")
        no_stop_codon = request.form.get("no_stop_codon")
        excel_sheet_name = request.form.get("excelsheetname")
        excel_header_row = request.form.get("excelheaderrow")
        results_dir = os.path.join(results_dir, sample_id)
        _id = request.args.get("_id")
        excel_file_upload = ast.literal_eval(request.form.get("excel_file_upload"))

        # create parent directory if it doesn't exist
        os.makedirs(results_dir, exist_ok=True)

        if excel_file_upload:
            excel_file_uploaded = request.files["excel-file"]
            excel_file = excel_name = excel_file_uploaded.filename
            tmpdir = tempfile.mkdtemp(prefix=os.path.join(results_dir, "tmpdir"))

            print(f"Temporary directory: {tmpdir}")
            excel_file = f"{tmpdir}/{excel_file_uploaded.filename}"
            excel_file = os.path.join(tmpdir, excel_file_uploaded.filename)
            excel_file_uploaded.save(excel_file)
        else:
            tmpdir = None
            excel_file = os.path.abspath(request.form.get("excel-file"))

        # Pre processing data from the excel file Create an instance of the ExcelReader class
        if os.path.exists(excel_file):
            try:
                excel_reader = ProcessExcel(
                    excel_file,
                    excel_header_row,
                    excel_sheet_name,
                    filtration_cutoff,
                    no_stop_codon,
                    is_in_frame,
                )

                # Filter the data based on the "% total reads, In-frame (Y/N), No Stop codon (Y/N)" columns
                filtered_data, meta_info = excel_reader.filter_data()

            except (pd.errors.ParserError, Exception) as e:
                cll_app.logger.error(
                    f"There was an Error while reading the excel file: File is corrupted not in Excel format anymore, {str(e)}"
                )
                return render_template(
                    "errors.html",
                    errors=[
                        f"There was an Error while reading the excel file: File is corrupted not in Excel format anymore, {str(e)}"
                    ],
                    sample_id=sample_id,
                    _id=id,
                )

            # remove temp directory
            if tmpdir is not None:
                shutil.rmtree(tmpdir)

            # Create a html table from the filtered data
            if isinstance(filtered_data, pd.DataFrame):
                filtered_data.reset_index(drop=True, inplace=True)
                filtered_data.insert(0, "Select", "")
                filtered_data_len = len(filtered_data)

                if filtered_data_len > 0:
                    filter_message = None
                    SampleListController.sample_handler.update_document(
                        _id, "is_eligible_for_vquest", True
                    )
                else:
                    SampleListController.sample_handler.update_document(
                        _id, "is_eligible_for_vquest", False
                    )

                for i in range(filtered_data_len):
                    filtered_data.loc[
                        i, "Select"
                    ] = f"<input type=\"checkbox\" name=\"checkbox{str(filtered_data.loc[i, 'Rank'])}\" id=\"checkbox{str(filtered_data.loc[i, 'Rank'])}\" value=\">Seq{str(filtered_data.loc[i, 'Rank'])}_{sample_id};{str(filtered_data.loc[i, 'Sequence'])};{int(filtered_data.loc[i, 'Merge count'])};{float(filtered_data.loc[i, '% total reads'])}\n\">"

                html_table = filtered_data.to_html(
                    index=False, classes="df-table-class", escape=False
                )

            else:
                SampleListController.sample_handler.update_document(
                    _id, "is_eligible_for_vquest", False
                )

        else:
            return render_template(
                "errors.html",
                errors=[f"Excel file does not exits in the path: {excel_file}"],
                sample_id=sample_id,
                _id=id,
            )

    return render_template(
        "get_sequences.html",
        filter_message=filter_message,
        html_table=html_table,
        meta_info=meta_info,
        sample_id=sample_id,
        _id=_id,
        table_class="df-table-class",
        excel_file=excel_file,
        excel_name=excel_name,
    )


@main_bp.route("/vquest_analysis/<string:sample_id>", methods=["POST"])
@login_required
def vquest_analysis(sample_id: str):
    selected_sequence = None
    selected_sequence_stats = None
    if request.method == "POST":
        _id = request.args.get("_id")
        selected = []
        seq_selected_stats = []
        for checkbox in request.form:
            _seq = request.form.get(checkbox).split("\\n")
            _seq_elements = _seq[0].split(";")
            seq_append = "\n".join(_seq_elements[0:2])
            seq_stats = ";".join(_seq_elements[i] for i in [0, 2, 3])
            seq_selected_stats.append(seq_stats.replace(">", ""))
            selected.append(f"{seq_append}\n")
        selected_sequence = "\n".join(selected)
        selected_sequence_stats = "|".join(seq_selected_stats)

    return render_template(
        "vquest_analysis.html",
        seqs=selected_sequence,
        sample_id=sample_id,
        _id=_id,
        selected_sequence_stats=selected_sequence_stats,
    )


@main_bp.route("/vquest_results/<string:sample_id>", methods=["POST"])
@login_required
def vquest_results(sample_id: str):
    results_dir = cll_app.config["ANALYSIS_OUTDIR"]
    _id = request.args.get("_id")
    sub_num = (
        request.args.get("sub_num") if request.args.get("sub_num") is not None else -1
    )
    selected_sequence_stats = None
    submission_id = ResultsController.get_submission_id(_id, num=sub_num)

    if request.method == "POST":
        submission_id = ResultsController.get_submission_id(_id, num=None)

        vquest_payload = VQuest.process_config(request.form.to_dict())

        selected_sequence_stats = vquest_payload["selected_seqs_merging_rate"]
        _selected_sequences_merging_rate = (
            selected_sequence_stats.split("|")
            if selected_sequence_stats is not None
            else None
        )
        selected_sequences_merging_rate = {
            elem.split(";")[0]: elem.split(";")[1:]
            for elem in _selected_sequences_merging_rate
            if _selected_sequences_merging_rate is not None
        }

        # run full analysis and download zip results and process them
        vquest_obj = VQuest(
            vquest_payload,
            results_dir,
            sample_id,
            submission_id,
        )

        vquest_results_raw, errors = vquest_obj.run_vquest()

        # merged vquest results to insert into the database
        if not errors and vquest_results_raw is not None:
            for seq_id in vquest_results_raw[sample_id].keys():
                if (
                    seq_id != "parameters"
                    and selected_sequences_merging_rate is not None
                ):
                    vquest_results_raw[sample_id][seq_id]["summary"][
                        "Merge Count"
                    ] = int(selected_sequences_merging_rate[seq_id][0])
                    vquest_results_raw[sample_id][seq_id]["summary"][
                        "Total Reads Per"
                    ] = round(
                        float(selected_sequences_merging_rate[seq_id][1].strip("/")), 2
                    )

            if ResultsController.save_results_to_db(
                _id,
                vquest_results_raw,
                submission_id,
                vquest_obj.vquest_results_file,
            ):
                SampleListController.sample_handler.update_document(_id, "vquest", True)
        else:
            return render_template(
                "errors.html", errors=errors, sample_id=sample_id, _id=_id
            )

    # Get the results back to display in results page.
    if SampleListController.sample_handler.get_vquest_status(_id):
        return redirect(
            url_for(
                "main_bp.cll_report",
                sample_id=sample_id,
                submission_id=submission_id,
                _id=_id,
            )
        )
    else:
        flash(f"Vquest results are not available, please run your analysis", "warning")
        return redirect(url_for("main_bp.get_sequences", sample_id=sample_id))


def comment_dict(summary: str) -> dict:
    """
    Create a dictionary for the comment to be saved in the database
    """

    new_comment = {}
    new_comment["id"] = ObjectId()
    new_comment["text"] = summary
    new_comment["time_created"] = datetime.now()
    new_comment["author"] = current_user.get_fullname()
    new_comment["hidden"] = False
    new_comment["hidden_by"] = ""
    new_comment["time_hidden"] = ""
    return new_comment


@main_bp.route(
    "/save_comment/<string:sample_id>/<string:submission_id>", methods=["POST"]
)
@login_required
def save_comment(sample_id: str, submission_id: str):
    _id = request.args.get("_id")
    report_summary = request.form.get("report_summary")
    _type = request.form.get("_type")
    if _type == "save_comment" and len(report_summary) > 0:
        new_comment = comment_dict(report_summary)

        if ResultsController.save_comments(_id, submission_id, new_comment):
            flash(f"comment saved", "success")
        else:
            flash(f"There was some error saving the comment", "error")
            cll_app.logger.error(f"There was some error saving the comment")
    else:
        flash(f"Comment is empty, could not be updated.", "warning")
        cll_app.logger.warning(f"Comment is empty, could not be updated.")

    return redirect(
        url_for(
            "main_bp.cll_report",
            sample_id=sample_id,
            submission_id=submission_id,
            _id=_id,
        )
        + "#analysis_comments"
    )


@main_bp.route(
    "/suggest_comment/<string:id>/<string:submission_id>",
    methods=["POST"],
)
@login_required
def suggest_comment(id: str, submission_id: str):
    suggested_text = ReportController.generate_report_summary_text(id, submission_id)
    return jsonify({"suggested_text": suggested_text})


@main_bp.route(
    "/update_comment_status/<string:sample_id>/<string:submission_id>",
    methods=["GET"],
)
@login_required
def update_comment_status(sample_id: str, submission_id: str):
    _id = request.args.get("_id")
    comment_id = request.args.get("comment_id") or None
    query_type = request.args.get("query_type")
    if current_user.super_user_mode():
        if ResultsController.update_submission_comments_status(
            _id, submission_id, comment_id, query_type
        ):
            flash(f"comment updated", "success")
        else:
            flash(f"There was some error updating the comment", "error")
            cll_app.logger.error(f"There was some error saving the comment")

    else:
        cll_app.logger.warning(
            "The current user is not authorized to modify the data based on the group policy."
        )
        flash(
            "The current user is not authorized to modify the data based on the group policy.",
            "warning",
        )

    return redirect(
        url_for(
            "main_bp.cll_report",
            sample_id=sample_id,
            submission_id=submission_id,
            _id=_id,
        )
        + "#analysis_comments"
    )


@main_bp.route("/cll_report/<string:sample_id>", methods=["GET", "POST"])
@login_required
def cll_report(sample_id: str):
    _id = request.args.get("_id")
    results_comments = ""
    _type = request.args.get("_type") or None
    submission_id = request.args.get(
        "submission_id"
    ) or ResultsController.get_submission_id(_id, num=-1)

    sample = ReportController.sample_handler.get_sample(_id)

    if request.method == "POST":
        report_summary = request.form.get("report_summary")
        _type = request.form.get("_type")
    else:
        report_summary = ""

    # get results if already exits in the database

    if ReportController.sample_handler.get_vquest_status(_id):
        results_parameters = ReportController.get_parameters_for_report(
            _id, submission_id
        )
        results_summary = ReportController.get_summary_for_report(_id, submission_id)
        results_comments = ReportController.get_comments_for_report(_id, submission_id)

        if results_parameters is None or results_summary is None:
            ReportController.sample_handler.update_document(_id, "vquest", False)
            flash(f"No Results in the database for the sample {sample_id}", "error")
            cll_app.logger.error(
                f"No Results in the database for the sample {sample_id}"
            )
            return render_template(
                "errors.html",
                errors=[
                    f"There is some issue with the information in the database. It looks it is incorrect. The results are not available in the database"
                ],
                sample_id=sample_id,
                _id=_id,
            )

        logo_base64 = create_base64_logo(cll_app.config["LOGO_PATH"])
        antibody_base64 = create_base64_logo(cll_app.config["ANTIBODY_LOGO_PATH"])
        html_file_path = ReportController.get_html_filename(_id, submission_id)
        html_file_name = os.path.basename(html_file_path)
        report_id = html_file_name.replace(".html", "")

        report_docs = ReportController.sample_handler.get_cll_reports(
            _id
        )  # for sample collections

        report_date = datetime.now()

        # To show a preview sign in the report
        if _type == "preview":
            preview = True
        else:
            preview = False

        try:
            if _type == "preview" or _type == "export":
                html = render_template(
                    "cll_report.html",
                    results_summary=results_summary,
                    sample_id=sample_id,
                    report_id=report_id,
                    report_summary=report_summary,
                    report_date=str(report_date).split(" ")[0],
                    logo_base64=logo_base64,
                    antibody_base64=antibody_base64,
                    submission_id=submission_id,
                    sample=sample,
                    preview=preview,
                )

            if _type == "preview":
                return html
            elif _type == "export":
                with open(html_file_path, "w") as html_out:
                    html_out.write(html)

                report_docs[report_id] = {}
                report_docs[report_id]["path"] = html_file_path
                report_docs[report_id]["date_created"] = report_date
                report_docs[report_id]["submission_id"] = submission_id
                report_docs[report_id]["created_by"] = current_user.get_fullname()
                report_docs[report_id]["hidden"] = False
                report_docs[report_id]["hidden_by"] = None
                report_docs[report_id]["time_hidden"] = None
                report_docs[report_id]["summary"] = report_summary
                ReportController.sample_handler.update_document(_id, "report", True)
                ReportController.sample_handler.update_document(
                    _id, "cll_reports", report_docs
                )

                if len(report_summary) > 0:
                    new_comment = comment_dict(report_summary)
                    if ResultsController.save_comments(_id, submission_id, new_comment):
                        pass
                    else:
                        cll_app.logger.error(f"There was some error saving the comment")

                flash(
                    f"Report with id: {report_id} save to the disk and added to the database",
                    "success",
                )
                return redirect(url_for("main_bp.cll_genie"))
            else:
                return render_template(
                    "vquest_results.html",
                    results_parameters=results_parameters,
                    results_summary=results_summary,
                    sample_id=sample_id,
                    _id=_id,
                    report_id=report_id,
                    report_summary=report_summary,
                    results_comments=results_comments,
                    submission_id=submission_id,
                )
        except Exception as e:
            flash(f"Report cannot be created", "error")
            cll_app.logger.error(f"Report cannot be created due to error: {str(e)}")
            return render_template(
                "errors.html", errors=[str(e)], sample_id=sample_id, _id=_id
            )

    else:
        flash(
            f"Cannot create report, Vquest results are not available, please run your analysis",
            "error",
        )
        return redirect(url_for("main_bp.get_sequences", sample_id=sample_id, _id=_id))


@main_bp.route("/negative_report/<string:sample_id>", methods=["POST", "GET"])
@login_required
def negative_report(sample_id: str):
    _id = request.args.get("_id")
    sample = ReportController.sample_handler.get_sample(_id)
    report_summary = ""
    results_summary = None

    negative_report_status = ReportController.sample_handler.negative_report_status(_id)
    html_file_path = ReportController.get_html_filename(_id, 0, neg=True)
    html_file_name = os.path.basename(html_file_path)
    report_id = html_file_name.replace(".html", "")
    report_date = datetime.now()

    if request.method == "POST":
        report_summary = request.form.get("negative_report_comment")

    if not negative_report_status:
        try:
            html = render_template(
                "cll_report.html",
                sample_id=sample_id,
                report_id=report_id,
                report_summary=report_summary,
                results_summary=results_summary,
                report_date=str(report_date).split(" ")[0],
            )

            with open(html_file_path, "w") as html_out:
                html_out.write(html)

            update_neg_report = {
                "report_id": report_id,
                "path": html_file_path,
                "date_created": report_date,
                "summary": report_summary,
                "created_by": current_user.get_fullname(),
            }

            ReportController.sample_handler.update_document(
                _id, "negative_report", update_neg_report
            )
            SampleListController.sample_handler.update_document(
                _id, "is_eligible_for_vquest", False
            )
            ReportController.sample_handler.update_document(_id, "report", True)
            flash(
                f"Report with id: {report_id} save to the disk and added to the database",
                "success",
            )
            return redirect(url_for("main_bp.cll_genie"))
        except Exception as e:
            flash(f"Report cannot be created", "error")
            cll_app.logger.error(f"Report cannot be created due to error: {str(e)}")
            return render_template(
                "errors.html", errors=[str(e)], sample_id=sample_id, _id=_id
            )
    else:
        flash(f"Report already exits", "info")
        report_doc = ReportController.sample_handler.get_negative_report(_id)
        if os.path.exists(report_doc["path"]):
            head, tail = os.path.split(report_doc["path"])
            return send_from_directory(head, tail)
        else:
            flash(f"Report does not exist in the given path", "info")
            return render_template(
                "errors.html",
                errors=[
                    f"Report does not exist in the given path: {report_doc['path']}"
                ],
                sample_id=sample_id,
                _id=_id,
            )


@main_bp.route("/report_view/<string:sample_id>")
@login_required
def report_view(sample_id: str):
    """
    show the latest report from the database.
    """
    _id = request.args.get("_id")
    report_id = request.args.get("report_id")

    report_file = ReportController.get_latest_report(_id, report_id)

    if report_file is None:
        flash(
            f"There are no reports available in the database for the sample {sample_id}. Go to home page and create a report",
            "error",
        )
        return redirect(url_for("main_bp.cll_genie"))
    else:
        head, tail = os.path.split(report_file)
        return send_from_directory(head, tail)


@main_bp.route("/toggle_report_status/<string:db_id>")
@login_required
def toggle_report_status(db_id: str):
    """
    Set samples as analyzed/not analyzed
    """

    def check_report_status_arg(arg):
        arg = arg.strip().lower()

        if arg == "true":
            return True
        elif arg == "false":
            return False
        else:
            return None

    set_report = request.args.get(
        "set_analyzed", default=None, type=check_report_status_arg
    )

    cll_app.logger.info(f"Setting report ({db_id}) to {set_report}")
    flash(f"Setting report ({db_id}) to {set_report}", "info")

    if set_report is not None:
        ReportController.sample_handler.update_document(db_id, "report", set_report)

    return redirect(url_for("main_bp.cll_genie"))


@main_bp.route("/update_report/<string:id>/<string:report_id>", methods=["GET"])
@login_required
def update_report(id: str, report_id: str):
    """
    Update the report status as hidden or show its contents from the samples database
    """
    sample_id = ReportController.sample_handler.get_sample_name(id)
    query_type = request.args.get("query_type")
    user_name = current_user.get_fullname()

    if current_user.super_user_mode():
        if SampleListController.sample_handler.update_report(
            id, report_id, query_type, user_name
        ):
            ReportController.update_report_status(id)
            flash(f"Report updated for the id {report_id}", "success")
        else:
            flash(
                f"There was some error updating the report for the id {report_id}",
                "error",
            )
            cll_app.logger.error(
                f"There was some error updating the report for the id {report_id}"
            )

    else:
        cll_app.logger.warning(
            "The current User is not authorized to modify the data based on the group policy."
        )
        flash(
            "The current User is not authorized to modify the data based on the group policy.",
            "warning",
        )

    return redirect(
        url_for("main_bp.sample", sample_id=sample_id, _id=id) + "#available_reports"
    )


@main_bp.route("/delete_negative_report/<string:sample_id>")
@login_required
def delete_negative_report(sample_id: str):
    """
    Delete the negative report and its contents from the samples database
    """
    _id = request.args.get("_id")
    if current_user.super_user_mode():
        status = ReportController.delete_cll_negative_report(_id)
        if status:
            cll_app.logger.info(
                f"No result report deleted successfully for the sample id {sample_id}"
            )
            flash(
                f"No result report deleted successfully for the sample id {sample_id}",
                "success",
            )

            ReportController.update_report_status(_id)

        else:
            # need more work on this
            cll_app.logger.error(
                f"No result report deletion failed for the sample id {sample_id}"
            )
            flash(
                f"No result report deleted failed for the sample id {sample_id}",
                "error",
            )
    else:
        cll_app.logger.warning(
            "The current User is not authorized to modify the data based on the group policy."
        )
        flash(
            "The current User is not authorized to modify the data based on the group policy.",
            "warning",
        )

    return redirect(url_for("main_bp.sample", sample_id=sample_id, _id=_id))


@main_bp.route("/delete_results/<string:id>/<string:sub_id>")
@login_required
def delete_results(id: str, sub_id: str):
    """
    Delete the results for the submissions or all the submission and its contents from the analysis database and samples database
    """
    sample_id = request.args.get("sample_id")

    if current_user.super_user_mode():
        status = ResultsController.delete_cll_results(id, sub_id)
        if status:
            cll_app.logger.info(
                f"Results deleted successfully for the sample id {sample_id} of submission id {sub_id}"
            )
            flash(
                f"Results deleted successfully for the sample id {sample_id} of submission id {sub_id}",
                "success",
            )

            ReportController.update_report_status(id)
            ResultsController.update_vquest_status(id)
        else:
            cll_app.logger.error(
                f"Results deletion failed for the sample id {sample_id} of submission id {sub_id}"
            )
            flash(
                f"Results deletion failed for the sample id {sample_id} of submission id {sub_id}",
                "error",
            )
    else:
        cll_app.logger.warning(
            "The current User is not authorized to modify the data based on the group policy."
        )
        flash(
            "The current User is not authorized to modify the data based on the group policy.",
            "warning",
        )

    return redirect(url_for("main_bp.sample", sample_id=sample_id, _id=id))
