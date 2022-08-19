import json
from urllib.parse import urljoin

import pytz
import requests
from requests.auth import HTTPBasicAuth


class Exotel:
    def __init__(self, sid, key, token, baseurl="https://api.exotel.com"):
        self.sid = sid
        self.baseurl = urljoin(baseurl, "v2/accounts/{sid}/".format(sid=sid))
        self.auth_headers = HTTPBasicAuth(key, token)

    def get_campaign_details(self, campaign_id):
        return requests.get(urljoin(self.baseurl, 'campaigns/{cid}'.format(cid=campaign_id)),
                            auth=self.auth_headers)

    def get_campaign_call_details(self, campaign_id):
        return requests.get(urljoin(self.baseurl, 'campaigns/{cid}/call-details'.format(cid=campaign_id)),
                            auth=self.auth_headers)

    def get_bulk_campaign_details(self):
        return requests.get(urljoin(self.baseurl, 'campaigns'), auth=self.auth_headers)

    def create_campaign(self, to, caller_id, app_id, name, send_at, end_at, campaign_type="static"):
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
        return requests.post(urljoin(self.baseurl, 'campaigns'), auth=self.auth_headers, data=json.dumps(payload))

    def delete_campaign(self, campaign_id):
        return requests.delete(urljoin(self.baseurl, "campaigns/{cid}".format(cid=campaign_id)), auth=self.auth_headers)

    def get_contact_details(self, contact_id):
        return requests.get(urljoin(self.baseurl, "contacts/{cid}".format(cid=contact_id)), auth=self.auth_headers)

    def create_contacts(self, numbers):
        contacts_url = urljoin(self.baseurl, "contacts")
        payload = {
            "contacts": [
                {"number": num} for num in numbers
            ]
        }
        data = requests.post(contacts_url, data=json.dumps(
            payload), auth=self.auth_headers).json()
        sids = [i["data"]["sid"] for i in data["response"]]
        return sids

    def delete_contact(self, sid):
        return requests.delete(urljoin(self.baseurl, "contacts/{cid}".format(cid=sid)), auth=self.auth_headers)

    def delete_contacts(self, sids):
        responses = []
        for sid in sids:
            responses.append(self.delete_contact(sid).status_code)

        return responses

    def add_contacts_to_list(self, sids, list_id):
        payload = {
            "contact_references": [
                {"contact_sid": sid} for sid in sids
            ]
        }
        return requests.post(
            urljoin(self.baseurl, "lists/{list_id}/contacts".format(list_id=list_id)), auth=self.auth_headers, data=json.dumps(payload))

    def create_list(self, name, tag="demo", numbers=None):
        payload = {
            "lists": [
                {
                    "name": name,
                    "tag": tag
                }
            ]
        }
        data = requests.post(urljoin(self.baseurl, "lists"),
                             auth=self.auth_headers, data=json.dumps(payload)).json()
        list_id = data["response"][0]["data"]["sid"]
        contact_sids = self.create_contacts(numbers)
        response = self.add_contacts_to_list(contact_sids, list_id)
        return list_id

    def delete_list(self, list_id):
        return requests.delete(urljoin(self.baseurl, "lists/{list_id}".format(list_id=list_id)), auth=self.auth_headers)
