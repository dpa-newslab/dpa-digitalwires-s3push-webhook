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

from botocore.exceptions import ClientError

from api import MyApi

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Fetch api endpoint and api key of SSM-Parameterstore
STAGE = os.environ.get('STAGE', 'prod')
ssm_client = boto3.client('ssm')

try:
    resp = ssm_client.get_parameter(
        Name='/mycompany/{}/dpa_s3push/api_endpoint'.format(STAGE),
        WithDecryption=False)
    API_URL = resp['Parameter']['Value']
    resp = ssm_client.get_parameter(
        Name='/mycompany/{}/dpa_s3push/api_apikey'.format(STAGE),
        WithDecryption=True)
    API_KEY = resp['Parameter']['Value']

    my_api = MyApi(API_URL, API_KEY)
except:
    pass


def handle_delivery_queue(event, context):
    """
    Processing queue events by posting articles and checking for insertion
    status
    """
    DELIVERY_QUEUE_URL = os.environ['DELIVERY_QUEUE_URL']
    DEADLETTER_QUEUE_URL = os.environ['DEADLETTER_QUEUE_URL']

    logger.info('handle_delivery_queue -> EVENT: {}'.format(event))

    message = event['Records'][0]
    entry = json.loads(message.get('body'))

    logger.info('Handling sqs-message {}'.format(message.get('messageId')))

    insertion_receipt = message.get("messageAttributes", {}).get(
        "InsertionReceipt", {}).get("stringValue")

    if insertion_receipt is None:
        try:
            # Post article to API
            insertion_receipt = post_article(entry)
            # Send entry back to the sqs to check for status updates
            send_sqs_message(
                DELIVERY_QUEUE_URL,
                entry,
                {
                    "InsertionReceipt": {
                        "DataType": "String",
                        "StringValue": insertion_receipt
                    },
                    "Retries": {
                        "DataType": "Number",
                        "StringValue": message.get(
                            "messageAttributes", {}).get("Retries", {}).get(
                                "stringValue", "0")
                    }
                },
                5
            )
        except Exception as e:
            # Due to RedrivePolicy of DeliveryQueue - retries are triggered
            logger.error('ERROR {}'.format(e))
            raise e
    else:
        logger.info(
            f"Checking insertion status of receipt {insertion_receipt}")
        status = my_api.get_insertion_status(insertion_receipt)
        if status == "success":
            # Insertion done - AWS will remove the sqs message
            logging.info(f"Receipt {insertion_receipt} done.")
        elif status == "pending":
            logging.info(f"Receipt {insertion_receipt} still pending")
            raise Exception("Still pending")
        else:
            # Insertion failed. Sending message to the deadletter queue
            send_sqs_message(
                DEADLETTER_QUEUE_URL,
                entry,
                {
                   "InsertionReceipt": {
                        "DataType": "String",
                        "StringValue": insertion_receipt
                    },
                    "Retries": {
                        "DataType": "Number",
                        "StringValue": message.get(
                            "messageAttributes", {}).get("Retries", {}).get(
                            "stringValue", "0")
                    }
                }
            )


def handle_failure_queue(event, context):
    """
    Receive failed imports. Check if MAX_RETRIES is reached, logs URN and
    notifies via email
    """
    DELIVERY_QUEUE_URL = os.environ['DELIVERY_QUEUE_URL']
    message = event['Records'][0]
    entry = json.loads(message.get('body', {}))

    error = ''
    # Prevent failures in deadletter queue
    try:
        logger.info('Processing of message {} failed (article: {})'.format(
            message['messageId'], entry))
        retries = int(message.get('messageAttributes', {}).get(
            'Retries', {}).get('stringValue', '0'))
        if retries == 0:  # try to put back on delivery queue one more time
            logger.info('Retry pushing of article: {}'.format(json.dumps(entry)))
            retries += 1
            send_sqs_message(
                DELIVERY_QUEUE_URL,
                entry,
                {
                    'Retries': {
                        'DataType': 'Number',
                        'StringValue': str(retries)
                    }
                },
                60*retries  # delay of 1 minute
            )
            return

        if retries is not None:
            error += 'Number of retries: {}'.format(retries)
    except Exception as e:
        logger.error(e)
        error += 'Handling sqs-message failed. Message:\n {} ({})'.format(
            event, e)

    logger.error(error)
    # Send mail with error message
    notifier_mail = os.environ.get('NOTIFICATION_MAIL')
    if notifier_mail is not None:
        content = '''Number of retries exceeded for message:
                     \n{}\n\nErrors: {}'''.format(entry, error)
        send_mail(notifier_mail, notifier_mail,
                  'Post-API failure notification',
                  content,
                  region=os.environ.get('AWS_REGION', 'eu-central-1'))


def post_article(entry):
    """
    Posts article to API and returns insertion receipt
    """
    s3_entry = entry['Records'][0]['s3']

    s3_bucket_name = s3_entry['bucket']['name']
    s3_bucket_key = s3_entry['object']['key']

    logger.info('Post article for s3-key {} in bucket {}'.format(
        s3_bucket_key, s3_bucket_name))

    # Fetch article JSON from s3-bucket and send call webhook
    s3 = boto3.resource('s3')
    s3_obj = s3.Object(s3_bucket_name, s3_bucket_key)
    article_json = s3_obj.get()['Body'].read().decode('utf-8') 

    try:
        receipt = my_api.send_article(article_json)
    except Exception as e:
        logger.error('ERROR {}'.format(e))
        raise e

    return receipt


def send_sqs_message(url, message, attributes, delay=5):
    sqs = boto3.client('sqs')
    sqs.send_message(
        QueueUrl=url,
        MessageBody=json.dumps(message),
        MessageAttributes=attributes,
        DelaySeconds=delay
    )


def send_mail(sender, recipient, title, message, region='eu-central-1'):
    CHARSET = 'UTF-8'
    client = boto3.client('ses', region_name=region)

    try:
        response = client.send_email(
            Destination={
                'ToAddresses': [recipient]
            },
            Message={
                'Body': {
                    'Text': {
                        'Charset': CHARSET,
                        'Data': message
                    }
                },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': title
                }
            },
            Source=sender
        )
    except ClientError as e:
        logger.error('Sending mail failed: {}'.format(
            e.response['Error']['Message']))
        raise e
    except Exception as e:
        raise e

    return response
