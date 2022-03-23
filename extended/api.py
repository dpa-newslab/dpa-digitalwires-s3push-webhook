# -*- coding: utf-8 -*-
#
# Copyright 2022, 2022 dpa-IT Services GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging

import requests

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class MyApi():
    def __init__(self, api_url, api_key):
        self.headers = {
            'Accept': 'application/json',
            'Authorization': 'Bearer {}'.format(api_key),
            'Content-Type': 'application/json'
        }

        self.api_url = api_url 

    def send_article(self, article):
        """
        Sends article to the api and receives insertion receipt to asynchronously check the insertion success
        """
        sess = requests.Session()
        try:
            response = sess.post(url=f"{self.api_url}/insert", json=article,
                             headers=self.headers, timeout=30)
            response.raise_for_status()
            
            logger.info('RESPONSE {}'.format(response))
            return response.json()["receipt"]
        except Exception as e:
            logger.info('Request {}'.format(e))
            raise e

    def get_insertion_status(self, receipt):
        """
        Checks whether article insertion is completed. Returns current status ("success", "pending" or anything else for errors)
        """
        sess = requests.Session()
        try:
            response = sess.get(url=f"{self.api_url}/status/{receipt}", headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json().get("status")
        except Exception as e:
            logger.info('Request {}'.format(e))
            raise e

    