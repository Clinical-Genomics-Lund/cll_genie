from pathlib import Path
import requests
from requests_html import HTML
from zipfile import ZipFile
from flask import current_app as cll_app
from copy import deepcopy
import pandas as pd
import io
import re
import os


class VQuest:
    URL = cll_app.config["VQUEST_URL"]

    def __init__(
        self,
        config: dict,
        output_dir: str,
        sample_id: str,
        submission_id: str,
    ):
        self.sample_id = sample_id
        self.payload = config
        self.output_dir = Path(
            os.path.join(output_dir, sample_id, submission_id, "vquest")
        )
        self.vquest_results_file = os.path.join(
            self.output_dir, f"{self.sample_id}.zip"
        )
        self.remove_files(self.vquest_results_file)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def remove_files(self, filename) -> None:
        if os.path.exists(filename):
            os.remove(filename)

    def run_vquest(self) -> dict:
        """Submit a request to V-QUEST.

        config should be a dictionary key/value pairs to use in the request.  See
        https://www.imgt.org/IMGT_vquest/url_request for a full list, organized into
        sections. Currently resultType must be "excel" and xv_outputtype must be 1
        (for "Download Zip results").

        sequences are submitted to the IMGT/V-QUEST server. Each request gives us a zip
        results.
        """

        headers = {
            "Referer": f"{VQuest.URL}.html",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        }

        errors = []
        try:
            response = requests.post(VQuest.URL, data=self.payload, headers=headers)
            cll_app.logger.info(f"{response}")
            cll_app.logger.debug(f"payload: {self.payload}")
            ctype = response.headers.get("Content-Type")
            cll_app.logger.info(f"{ctype}")
            cll_app.logger.debug(f"Received data of type {ctype}")

            if response.status_code != 200:
                errors.append(f"Request failed with status code {response.status_code}")

            elif ctype and "text/html" in ctype:
                content_type_parts = ctype.split(";")
                for part in content_type_parts:
                    if "charset=" in part:
                        charset = part.split("charset=")[-1].strip()
                        break

                default_encoding = (
                    "utf-8"  # You can change this to your desired default encoding
                )
                html = None
                try:
                    html = response.content.decode(charset)
                except LookupError:
                    html = response.content.decode(default_encoding)

                cll_app.logger.info(f"\n{html}\n")

                # Match elements with class="error" or class="error-message" within other tags
                pattern = r'<ul\s+class="errorMessage">\s*(.*?)\s*</ul>'
                matches = re.findall(pattern, html, re.DOTALL)
                if matches:
                    errors.extend(re.findall(r"<span>(.*?)</span>", matches[0]))

                try:
                    for div in HTML(html).find("div.form_error"):
                        errors.append(div.text)
                except:
                    pass
        except requests.exceptions.ConnectionError as e:
            errors.append(
                "Request failed with error 'Failed to establish a new connection'"
            )

        if errors:
            for error in errors:
                cll_app.logger.error(error)

            return None, errors
        else:
            try:
                self.save_zip_content(response.content)
                return self.process_zip_results_for_report(), None
            except FileNotFoundError:
                cll_app.logger.error("File not found on the server")
                return None, "File not found on the server"

    def save_zip_content(self, zip_data) -> None:
        """
        convert the html response content to a zip file
        """
        # create a binary stream from the response content
        stream = io.BytesIO(zip_data)

        # extract the files from the stream and save them to disk
        with ZipFile(stream, "r") as zip_file:
            with ZipFile(self.vquest_results_file, "w") as output_zip:
                for member_name in zip_file.namelist():
                    member_content = zip_file.read(member_name)
                    output_zip.writestr(member_name, member_content)
                    output_file = Path(os.path.join(self.output_dir, member_name))
                    with output_file.open("wb") as f:
                        f.write(member_content)

    def process_zip_results_for_report(self) -> dict:
        """
        Process the results of a V-QUEST request.
        """

        parameter_dict = {}
        with open(os.path.join(self.output_dir, "11_Parameters.txt"), "r") as f:
            for line in f:
                parts = line.strip().split("\t")
                if parts[0] == "Date" or parts[0].startswith("Nb of nucleotides"):
                    continue
                else:
                    parameter_dict[parts[0]] = parts[1]

        # processing Summary from the results
        summary_raw_df = pd.read_csv(
            os.path.join(self.output_dir, "1_Summary.txt"), sep="\t", header=0
        )
        summary_raw_df = summary_raw_df.loc[
            :, ~summary_raw_df.columns.str.contains("^Unnamed")
        ]
        summary_raw_df.fillna("", inplace=True)
        summary_raw_dict = (
            summary_raw_df.groupby("Sequence ID")
            .apply(lambda x: x.set_index("Sequence ID").to_dict("records")[0])
            .to_dict()
        )
        VQuest.replace_empty_with_none(summary_raw_dict)

        # Processing Junction results
        junction_raw_df = pd.read_csv(
            os.path.join(self.output_dir, "6_Junction.txt"), sep="\t", header=0
        )
        junction_raw_df = junction_raw_df.loc[
            :, ~junction_raw_df.columns.str.contains("^Unnamed")
        ]
        junction_raw_df.fillna("", inplace=True)
        junction_raw_dict = (
            junction_raw_df.groupby("Sequence ID")
            .apply(lambda x: x.set_index("Sequence ID").to_dict("records")[0])
            .to_dict()
        )
        VQuest.replace_empty_with_none(junction_raw_dict)

        merged_dict_raw = self.create_dict_for_mongo(
            summary_raw_dict, junction_raw_dict, parameter_dict
        )
        return merged_dict_raw

    @staticmethod
    def replace_empty_with_none(d):
        for k, v in d.items():
            if isinstance(v, dict):
                VQuest.replace_empty_with_none(v)
            elif v == "":
                d[k] = None

    def create_dict_for_mongo(self, s_dict, j_dict, p_dict):
        results_dict = {self.sample_id: {"parameters": p_dict}}

        seq_ids = s_dict.keys()

        for seq_id in seq_ids:
            results_dict[self.sample_id][seq_id] = {
                "summary": s_dict[seq_id],
                "junction": j_dict[seq_id],
            }

        return results_dict

    @staticmethod
    def process_config(config_dict):
        vquest_payload = deepcopy(config_dict)
        for key, value in vquest_payload.items():
            if value == "True" or value == "true":
                vquest_payload[key] = True
            elif value == "False" or value == "false":
                vquest_payload[key] = False
            elif value == "None" or value == "null":
                vquest_payload[key] = None
            elif value.isdigit() or (
                value.startswith("-") and value[1:].isdigit()
            ):  # for negative numbers as well
                vquest_payload[key] = int(value)
            elif value.startswith(">Seq"):
                vquest_payload[key] = value.replace("\r", "")
            else:
                pass
        return vquest_payload


class VquestError(Exception):
    """
    Vquest-related errors.  These can have one or more messages provided by the server.
    """

    def __init__(self, message, server_messages=None):
        self.message = message
        self.server_messages = server_messages
        super().__init__(self.message)
