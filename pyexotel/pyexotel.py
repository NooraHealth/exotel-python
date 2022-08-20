import json
from datetime import datetime
from typing import List
from urllib.parse import urljoin

import pytz
import requests
from requests.auth import HTTPBasicAuth


class AuthenticationFailed(Exception):
    pass


class PermissionDenied(Exception):
    pass


class PaymentRequired(Exception):
    pass


class Throttled(Exception):
    pass


class Exotel:
    def __init__(self, sid: str, key: str, token: str, baseurl: str = "https://api.exotel.com"):
        self.sid = sid
        self.baseurl = urljoin(baseurl, "v2/accounts/{sid}/".format(sid=sid))
        self.auth_headers = HTTPBasicAuth(key, token)

    def __call_api(self, method: str, endpoint: str, data: dict = None) -> dict:
        if method == "POST" and data is not None:
            data = json.dumps(data)

        if data is not None:
            response = requests.request(
                method=method, url=endpoint, auth=self.auth_headers, data=data)
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

    def get_campaign_details(self, campaign_id: str):
        return self.__call_api("GET", urljoin(self.baseurl, 'campaigns/{cid}'.format(cid=campaign_id)))

    def get_campaign_call_details(self, campaign_id: str):
        return self.__call_api("GET", urljoin(self.baseurl, 'campaigns/{cid}/call-details'.format(cid=campaign_id)))

    def get_bulk_campaign_details(self):
        return self.__call_api("GET", urljoin(self.baseurl, 'campaigns'))

    def create_campaign(self, to: List[str], caller_id: str, app_id: str, name: str, send_at: datetime, end_at: datetime, campaign_type: str = "static"):
        ist = pytz.timezone("Asia/Kolkata")
        send_at_ist = send_at.astimezone(ist).isoformat()
        end_at_ist = end_at.astimezone(ist).isoformat()
        payload = {
            "campaigns": [
                {
                    "from": to,
                    "caller_id": caller_id,
                    "campaign_type": campaign_type,
                    "url": f"http://my.exotel.com/{self.sid}/exoml/start_voice/{app_id}",
                    "name": name,
                    "schedule": {
                        "send_at": send_at_ist,
                        "end_at": end_at_ist
                    }
                }
            ]
        }
        return self.__call_api("POST", urljoin(self.baseurl, 'campaigns'), data=payload)

    def delete_campaign(self, campaign_id: str):
        return self.__call_api("DELETE", urljoin(self.baseurl, "campaigns/{cid}".format(cid=campaign_id)))

    def get_contact_details(self, contact_id: str):
        return self.__call_api("GET", urljoin(self.baseurl, "contacts/{cid}".format(cid=contact_id)))

    def create_contacts(self, numbers: List[str]):
        contacts_url = urljoin(self.baseurl, "contacts")
        payload = {
            "contacts": [
                {"number": num} for num in numbers
            ]
        }
        data = self.__call_api("POST", contacts_url, data=payload)
        sids = [i["data"]["sid"] for i in data["response"]]
        return sids

    def delete_contact(self, sid: str):
        return self.__call_api("DELETE", urljoin(self.baseurl, "contacts/{cid}".format(cid=sid)))

    def delete_contacts(self, sids: str) -> List[dict]:
        responses = []
        for sid in sids:
            responses.append(self.delete_contact(sid))

        return responses

    def add_contacts_to_list(self, sids: List[str], list_id: str):
        payload = {
            "contact_references": [
                {"contact_sid": sid} for sid in sids
            ]
        }
        return self.__call_api("POST",
                               urljoin(self.baseurl, "lists/{list_id}/contacts".format(list_id=list_id)), data=payload)

    def create_list(self, name: str, tag: str = "demo", numbers: List[str] = None) -> str:
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
        list_id = data["response"][0]["data"]["sid"]

        if numbers is not None:
            contact_sids = self.create_contacts(numbers)
            response = self.add_contacts_to_list(contact_sids, list_id)

        return list_id

    def delete_list(self, list_id: str):
        return self.__call_api("DELETE", urljoin(self.baseurl, "lists/{list_id}".format(list_id=list_id)))
