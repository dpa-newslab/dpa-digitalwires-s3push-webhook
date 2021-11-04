# S3 Push Setup

## Requirements

To receive articles by s3push, you must create a S3 bucket with appropriate
access rights in your AWS account. This is automatically done for you if you
follow the upcoming instructions. You need Node.js at least in version 8.

Please configure the AWS credentials of an admin user for the desired AWS account.
(references)[https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-envvars.html]

Futhermore you need to login to the (AWS Console)[https://eu-central-1.console.aws.amazon.com/ses/home?region=eu-central-1]
to verify an email address which should be used in case of errors. This email
address needs to be referenced in the `serverless.yml` file:

```
notification_mail: my@notification.mail # CHANGE THIS!
```

The variables for the API-Endpoint and the API-Key of the endpoint need to be
put into the Parameter Store of the (Systems Manager)[https://eu-central-1.console.aws.amazon.com/systems-manager/parameters/?region=eu-central-1].

These parameters are referenced in the `serverless.yml` by:

```
/mycompany/$STAGE/dpa_s3push/api_endpoint
/mycompany/$STAGE/dpa_s3push/api_apikey
```

## Deploy to AWS with the helper script provided in this repository:

Change the bucket name (the bucket must not yet exist) and the path prefix in `serverless.yml`.

```
nano serverless.yml
```

Then run the following commands in a Unix shell:

```
npm install
npm run deploy
```

If the installation was successful, the following output appears:

```
Stack Outputs
S3PushDeliveryQueueUrl: https://sqs.eu-central-1.amazonaws.com/{accountId}/{qs_name}]
S3PushSecretAccessKey: xxxx
S3PushUrlPrefix: s3://{s3_bucket_name}/{s3_prefix}
S3PushAccessKeyId: AKIAIxxxxx
...
```

To set up the delivery, please either contact your contact person or configure
the API in the customer portal of dpa-infocom GmbH (https://api-portal.dpa-newslab.com/api/s3push).

Please enter the output for S3 URL prefix, Access Key ID und Secret Access Key
in the given form.
