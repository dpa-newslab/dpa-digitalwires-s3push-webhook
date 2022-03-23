# Import dpa-digitalwires via s3push-API

In this repository we show two best practices of how to receive dpa-digitalwires
via s3push and show further possible scenarios of processing the data.

## basic

A basic setup to receive articles via s3push and send them to an API-Endpoint.

## extended

An extended setup sending received articles to an API-Endpoint, asynchronously
checking the insertion status and containing a dead letter queue in case of
failures which triggers retries or sending an email notification via SNS.

## Preprocess articles before sending them to an API

If articles should be transformed before sending them to an API-endpoint or the sorting of sent articles is important, please take a look at the extended [s3push-example](https://github.com/dpa-newslab/dpa-digitalwires-s3push-example/tree/main/extended). Using it guarantees only the latest received version of an article will be transformed and further processed. Deploying the project will create three CloudFormation-stacks, allowing you to receive articles via s3push and setting up transformation and deduplication. 

The `sqs_receive`-project creates a SQS-FIFO-queue to receive articles in guaranteed order. You might unite this part with the setup provided for webhook-integration in this repository, so that the `DeliveryQueue` receives SNS-notifications for transformed articles (instead of s3push-received articles as specified in this project). Be aware, that your `DeliveryQueue` has to be FIFO then. (check [the example project](https://github.com/dpa-newslab/dpa-digitalwires-s3push-example/blob/main/extended/sqs_receive/serverless.yml) for details on the setup)