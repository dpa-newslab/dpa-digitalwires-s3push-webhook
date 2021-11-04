# Import dpa-digitalwires via s3push-API

In this repository we show two best practices of how to receive dpa-digitalwires
via s3push and show further possible scenarios of processing the data.

## basic

A basic setup to receive articles via s3push and send them to an API-Endpoint.

## extended

An extended setup sending received articles to an API-Endpoint, asynchronously
checking the insertion status and containing a dead letter queue in case of
failures which triggers retries or sending an email notification via SNS.
