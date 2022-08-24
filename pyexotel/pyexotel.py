from datetime import datetime
from multiprocessing.sharedctypes import Value
from subprocess import call
from typing import List
from urllib.parse import urljoin

import pytz
import requests
from requests.auth import HTTPBasicAuth

from .exceptions import *
from .helpers import validate_list_of_nums
from .validators import validate_url


class Schedule:
    def __init__(self, send_at: datetime = None, end_at: datetime = None):
        self.send_at = send_at
        self.end_at = end_at

    def _is_valid_arg(self, arg, value):
        if not isinstance(value, datetime):
            raise ValueError("{arg} should be of type datetime not {_type}".format(
                arg=arg, _type=type(value)))
        return value

    def _format_datetime(self, value):
        ist = pytz.timezone("Asia/Kolkata")
        return value.astimezone(ist).isoformat()

    @property
    def send_at(self):
        return self._send_at

    @property
    def end_at(self):
        return self._end_at

    @send_at.setter
    def send_at(self, value):
        self._send_at = self._is_valid_arg("send_at", value)

    @end_at.setter
    def end_at(self, value):
        self._end_at = self._is_valid_arg("end_at", value)

    def to_json(self):
        output = {
            "send_at": self._format_datetime(self.send_at)
        }
        if self.end_at is not None:
            output["end_at"] = self._format_datetime(self.end_at)
        return output


class Retry:
    def __init__(self, number_of_retries: int, interval_mins: int, on_status: List[str], mechanism: str = "Linear"):
        self.number_of_retries = number_of_retries
        self.interval_mins = interval_mins
        self.on_status = on_status
        self.mechanism = mechanism

    @property
    def on_status(self):
        return self._on_status

    @property
    def mechanism(self):
        return self._mechanism

    @on_status.setter
    def on_status(self, value):
        self._on_status = self._is_valid_status(value)

    @mechanism.setter
    def mechanism(self, value):
        self._mechanism = self._is_valid_mechanism(value)

    def _is_valid_status(self, value):
        values = ["busy", "failure", "no-answer"]

        if not isinstance(value, list):
            raise TypeError(
                "on_status argument should be a list")

        for v in value:
            if v not in values:
                raise ValueError(
                    "{v} is not a valid value for status".format(v=v))
        return value

    def _is_valid_mechanism(self, value):
        values = ["Linear", "Exponential"]
        if value not in values:
            raise ValueError(
                "{v} is not a valid value for mechanism".format(v=value))
        return value

    def to_dict(self):
        return self.__dict__


class Exotel:
    def __init__(self, sid: str, key: str, token: str, baseurl: str = "https://api.exotel.com"):
        self.sid = sid
        self.baseurl = urljoin(baseurl, "v2/accounts/{sid}/".format(sid=sid))
        self.auth_headers = HTTPBasicAuth(key, token)

    def __call_api(self, method: str, endpoint: str, data: dict = None) -> dict:

        if data is not None:
            if method in ["POST", "PUT", "PATCH"]:
                response = requests.request(
                    method=method, url=endpoint, auth=self.auth_headers, json=data)
            elif method == "GET":
                response = requests.request(
                    method=method, url=endpoint, auth=self.auth_headers, params=data)
        else:
            response = requests.request(
                method=method, url=endpoint, auth=self.auth_headers)

        if response.status_code == 401:
            raise AuthenticationFailed
        elif response.status_code == 403:
            raise PermissionDenied(
                "Your credentials are valid, but you don't have access to the requested resource.")
        elif response.status_code == 402:
            raise PaymentRequired(
                "The action is not available on your plan, or you have exceeded usage limits for your current plan.")
        elif response.status_code == 429:
            raise Throttled("Request was throttled.")

        return response.json()

    def get_campaign_details(self, campaign_id: str) -> dict:
        return self.__call_api("GET", urljoin(self.baseurl, 'campaigns/{cid}'.format(cid=campaign_id)))

    def get_campaign_call_details(self, campaign_id: str):
        return self.__call_api("GET", urljoin(self.baseurl, 'campaigns/{cid}/call-details'.format(cid=campaign_id)))

    def get_bulk_campaign_details(self) -> dict:
        return self.__call_api("GET", urljoin(self.baseurl, 'campaigns'))

    def create_campaign(self, caller_id: str, app_id: str, _from: List[str] = None, lists: List[str] = None, name: str = None, call_duplicate_numbers: bool = None, schedule: Schedule = None, campaign_type: str = "static", call_status_callback: str = None, call_schedule_callback: str = None, status_callback: str = None, retry: Retry = None) -> dict:
        campaign = {
            "caller_id": caller_id,
            "campaign_type": campaign_type,
            "url": f"http://my.exotel.com/{self.sid}/exoml/start_voice/{app_id}",
        }

        if (_from is not None) and (lists is not None):
            raise ValueError(
                "Both _from and lists can't be provided at the same, only either can be passed")

        if (_from is None) and (lists is None):
            raise ValueError(
                "Either _from or lists must be passed, can't create campaign without it")

        if _from is not None:
            campaign["from"] = _from

        if lists is not None:
            campaign["lists"] = lists

        if call_duplicate_numbers is not None:
            campaign["call_duplicate_numbers"] = call_duplicate_numbers

        if name is not None:
            campaign["name"] = name

        if schedule is not None:
            campaign["schedule"] = schedule.to_json()

        if call_status_callback is not None:
            campaign["call_status_callback"] = validate_url(
                call_status_callback)

        if call_schedule_callback is not None:
            campaign["call_schedule_callback"] = validate_url(
                call_schedule_callback)

        if status_callback is not None:
            campaign["status_callback"] = validate_url(status_callback)

        if retry is not None:
            campaign["retries"] = retry.to_dict()

        payload = {"campaigns": [campaign]}

        return self.__call_api("POST", urljoin(self.baseurl, 'campaigns'), data=payload)

    def create_campaign_with_list(self, numbers: List[str], list_name: str, caller_id: str, app_id: str, **kwargs) -> dict:
        validate_list_of_nums(numbers)
        list_id = self.create_list(name=list_name, numbers=numbers)
        lists = [list_id]
        return self.create_campaign(caller_id=caller_id, app_id=app_id, lists=lists, **kwargs)

    def delete_campaign(self, campaign_id: str) -> dict:
        return self.__call_api("DELETE", urljoin(self.baseurl, "campaigns/{cid}".format(cid=campaign_id)))

    def get_contact_details(self, contact_id: str) -> dict:
        return self.__call_api("GET", urljoin(self.baseurl, "contacts/{cid}".format(cid=contact_id)))

    def create_contacts(self, numbers: List[str]) -> List[str]:
        validate_list_of_nums(numbers)
        contacts_url = urljoin(self.baseurl, "contacts")
        payload = {
            "contacts": [
                {"number": num} for num in numbers
            ]
        }
        data = self.__call_api("POST", contacts_url, data=payload)
        sids = [i["data"]["sid"] for i in data["response"]]
        return sids

    def delete_contact(self, sid: str) -> dict:
        return self.__call_api("DELETE", urljoin(self.baseurl, "contacts/{cid}".format(cid=sid)))

    def delete_contacts(self, sids: str) -> List[dict]:
        responses = []
        for sid in sids:
            responses.append(self.delete_contact(sid))

        return responses

    def add_contacts_to_list(self, sids: List[str], list_id: str) -> dict:
        payload = {
            "contact_references": [
                {"contact_sid": sid} for sid in sids
            ]
        }
        return self.__call_api("POST",
                               urljoin(self.baseurl, "lists/{list_id}/contacts".format(list_id=list_id)), data=payload)

    def create_list(self, name: str, tag: str = "demo", numbers: List[str] = None) -> str:
        validate_list_of_nums(numbers)
        payload = {
            "lists": [
                {
                    "name": name,
                    "tag": tag
                }
            ]
        }
        data = self.__call_api("POST", urljoin(self.baseurl, "lists"),
                               data=payload)

        if data["response"][0]["code"] == 409:
            description = data["response"][0]["error_data"]["description"]
            raise UniqueViolationError(description)

        list_id = data["response"][0]["data"]["sid"]

        if numbers is not None:
            contact_sids = self.create_contacts(numbers)
            response = self.add_contacts_to_list(contact_sids, list_id)

        return list_id

    def delete_list(self, list_id: str) -> dict:
        return self.__call_api("DELETE", urljoin(self.baseurl, "lists/{list_id}".format(list_id=list_id)))
