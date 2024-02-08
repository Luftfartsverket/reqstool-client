# Copyright © LFV

import logging
import os
import tempfile
from itertools import chain
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import requests
from requests_file import FileAdapter

from reqstool.common.dataclasses.urn_id import UrnId
from reqstool.models.raw_datasets import RawDataset
from reqstool.models.requirements import VARIANTS, RequirementData
from reqstool.models.svcs import SVCData


class TempDirectoryUtil:
    tmpdir: tempfile.TemporaryDirectory = tempfile.TemporaryDirectory()
    count: int = 0

    @staticmethod
    def get_path() -> Path:
        return Path(TempDirectoryUtil.tmpdir.name)

    @staticmethod
    def get_suffix_path(suffix: str) -> Path:
        new_path = Path(
            os.path.join(
                TempDirectoryUtil.tmpdir.name,
                str(TempDirectoryUtil.count),
                suffix,
            )
        )
        new_path.mkdir(parents=True, exist_ok=True)
        TempDirectoryUtil.count += 1

        return new_path


def open_file_https_file(uri: str):
    session = requests.Session()
    session.mount("file://", FileAdapter())

    if not (uri.startswith("https://")):
        path: Path = Path(uri)

        uri = "file://" + str(path.absolute())

    response = session.get(uri)

    return response


def flatten_all_reqs(raw_datasets: Dict[str, RawDataset]) -> Dict[str, RequirementData]:
    """Returns a Dict of all filtered RequirementData of all imported models

    Args:
        models (Dict[str, RawDataset]): The models where filtered RequirementData should be extracted

    Returns:
        Dict[str, RequirementData]: All filtered RequirementData from models
    """
    all_reqs = {}
    for model_id, model_info in raw_datasets.items():
        for req_id, req_info in model_info.requirements_data.requirements.items():
            # unique_id = model_id + ":" + req_id
            if req_id not in all_reqs:
                all_reqs[req_id] = req_info

    return all_reqs


def flatten_all_reqs_unfiltered(raw_datasets: Dict[str, RawDataset]) -> Dict[str, RequirementData]:
    """Returns a Dict of all RequirementData of all imported models

    Args:
        models (Dict[str, RawDataset]): The models where RequirementData should be extracted

    Returns:
        Dict[str, RequirementData]: All RequirementData from models
    """
    all_reqs = {}
    for model_id, model_info in raw_datasets.items():
        for req_id, req_info in model_info.requirements_data.requirements.items():
            unique_id = model_id + ":" + req_id
            if unique_id not in all_reqs:
                all_reqs[unique_id] = req_info

    return all_reqs


def flatten_all_svcs(raw_datasets: Dict[str, RawDataset]) -> Dict[str, SVCData]:
    """Returns a Dict of all filtered SVCData of all imported models

    Args:
        models (Dict[str, RawDataset]): The models where the filtered SVCData should be extracted

    Returns:
        Dict[str, SVCData]: All filtered SVCData from models
    """
    all_svcs = {}

    for model_id, model_info in raw_datasets.items():
        if model_is_external(raw_datasets=model_info):
            continue
        if model_info.svcs_data is not None:
            for svc_id, svc in model_info.svcs_data.cases.items():
                if svc_id not in all_svcs:
                    all_svcs[svc_id] = svc

    return all_svcs


def flatten_all_svcs_unfiltered(raw_datasets: Dict[str, RawDataset]) -> Dict[str, SVCData]:
    """Returns a Dict of all SVCData of all imported models

    Args:
        models (Dict[str, RawDataset]): The models where the SVCData should be extracted

    Returns:
        Dict[str, SVCData]: All SVCData from models
    """
    all_svcs = {}

    for model_id, model_info in raw_datasets.items():
        if model_is_external(raw_datasets=model_info):
            continue
        if model_info.svcs_data is not None:
            for svc_id, svc in model_info.svcs_data.cases.items():
                unique_id = model_id + ":" + svc.id
                if unique_id not in all_svcs:
                    all_svcs[unique_id] = svc

    return all_svcs


def generate_all_svc_req_refs(raw_datasets: Dict[str, RawDataset]) -> Dict[str, str]:  # NOSONAR
    """Generates a collection where the unique Requirement ID's are coupled with all filtered SVC's refering to them

    Args:
        models (Dict[str, RawDataset]): collection of all RawDatasets that needs processing

    Returns:
        Dict[str, str]: A collection of RequirmentID's and it's related SVC ID's
    """
    svc_req_refs = {}
    for model_id, model_info in raw_datasets.items():
        for req_id, svc_info in model_info.filtered_svcs.items():
            for svc in svc_info:
                unique_id = model_id + ":" + svc.id
                for req in svc.requirement_ids:
                    if ":" not in req:
                        unique_ref_id = model_id + ":" + req
                    else:
                        unique_ref_id = req
                    if unique_ref_id not in svc_req_refs:
                        svc_req_refs[unique_ref_id] = [unique_id]
                    else:
                        svc_req_refs[unique_ref_id].append(unique_id)
    return svc_req_refs


def flatten_list(list_to_flatten: Iterable) -> List[any]:
    return list(chain.from_iterable(list_to_flatten))


def model_is_external(raw_datasets: RawDataset) -> bool:
    return raw_datasets.requirements_data.metadata.variant.value == VARIANTS.EXTERNAL.value


def string_contains_delimiter(string: str, delimiter: str) -> bool:
    return delimiter in string


def get_after_colon_or_original(input_string):
    parts = input_string.rsplit(":", 1)  # Split only once from the right
    if len(parts) > 1:
        return parts[-1]
    return input_string


def convert_ids_to_urn_id(urn: str, ids: Sequence[str]) -> List[UrnId]:
    ids_as_urn_ids = []

    for id in ids:
        urn_id = convert_id_to_urn_id(urn, id)

        ids_as_urn_ids.append(urn_id)

    return ids_as_urn_ids


def convert_id_to_urn_id(urn: str, id: str) -> UrnId:
    if ":" in id:
        split = id.split(":")
        urn_id = UrnId(urn=split[0], id=split[1])
    else:
        # if no ":" in svc_id, append with specified urn
        urn_id = UrnId(urn=urn, id=id)

    return urn_id


# Checks conditions for filtered ids and logs an error if they are not properly formatted
def check_ids_to_filter(ids: Sequence[str], current_urn: str) -> Sequence[str]:
    checked_ids: List[str] = []
    for id in ids:
        if ":" in ids:
            split = id.split(":")
            if split[0] is not current_urn:
                logging.error(f"Id cannot contain a ':' and a reference to another urn. The {id} will be filtered out")
            else:
                checked_ids.append(id)
        else:
            id_with_urn = current_urn + ":" + id
            checked_ids.append(id_with_urn)
    return checked_ids


def append_data_item_to_dict_list_entry(dictionary: dict, key, data: str):
    if key not in dictionary:
        logging.debug(f"Creating empty dict with key {key} for: {dictionary}")
        dictionary[key] = []

    dictionary[key].append(data)


def extend_data_sequence_to_dict_list_entry(dictionary: dict, key, data: Sequence):
    if key not in dictionary:
        logging.debug(f"Creating empty dict with key {key} for: {dictionary}")
        dictionary[key] = []

    dictionary[key].extend(data)


def create_accessible_nodes_dict(graph: Dict[str, List[str]]):
    """
    Creates a dictionary containing _all_ nodes that can be accessed from each node in the graph.

    Parameters:
    - graph (dict): A dictionary representing the graph where keys are nodes and values are lists
                    of nodes that can be accessed from the corresponding key.

    Returns:
    - dict: A dictionary where keys are nodes, and values are lists of _all_ nodes that can be accessed
            from the corresponding key.
    """

    def get_accessible_nodes(graph: Dict[str, List[str]], start_node: str):
        """
        Performs breadth-first search to find all nodes accessible from a given starting node.

        Parameters:
        - graph (dict): A dictionary representing the graph.
        - start_node: The starting node for the breadth-first search.

        Returns:
        - list: A list of nodes accessible from the starting node.
        """
        visited = set()
        queue = [start_node]
        accessible_nodes = []

        while queue:
            current_node = queue.pop(0)
            if current_node not in visited:
                visited.add(current_node)
                queue.extend(graph[current_node])
                if current_node != start_node:
                    accessible_nodes.append(current_node)

        return accessible_nodes

    accessible_nodes_dict = {}

    for node in graph:
        accessible_nodes = get_accessible_nodes(graph, node)
        accessible_nodes_dict[node] = accessible_nodes

    return accessible_nodes_dict
