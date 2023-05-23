from s4.clarity import LIMS, ClarityException  # type: ignore

from flask import Flask
from flask import current_app as cll_app
from pprint import pformat
from typing import Dict, Optional


class Clarity:
    """
    Fetch clarity sample data
    """

    def __init__(self):
        self.api = None

    def initialize(
        self,
        clarity_host: str,
        clarity_username: str,
        clarity_password: str,
        dry_run: bool = False,
    ) -> None:
        self.api = LIMS(
            clarity_host, clarity_username, clarity_password, dry_run=dry_run
        )

    def init_from_app(self, flask_app: Flask) -> None:
        credentials = {
            "clarity_host": flask_app.config["CLARITY_HOST"],
            "clarity_username": flask_app.config["CLARITY_USER"],
            "clarity_password": flask_app.config["CLARITY_PASSWORD"],
        }

        missing_credentials = [
            key for key, value in credentials.items() if value is None
        ]

        if missing_credentials:
            cll_app.logger.error(
                "Cannot initialize ClarityDB. Following credentials undefined: "
                f"{', '.join(missing_credentials)}"
            )

            return None

        self.initialize(
            clarity_host=flask_app.config["CLARITY_HOST"],
            clarity_username=flask_app.config["CLARITY_USER"],
            clarity_password=flask_app.config["CLARITY_PASSWORD"],
            dry_run=True,  # Ensure read-only operations
        )

    def sample_udfs_from_sample_id(self, clarity_id) -> Optional[Dict]:
        if self.api is None:
            cll_app.logger.error(
                f"Cannot retrieve sample {clarity_id}: clarity API not initialized."
            )
            return None

        try:
            sample = self.api.sample(clarity_id)
            output = dict(sample.fields.items())
        except ClarityException:
            cll_app.logger.error(
                f"Error when retrieving sample data from Clarity for {clarity_id}"
            )
            return None

        cll_app.logger.debug(f"Returning clarity output: {pformat(output)}")
        return output

    def sample_udfs_from_sample_obj(self, sample_obj: dict) -> Optional[Dict]:
        return self.sample_udfs_from_sample_id(sample_obj.get("clarity_id"))
