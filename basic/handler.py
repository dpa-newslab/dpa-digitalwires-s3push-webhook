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

import boto3
import json
import logging
import os
import requests

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Fetch api endpoint and api key of SSM-Parameterstore
STAGE = os.environ.get('STAGE', 'prod')
client = boto3.client('ssm')
resp = client.get_parameter(Name='/mycompany/{}/dpa_s3push/api_endpoint'.format(
    STAGE), WithDecryption=False)
API_URL = resp['Parameter']['Value']
resp = client.get_parameter(Name='/mycompany/{}/dpa_s3push/api_apikey'.format(
    STAGE), WithDecryption=True)
API_KEY = resp['Parameter']['Value']


def handle_delivery_queue(event, context):
    """
    Processing queue events by posting articles and checking for insertion status
    """
    logger.info('handle_delivery_queue -> EVENT: {}'.format(event))

    message = event['Records'][0]
    entry = json.loads(message.get('body'))

    logger.info('Handling sqs-message {}'.format(message.get('messageId')))

    # Post article to API
    try:
        post_article(entry)
    except Exception as e:
        # Due to RedrivePolicy of DeliveryQueue - retries are triggered
        logger.error('ERROR {}'.format(e))
        raise e


def post_article(entry):
    """ Post article to API.
    """
    logger.info('post_article -> {}'.format(entry))
    records = entry.get('Records', [])
    if records:
        s3_entry = records[0]['s3']

        s3_bucket_name = s3_entry['bucket']['name']
        s3_bucket_key = s3_entry['object']['key']

        logger.info('Post article for s3-key {} in bucket {}'.format(s3_bucket_key, s3_bucket_name))

        # Fetch article JSON from s3-bucket and send call webhook
        s3 = boto3.resource('s3')
        s3_obj = s3.Object(s3_bucket_name, s3_bucket_key)
        article_json = s3_obj.get()['Body'].read().decode('utf-8') 

        try:
            response = trigger_webhook(article_json)
        except Exception as e:
            logger.error('ERROR {}'.format(e))
            raise e

        # TODO: handle response
        logger.info('RESPONSE {}'.format(response))
    else:
        logger.error('ERROR no record available in entry {}'.format(entry))


def trigger_webhook(request_json):
    """Trigger webhook to send data to API."""
    # CHANGE THIS!
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Bearer {}'.format(API_KEY),
        'Content-Type': 'application/json'
    }

    logger.info('Webhook URL: {}'.format(API_URL))
    sess = requests.Session()
    try:
        response = sess.post(url=API_URL, json=request_json,
                             headers=headers, timeout=30)
        response.raise_for_status()
    except Exception as e:
        logger.info('Request {}'.format(e))
        raise e

    return response.json()
