import json
from urllib.request import Request, urlopen
import logging
import os
import boto3

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

mapping_dict = json.loads(os.environ['MAPPING_DICT'])
slack_webHook_URL = os.environ['SLACK_WEBHOOK_URL']
slack_alert_webHook_URL = os.environ['SLACK_ALERT_WEBHOOK_URL']
assume_role_name = os.environ['ASSUME_ROLE_NAME']
SENDER = os.getenv('EXCEPTION_SENDER', 'shreyansluker26@gmail.com')
RECIPIENTS = os.getenv('EXCEPTION_SENDER', 'shreyansluker26@gmail.com')
critical_accounts = os.environ['CRITICAL_ACCOUNTS'].split(',')
sts = boto3.client('sts')

def send_email_exception(ex):
    CHARSET = "UTF-8"
    # The HTML body of the email.
    BODY_HTML = """<html>
    <head></head>
    <body>
      <h1>Exception Occurred  for Login notifications to slack</h1>
      <p> Failed with Exception <strong>{}</strong> </p>
    </body>
    </html>
                """.format(ex)
    ses_client = boto3.client('ses')
    ses_client.send_email(
        Destination={
            'ToAddresses': [RECIPIENTS],
        },
        Message={
            'Body': {
                'Html': {
                    'Charset': CHARSET,
                    'Data': BODY_HTML,
                },
            },
            'Subject': {
                'Charset': 'UTF-8',
                'Data': 'Exception Occurred in Login notifications to slack'
            },
        },
        Source=SENDER,
    )

def send_email(body, subject):
    CHARSET = "UTF-8"
    client = boto3.client('ses')
    client.send_email(
        Destination={
            'ToAddresses': [RECIPIENTS]
        },
        Message={
            'Body': {
                'Html': {
                    'Charset': CHARSET,
                    'Data': body,
                },
            },
            'Subject': {
                'Charset': 'UTF-8',
                'Data': subject,
            },
        },
        Source=SENDER,
    )

# send to slack function
def send_webhook(event):
    aws_account = event['detail']['userIdentity']['accountId']
    awsRegion = str(event['detail']['awsRegion'])
    env = mapping_dict[aws_account]
    eventName = str(event['detail']['eventName'])
    eventTime = str(event['detail']['eventTime'])
    consoleLogin = str(event['detail']['responseElements']['ConsoleLogin'])
    mfa = str(event['detail']['additionalEventData']['MFAUsed'])
    if (consoleLogin == "Success"):
        userType = str(event['detail']['userIdentity']['type'])
        if (userType == "Root"):
            userName = str(event['detail']['userIdentity']['type'])
            printMessage = "Root Login Detected"
        else:
            userName = str(event['detail']['userIdentity']['arn']).split('/')[-1]
            if (mfa == "No"):
                printMessage = "Login without MFA found"
            else:
                return
    else:
        errorMessage = str(event['detail']['errorMessage'])
        if (errorMessage == "Failed authentication"):
            userName = str(event['detail']['userIdentity']['userName'])
            printMessage = str(event['detail']['errorMessage'])
        else:
            printMessage = str(event['detail']['errorMessage'])
            userName = "No User Exists"

    if (printMessage == "Root Login Detected"):
        icon = "rotating_light"
        slack_title = str(
            "*:" + icon + ": [{}] - Login Notification - {} :".format(env,printMessage) + icon + ":*")
        color = "danger"
    elif (printMessage == "No username found in supplied account"):
        icon = "rotating_light"
        slack_title = str(
            "*:" + icon + ": [{}] - Login Notification - {} :".format(env,printMessage) + icon + ":*")
        color = "danger"
    else:
        icon = "warning"
        slack_title = str(
            "*:" + icon + ": [{}] - Login Notification - {} :".format(env,printMessage) + icon + ":*")
        color = "warning"
    subject = f"[{env}] - Root Login detected "
    body = f"""<html>
    <head></head>
    <body>
      <h4>Root Login detected</h4>
      <h4>Event Name: {eventName}</h4>
      <h4>AccountID: {aws_account} - ({env})</h4>
      <h4>Event Time: {eventTime}</h4>

      <h4>Details:</h4>
      <p><pre>{json.dumps(event, indent=2)} </pre></p>
    </body>
    </html>"""

    slack_message = {
        "username": 'aws_login_notification',
        "icon_emoji": ':aws:',
        "text": slack_title,
        "attachments": [
            {
                "color": color,
                "fields": [
                    {"title": "UserName(s)", "value": userName, "short": True},
                    {"title": "ErrorMessage", "value": printMessage, "short": True},
                    {"title": "Event Name", "value": eventName, "short": True},
                    {"title": "Event Time", "value": eventTime, "short": True},
                    {"title": "Region", "value": awsRegion, "short": True},
                    {"title": "Account", "value": aws_account, "short": True},
                ],
            },
            {
                "color": color,
                "text": "```{}```".format(json.dumps(event, indent=1)),
            }
        ]
    }

    if (printMessage == "Root Login Detected"):
        send_email(body, subject)
        req = Request(slack_webHook_URL, data=json.dumps(slack_message).encode("utf-8"),
                    headers={"content-type": "application/json"})
    else:
        req = Request(slack_webHook_URL, data=json.dumps(slack_message).encode("utf-8"),
                    headers={"content-type": "application/json"})
    response = urlopen(req)
    response.read()
    logger.info("Message sent to slack")
        
def lambda_handler(event, context):
    try:
        logger.info(event)
        send_webhook(event)
    except Exception as e:
        logger.error("Request failed : {}".format(str(e)))
        send_email_exception(str(e))
