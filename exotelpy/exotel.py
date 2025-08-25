import logging
from copy import deepcopy
from datetime import datetime
from typing import List
from urllib.parse import urljoin

import requests
from requests.auth import HTTPBasicAuth

from .exceptions import *
from .helpers import (
    batch_contacts,
    get_contact_sids,
    get_error_description,
    get_list_id,
    validate_list_of_nums,
)
from .validators import validate_url

logger = logging.getLogger("exotelpy")


class Schedule:
    """
    Utility class for passing schedule of campaigns in a uniform manner

    Args:
        send_at (datetime, optional): Time when the campaign should start. Defaults to None.
        end_at (datetime, optional): Time when the campaign should end. Defaults to None.
    """

    def __init__(self, send_at: datetime = None, end_at: datetime = None):
        self.send_at = send_at
        self.end_at = end_at

    @staticmethod
    def _is_valid_arg(arg, value):
        if not isinstance(value, datetime):
            raise ValueError("{arg} should be of type datetime not {_type}".format(
                arg=arg, _type=type(value)))
        else:
            if value.utcoffset() is None:
                raise ValueError(
                    "{arg} received a naive datetime, please pass tzinfo".format(
                        arg=arg))
        return value

    @staticmethod
    def _format_datetime(value: datetime) -> str:
        return value.isoformat(timespec="seconds")

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

    def to_json(self, sms: bool = False) -> dict:
        """
            Utility method for serializing API payload

            :meta private:
        """
        start = "send_at"
        end = "end_at"

        if sms is True:
            start = "start_time"
            end = "end_time"

        output = {
            start: self._format_datetime(self.send_at)
        }
        if self.end_at is not None:
            output[end] = self._format_datetime(self.end_at)
        return output

    def __repr__(self) -> str:
        return "Schedule(send_at='{send_at}', end_at='{end_at}')".format(
            send_at=self.send_at.isoformat(timespec="seconds"),
            end_at=self.end_at.isoformat(timespec="seconds"))


class Retry:
    """
    Utility class to pass the retry data to campaign methods

    Args:
        number_of_retries (int): The number of times a call to a phone number should be attempted
        interval_mins (int): The time interval between retries in mins
        on_status (List[str]): Determines when should campaign treat a call as an unsuccessful attempt. Could be "busy", "no-answer", "failed"
        mechanism (str, optional): Can be either "Linear" or "Exponential". If the retry should be equally spaced or exponentially. Defaults to "Linear".
    """

    def __init__(
            self, number_of_retries: int, interval_mins: int,
            on_status: List[str], mechanism: str = "Linear"):
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

    @staticmethod
    def _is_valid_status(value):
        values = ["busy", "failed", "no-answer"]

        if not isinstance(value, list):
            raise TypeError(
                "on_status argument should be a list")

        for v in value:
            if v not in values:
                raise ValueError(
                    "{v} is not a valid value for status".format(v=v))
        return value

    @staticmethod
    def _is_valid_mechanism(value):
        values = ["Linear", "Exponential"]
        if value not in values:
            raise ValueError(
                "{v} is not a valid value for mechanism".format(v=value))
        return value

    def to_dict(self) -> dict:
        return {
            "mechanism": self.mechanism,
            "on_status": self.on_status,
            "number_of_retries": self.number_of_retries,
            "interval_mins": self.interval_mins
        }

    def __repr__(self) -> str:
        return "Retry(mechanism='{mechanism}', on_status=['{on_status}'], number_of_retries={num_of_retries}, interval_mins={interval_mins})".format(
            mechanism=self.mechanism, num_of_retries=self.number_of_retries, interval_mins=self.interval_mins, on_status="','".join(self.on_status))


class Exotel:
    """Object to initialize and interact with Exotel API

    It holds the authentication details

    Args:
        sid (str): Exotel Account SID
        key (str): API Key
        token (str): API Token
        baseurl (str, optional): Account Subdomain. Defaults to "https://api.exotel.com".
    """

    def __init__(self, sid: str, key: str, token: str,
                 baseurl: str = "https://api.exotel.com"):
        self.sid = sid
        self.baseurl = baseurl
        self.auth_headers = HTTPBasicAuth(key, token)

    def __repr__(self) -> str:
        return "Exotel(sid='{sid}', baseurl='{baseurl}', key='{key}', token='{token}')".format(
            sid=self.sid, baseurl=self.baseurl, key=self.auth_headers.username, token=self.auth_headers.password)

    def __api_url(self, version: str) -> str:
        if version == "v1":
            return urljoin(self.baseurl, "v1/Accounts/{sid}/".format(sid=self.sid))
        if version == "v2":
            return urljoin(self.baseurl, "v2/accounts/{sid}/".format(sid=self.sid))
        if version == "v2_beta":
            return urljoin(self.baseurl, "v2_beta/Accounts/{sid}/".format(sid=self.sid))

    def __call_api(self, method: str, endpoint: str,
                   version: str = "v2", data: dict = None) -> dict:

        url = urljoin(self.__api_url(version), endpoint)

        if data is not None:
            if version == "v1":
                response = requests.request(
                    method=method, url=url, auth=self.auth_headers, data=data)
            else:
                if method in ["POST", "PUT", "PATCH"]:
                    response = requests.request(
                        method=method, url=url, auth=self.auth_headers, json=data)
                elif method == "GET":
                    response = requests.request(
                        method=method, url=url, auth=self.auth_headers, params=data)
        else:
            response = requests.request(
                method=method, url=url, auth=self.auth_headers)

        logging.debug(
            "Making API request to {url} with payload: {payload}, received response: {response}".format(
                url=url, payload=data, response=response.json()))

        if response.status_code == 401:
            description = get_error_description(response.json())
            raise AuthenticationFailed(description)
        elif response.status_code == 403:
            raise PermissionDenied(
                "Your credentials are valid, but you don't have access to the requested resource.")
        elif response.status_code == 402:
            description = get_error_description(response.json())
            raise PaymentRequired(description)
        elif response.status_code == 429:
            raise Throttled("Request was throttled.")
        elif response.status_code == 400:
            description = get_error_description(
                response.json(), version=version)
            raise ValidationError(description)
        elif response.status_code == 404:
            description = get_error_description(
                response.json(), version=version)
            raise NotFound(description)

        return response.json()

    def create_campaign(
            self, caller_id: str, app_id: str, from_: List[str] = None, lists: List[str] = None,
            name: str = None, call_duplicate_numbers: bool = None, schedule: Schedule = None,
            campaign_type: str = "static", call_status_callback: str = None,
            call_schedule_callback: str = None, status_callback: str = None, retry: Retry = None) -> dict:
        """
        The parameter information is available at https://developer.exotel.com/api/campaigns#create-campaign

        Args:
            caller_id (str): This is your ExoPhone
            app_id (str): Identifier of the flow that you want to connect to once the from number picks up the call, this is used to build the `url` param for API
            `from_` (List[str], optional): `from` equivalent
            lists (List[str], optional): Defaults to None.
            name (str, optional): Defaults to None.
            call_duplicate_numbers (bool, optional): Defaults to None.
            schedule (Schedule, optional): Defaults to None.
            campaign_type (str, optional): Defaults to "static".
            call_status_callback (str, optional): Defaults to None.
            call_schedule_callback (str, optional): Defaults to None.
            status_callback (str, optional): Defaults to None.
            retry (Retry, optional): Defaults to None.

        Raises:
            ValueError: raised when both from_ and lists are provided at the same, only either can be passed
            ValueError: raised when neither from_ or lists is passed, can't create campaign without it

        Returns:
            dict: json containing API response
        """
        campaign = {
            "caller_id": caller_id,
            "campaign_type": campaign_type,
            "url": f"http://my.exotel.com/{self.sid}/exoml/start_voice/{app_id}",
        }

        if (from_ is not None) and (lists is not None):
            raise ValueError(
                "Both from_ and lists can't be provided at the same, only either can be passed")

        if (from_ is None) and (lists is None):
            raise ValueError(
                "Either from_ or lists must be passed, can't create campaign without it")

        if from_ is not None:
            validate_list_of_nums(from_)
            campaign["from"] = from_

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

        return self.__call_api("POST", 'campaigns', data=payload)

    def create_campaign_with_list(
            self, numbers: List[str],
            list_name: str, caller_id: str, app_id: str, **kwargs) -> dict:
        """Slightly customized to create list with numbers
        passed as argument implicitly

        Args:
            numbers (List[str]): List of numbers in E.164 format
            list_name (str): name of contact list that will be created implicitly
            caller_id (str): This is your exophone
            app_id (str): Identifier of the flow that you want to connect to once the from number picks up the call, this is used to build the `url` param for API
            **kwargs: accepts the rest of the arguments of create_campaign

        Returns:
            dict: json containing API response
        """
        validate_list_of_nums(numbers)
        data = self.create_list(name=list_name, numbers=numbers)
        list_id = get_list_id(data)
        contact_sids = get_contact_sids(data)
        lists = [list_id]

        try:
            return self.create_campaign(caller_id=caller_id,
                                        app_id=app_id, lists=lists, **kwargs)
        except ValidationError as e:
            logger.warn(
                "Exotel API raised validation error, reverting list and contacts creation")
            self.delete_list(list_id)
            self.delete_contacts(contact_sids)
            raise e
        except PaymentRequired as e:
            logging.warn(
                "Exotel API raised payment required error, campaign creation failed, reverting contact and list creation")
            self.delete_list(list_id)
            self.delete_contacts(contact_sids)
            raise e

    def get_campaign_details(self, campaign_id: str) -> dict:
        """Retrieve the details of a specific campaign in your account

        https://developer.exotel.com/api/campaigns#campaign-details

        Args:
            campaign_id (str): ID of the campaign

        Returns:
            dict: json object containg the API response
        """
        return self.__call_api("GET", 'campaigns/{cid}'.format(cid=campaign_id))

    def delete_campaign(self, campaign_id: str) -> dict:
        """Delete a specific campaign

        https://developer.exotel.com/api/campaigns#delete-campaign

        Args:
            campaign_id (str): ID of the campaign

        Returns:
            dict: json object containing the API response
        """
        return self.__call_api("DELETE", "campaigns/{cid}".format(cid=campaign_id))

    def get_bulk_campaign_details(
            self, offset: int = None, limit: int = None, name: str = None, status: str = None,
            sort_by: str = None) -> dict:
        """Allows you to fetch bulk campaign details with sorting and searching capabilities
        https://developer.exotel.com/api/campaigns#bulk-campaign-details

        Args:
            offset (int, optional): _description_. Defaults to None.
            limit (int, optional): number of records on single page. Defaults to None. (Exotel applies its own default, refer docs)
            name (str, optional): Search on Campaign name. Defaults to None.
            status (str, optional): Defaults to None.
            sort_by (str, optional): Defaults to None.

        Returns:
            dict: json object containing the API response
        """
        data = {}

        if offset is not None:
            data["offset"] = offset

        if limit is not None:
            data["limit"] = limit

        if name is not None:
            data["name"] = name

        if status is not None:
            data["status"] = status

        if sort_by is not None:
            data["sort_by"] = sort_by

        return self.__call_api("GET", 'campaigns', data=data)

    def get_campaign_call_details(
            self, campaign_id: str, offset: int = None, limit: int = None, status: str = None,
            sort_by: str = None) -> dict:
        """https://developer.exotel.com/api/campaigns#call-details-single-campaign

        Args:
            campaign_id (str): ID of the campaign
            offset (int, optional): Defaults to None.
            limit (int, optional): Defaults to None.
            status (str, optional): Defaults to None.
            sort_by (str, optional): Defaults to None.

        Returns:
            dict: json object containing the API response
        """
        data = {}
        if offset is not None:
            data["offset"] = offset

        if limit is not None:
            data["limit"] = limit

        if status is not None:
            data["status"] = status

        if sort_by is not None:
            data["sort_by"] = sort_by

        return self.__call_api(
            "GET", 'campaigns/{cid}/call-details'.format(cid=campaign_id),
            data=data)

    def create_contacts(self, numbers: List[str]):
        """Create contacts

        https://developer.exotel.com/api/campaigns-contacts#create-contacts

        Args:
            numbers (List[str]): List of E.164 formatted phone numbers

        Returns:
            dict: json object containing API response
        """
        validate_list_of_nums(numbers)
        payload = {
            "contacts": [
                {"number": num} for num in numbers
            ]
        }
        return self.__call_api("POST", "contacts", data=payload)

    def get_contact_details(self, contact_id: str) -> dict:
        """
        https://developer.exotel.com/api/campaigns-contacts#get-details-of-a-contact

        Args:
            contact_id (str): Contact SID

        Returns:
            dict: json object containing API response
        """
        return self.__call_api("GET", "contacts/{cid}".format(cid=contact_id))

    def delete_contact(self, sid: str) -> dict:
        """https://developer.exotel.com/api/campaigns-contacts#delete-a-contact

        Args:
            sid (str): contact sid

        Returns:
            dict: json object containing API response
        """

        return self.__call_api("DELETE", "contacts/{cid}".format(cid=sid))

    def delete_contacts(self, sids: List[str]) -> List[dict]:
        """Utility method for deleting multiple contact at once

        Args:
            sids (List[str]): List of E.164 formatted numbers

        Returns:
            List[dict]: List of json object containing API response for each contact
        """
        responses = []
        for sid in sids:
            responses.append(self.delete_contact(sid))

        return responses

    def create_list(self, name: str, tag: str = "demo",
                    numbers: List[str] = None) -> dict:
        """
        Slightly modded implementation that takes number as arguments and add
        those numbers to list after creation

        https://developer.exotel.com/api/campaigns-lists#create-lists

        Args:
            name (str): Name of the list
            tag (str, optional): Defaults to "demo".
            numbers (List[str], optional): List of E.164 formatted phone numbers. Defaults to None.

        Raises:
            UniqueViolationError: When contact list with same name already exists

        Returns:
            dict: json object containing API response
        """
        if numbers is not None:
            validate_list_of_nums(numbers)

        payload = {
            "lists": [
                {
                    "name": name,
                    "tag": tag
                }
            ]
        }
        data = self.__call_api("POST", "lists", data=payload)

        if data["response"][0]["code"] == 409:
            description = data["response"][0]["error_data"]["description"]
            raise UniqueViolationError(description)

        list_id = data["response"][0]["data"]["sid"]

        if numbers is not None:
            output = None
            for nums in batch_contacts(numbers):
                contact_sids = get_contact_sids(self.create_contacts(nums))

                response = self.add_contacts_to_list(contact_sids, list_id)
                if output is None:
                    output = deepcopy(response)
                else:
                    output["response"] += response["response"]
                    output["metadata"]["success"] += response["metadata"]["success"]
                    output["metadata"]["total"] += response["metadata"]["total"]
            return output

        return data

    def add_contacts_to_list(self, sids: List[str], list_id: str) -> dict:
        """
        https://developer.exotel.com/api/campaigns-lists#add-contacts-to-a-list

        Args:
            sids (List[str]): List of contact sids to add
            list_id (str): Contact List ID

        Returns:
            dict: json object containing API response
        """
        payload = {
            "contact_references": [
                {"contact_sid": sid} for sid in sids
            ]
        }
        return self.__call_api("POST", "lists/{list_id}/contacts".format(list_id=list_id),
                               data=payload)

    def delete_list(self, list_id: str) -> dict:
        """Deletes a list

        https://developer.exotel.com/api/campaigns-lists#delete-a-list

        Args:
            list_id (str): Contact List ID

        Returns:
            dict: json object containing API response
        """
        return self.__call_api("DELETE", "lists/{list_id}".format(list_id=list_id))

    def get_list_details(self, list_id: str) -> dict:
        """
        https://developer.exotel.com/api/campaigns-lists#get-details-of-a-list

        Args:
            list_id (str): Contact List ID
        """
        return self.__call_api("GET", "lists/{list_id}".format(list_id=list_id))

    def get_bulk_lists(self, offset: int = None, limit: int = None,
                       name: str = None, sort_by: str = None) -> dict:
        """https://developer.exotel.com/api/campaigns-lists#getbulklists

        Args:
            offset (int, optional): Defaults to None.
            limit (int, optional): Defaults to None.
            name (str, optional): Defaults to None.
            sort_by (str, optional): Defaults to None.

        Returns:
            dict: json object containing API response
        """

        data = {}
        if offset is not None:
            data["offset"] = offset

        if limit is not None:
            data["limit"] = limit

        if name is not None:
            data["name"] = name

        if sort_by is not None:
            data["sort_by"] = sort_by

        return self.__call_api("GET", "lists", data=data)

    def get_list_contacts(self, list_id: str, limit: int = None, offset: int = None) -> dict:
        """
        https://developer.exotel.com/api/campaigns-lists#get-contacts-in-a-list

        Args:
            list_id (str): Contact List ID
            limit (int, optional): Defaults to None.
            offset (int, optional): Defaults to None.

        Returns:
            dict: json object containing API response
        """
        data = {}

        if offset is not None:
            data["offset"] = offset

        if limit is not None:
            data["limit"] = limit

        return self.__call_api(
            "GET", "lists/{list_id}/contacts".format(list_id=list_id),
            data=data)

    def create_sms_campaign(
            self, content_type: str, lists: List[str],
            dlt_entity_id: int, dlt_template_id: int, sender_id: str, sms_type: str,
            template: str, name: str = None, schedule: Schedule = None,
            status_callback: str = None, sms_status_callback: str = None) -> dict:
        """Deprecated

        Returns:
            dict: json object containing API response
        """
        data = {
            "content_type": content_type,
            "lists": lists,
            "dlt_entity_id": dlt_entity_id,
            "dlt_template_id": dlt_template_id,
            "sender_id": sender_id,
            "template": template,
            "sms_type": sms_type
        }

        if name is not None:
            data["name"] = name

        if schedule is not None:
            data["schedule"] = schedule.to_json(sms=True)

        if status_callback is not None:
            data["status_callback"] = validate_url(status_callback)

        if sms_status_callback is not None:
            data["sms_status_callback"] = validate_url(sms_status_callback)

        return self.__call_api("POST", "sms-campaigns", data=data)

    def create_message_campaign(
            self, content_type: str, lists: List[str],
            dlt_entity_id: int, template_id: int, sender_id: str, message_type: str,
            template: str, name: str, channel: str, schedule: Schedule = None,
            status_callback: str = None, message_status_callback: str = None) -> dict:
        """Create SMS Campaign
        https://developer.exotel.com/api/sms-campaigns#create-sms-campaigns

        Args:
            content_type (str): static or dynamic
            lists (List[str]): List of contact list IDs
            dlt_entity_id (int): DLT Entity ID
            template_id (int): Template ID
            sender_id (str): Sender ID
            message_type (str): Transactional/Promotional
            template (str): Body of the SMS
            name (str): Name of the campaign
            channel (str): SMS or Whatsapp
            schedule (Schedule, optional): Defaults to None.
            status_callback (str, optional): Defaults to None.
            message_status_callback (str, optional): Defaults to None.

        Returns:
            dict: json object containing API response
        """

        data = {
            "content_type": content_type,
            "lists": lists,
            "dlt_entity_id": dlt_entity_id,
            "template_id": template_id,
            "from": sender_id,
            "message_type": message_type,
            "template": template,
            "name": name,
            "channel": channel
        }

        if schedule is not None:
            data["schedule"] = schedule.to_json(sms=True)

        if status_callback is not None:
            data["status_callback"] = validate_url(status_callback)

        if message_status_callback is not None:
            data["message_status_callback"] = validate_url(
                message_status_callback)

        return self.__call_api("POST", "message-campaigns", data=data)

    def create_message_campaign_with_list(self, numbers: List[str],
                                          list_name: str, *args, **kwargs) -> dict:
        """Slightly customized to create list with numbers
        passed as argument implicitly

        https://developer.exotel.com/api/sms-campaigns#create-sms-campaigns

        Args:
            numbers (List[str]): List of E.164 formatted phone numbers
            list_name: Name of the contact list which will be used implicitly

        Raises:
            ValidationError: raised when any of the parameters isn't passed correctly
        """
        validate_list_of_nums(numbers)
        data = self.create_list(name=list_name, numbers=numbers)
        list_id = get_list_id(data)
        contact_sids = get_contact_sids(data)
        lists = [list_id]

        try:
            return self.create_message_campaign(*args, lists=lists, **kwargs)
        except ValidationError as e:
            logger.warn(
                "Exotel API raised validation error, reverting lists and contacts creation")
            self.delete_list(list_id)
            self.delete_contacts(contact_sids)
            raise e

    def create_sms_campaign_with_list(self, numbers: List[str],
                                      list_name: str, *args, **kwargs) -> dict:
        """Slightly customized to create list with numbers
        passed as argument implicitly
        https://developer.exotel.com/api/sms-campaigns#create-sms-campaigns

        Args:
            numbers (List[str]): List of E.164 formatted phone numbers
            list_name: Name of the contact list which will be used implicitly

        Returns:
            dict: json object containing API response

        Raises:
            ValidationError: raised when any of the parameters isn't passed correctly
        """
        validate_list_of_nums(numbers)
        data = self.create_list(name=list_name, numbers=numbers)
        list_id = get_list_id(data)
        contact_sids = get_contact_sids(data)
        lists = [list_id]

        try:
            return self.create_sms_campaign(*args, lists=lists, **kwargs)
        except ValidationError as e:
            logger.warn(
                "Exotel API raised validation error, reverting lists and contacts creation")
            self.delete_list(list_id)
            self.delete_contacts(contact_sids)
            raise e

    def get_sms_campaign_details(self, campaign_id: str) -> dict:
        """Get details of the SMS Campaign
        https://developer.exotel.com/api/sms-campaigns#sms-campaigns-details

        Args:
            campaign_id (str): SMS Campaign ID

        Returns:
            dict: json object containing the API response
        """
        return self.__call_api(
            "GET", "sms-campaigns/{campaign_id}".format(campaign_id=campaign_id))

    def get_bulk_sms_campaign_details(
            self, offset: int = None, limit: int = None, name: str = None, status: str = None,
            sort_by: str = None) -> dict:
        """https://developer.exotel.com/api/sms-campaigns#bulk-sms-campaign-details

        Args:
            offset (int, optional): Defaults to None.
            limit (int, optional): Defaults to None.
            name (str, optional): Defaults to None.
            status (str, optional): Defaults to None.
            sort_by (str, optional): Defaults to None.

        Returns:
            dict: json object containing API response
        """
        data = {}

        if offset is not None:
            data["offset"] = offset

        if limit is not None:
            data["limit"] = limit

        if name is not None:
            data["name"] = name

        if status is not None:
            data["status"] = status

        if sort_by is not None:
            data["sort_by"] = sort_by

        return self.__call_api("GET", "sms-campaigns", data=data)

    def get_sms_campaign_sms_details(
            self, campaign_id: str, limit: int = None, offset: int = None, sort_by: str = None) -> dict:
        """https://developer.exotel.com/api/sms-campaigns#sms-details-single-campaign

        Args:
            campaign_id (str): SMS Campaign ID
            limit (int, optional): Defaults to None.
            offset (int, optional): Defaults to None.
            sort_by (str, optional): Defaults to None.

        Returns:
            dict: json object containing API response
        """
        data = {}

        if offset is not None:
            data["offset"] = offset

        if limit is not None:
            data["limit"] = limit

        if sort_by is not None:
            data["sort_by"] = sort_by

        return self.__call_api(
            "GET", "sms-campaigns/{campaign_id}/sms-details".format(campaign_id=campaign_id), data=data)

    def get_sms_details(self, sms_sid: str) -> dict:
        """https://developer.exotel.com/api/sms#sms-details

        Args:
            sms_sid (str):sms_id is an alpha-numeric unique identifier generated for all the SMS sent via Exotel

        Returns:
            dict: json object containing API response
        """
        return self.__call_api(
            "GET", "SMS/Messages/{sms_sid}.json".format(sms_sid=sms_sid),
            version="v1")

    def send_bulk_sms(
            self, from_: str, to: List[str],
            body: str, encoding_type: str = None, priority: str = None,
            status_callback: str = None, dlt_entity_id: str = None, dlt_template_id: str = None,
            sms_type: str = None) -> dict:
        """
        https://developer.exotel.com/api/sms#send-bulk-static-sms

        Args:
            from_ (str): Refer Exotel docs
            to (List[str]): Refer Exotel docs
            body (str): Refer Exotel docs
            encoding_type (str, optional): Defaults to None.
            priority (str, optional): Defaults to None.
            status_callback (str, optional): Defaults to None.
            dlt_entity_id (str, optional): Defaults to None.
            dlt_template_id (str, optional): Defaults to None.
            sms_type (str, optional): Defaults to None.

        Returns:
            dict: json object containing API response
        """
        validate_list_of_nums(to)

        data = {
            "From": from_,
            "To": to,
            "Body": body
        }

        if encoding_type is not None:
            data["EncodingType"] = encoding_type

        if priority is not None:
            data["Priority"] = priority

        if status_callback is not None:
            data["StatusCallback"] = validate_url(status_callback)

        if dlt_entity_id is not None:
            data["DltEntityId"] = dlt_entity_id

        if dlt_template_id is not None:
            data["DltTemplateId"] = dlt_template_id

        if sms_type is not None:
            data["SmsType"] = sms_type

        return self.__call_api("POST", "Sms/send.json", version="v1", data=data)

    def get_all_exophones(self) -> dict:
        """Get a list of all the ExoPhone numbers that have been assigned to an account
        https://developer.exotel.com/api/exophones#list-exophones

        Returns:
            dict : json object containing API response
        """
        return self.__call_api("GET", "IncomingPhoneNumbers", version="v2_beta")

    def get_exophone_details(self, exophone_sid: str) -> dict:
        """Get the details of a specific ExoPhone number of an account

        https://developer.exotel.com/api-console/exophone#get-details-of-an-exophone

        Args:
            exophone_sid (str): Exophone SID

        Returns:
            dict: json object containing API response
        """
        return self.__call_api("GET", f"IncomingPhoneNumbers/{exophone_sid}", version="v2_beta")

    def get_exophone_heartbeat(self, exophone_sid: str) -> dict:
        """Get the details of a specific ExoPhone in your account including connectivity information

        https://developer.exotel.com/api-console/heart-beat#get-exophone-details-v2

        Args:
            exophone_sid (str): Exophone SID

        Returns:
            dict: json object containing API response
        """
        return self.__call_api("GET", f"incoming-phone-numbers/{exophone_sid}", version="v2")
