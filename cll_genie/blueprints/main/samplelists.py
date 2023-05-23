from typing import List, Optional, Dict
from copy import deepcopy
import pymongo  # type: ignore
from cll_genie.extensions import sample_handler
from flask import current_app as cll_app


class SampleListController:
    """
    Create cll_genie samplelists for main.views and annotate with CDM data
    """

    sample_handler = sample_handler

    @staticmethod
    def get_unanalyzed_sample_list(
        query: Optional[dict] = None, n_skip: int = 0, page_size: int = 0
    ) -> List[dict]:
        """
        Get list of cll_genie samples and annotate with CDM data
        """

        if query is None:
            query = {}
        else:
            query = deepcopy(query)

        query["report"] = False

        samples_false = SampleListController.get_sample_list(
            query, n_skip=n_skip, page_size=page_size
        )

        sample_false_count = SampleListController.get_sample_list(query)

        #samples_false = SampleListController._annotate_samples_with_cdm_data(samples_false)
        duplicate_count = [
            SampleListController._get_duplicated_samples(sample["name"]) for sample in samples_false
        ]

        for sample, count in zip(samples_false, duplicate_count):
            sample["samples_with_same_sample_id"] = count

        return samples_false, len(sample_false_count)

    @staticmethod
    def get_sample_list(
        query: Optional[dict] = None, n_skip: int = 0, page_size: int = 0
    ) -> pymongo.collection.Cursor:
        """
        Get and prepare sample list for display
        """
        if query is None:
            query = {}
        else:
            query = deepcopy(query)

        cll_app.logger.debug(query)
        samples = (
            SampleListController.sample_handler.get_samples(query)
            #.sort("date_added", -1)
            .sort([
                    ("date_added", -1),
                    ("name", 1)
                ])
            .skip(n_skip)
            .limit(page_size)
        )
        samples = list(samples)
        return samples

    @staticmethod
    def _get_duplicated_samples(sample_id: str) -> Optional[List[dict]]:
        """
        Given a sample id, detect and return list samples sharing the same sample id.

        Returns None if no duplicates found.
        """
        results = SampleListController.sample_handler.get_samples({"name": sample_id})
        results = list(results)

        if len(results) < 2:
            return None

        return results