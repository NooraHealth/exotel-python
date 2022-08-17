from urllib.parse import urljoin

import requests
from requests.auth import HTTPBasicAuth


class Exotel:
    def __init__(self, sid, key, token, baseurl="https://api.exotel.com"):
        self.sid = sid
        self.key = key
        self.token = token
        self.baseurl = urljoin(baseurl, "v2/accounts/{sid}/".format(sid=sid))

    def get_campaign_details(self, campaign_id):
        return requests.get(urljoin(self.baseurl, 'campaigns/{cid}'.format(cid=campaign_id)), 
        auth=HTTPBasicAuth(self.key, self.token))

    def get_campaign_call_details(self, campaign_id):
        return requests.get(urljoin(self.baseurl, 'campaigns/{cid}/call-details'.format(cid=campaign_id)),
        auth=HTTPBasicAuth(self.key, self.token))

    def get_bulk_campaign_details(self):
        return requests.get(urljoin(self.baseurl, 'campaigns'), auth=HTTPBasicAuth(self.key, self.token))
