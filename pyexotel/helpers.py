from typing import List

from .exceptions import ValidationError
from .validators import validate_phone_number


def validate_list_of_nums(numbers: List[str]):
    if not isinstance(numbers, list):
        raise ValueError("numbers argument should be a list of strings")
    invalid = []
    for num in numbers:
        try:
            validate_phone_number(num)
        except ValidationError:
            invalid.append(num)

    if len(invalid) > 0:
        raise ValidationError(
            "Received invalid numbers as per E.164 format, please check")


def get_error_description(data: dict, version: str = None):
    if version == "v1":
        error_description = data["RestException"]["Message"]
    else:
        if isinstance(data["response"], list):
            error_description = data["response"][0]["error_data"]["description"]
        elif isinstance(data["response"], dict):
            error_description = data["response"]["error_data"]["description"]
    return error_description


def get_contact_sids(data: dict) -> List[str]:
    sids = [i["data"]["sid"] for i in data["response"]]
    return sids


def get_list_id(data: dict) -> str:
    return data["response"][0]["data"]["list_id"]
