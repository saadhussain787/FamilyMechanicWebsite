import json
import boto3
import os
from botocore.exceptions import ClientError

# Initialize AWS clients outside the handler for optimal serverless performance
ses_client = boto3.client('ses', region_name='ca-central-1')
sns_client = boto3.client('sns', region_name='ca-central-1')

def lambda_handler(event, context):
    print("Received incoming form event: ", json.dumps(event))
    
    # -------------------------------------------------------------------------
    # 1. PREFLIGHT OPTIONS CHECKER
    # Intercepts browser OPTIONS requests and immediately returns 200 OK with CORS headers.
    # Essential when using API Gateway proxy integrations configured on 'ANY' routes.
    # -------------------------------------------------------------------------
    http_method = event.get('requestContext', {}).get('http', {}).get('method', '').upper()
    legacy_method = event.get('httpMethod', '').upper()
    
    if http_method == 'OPTIONS' or legacy_method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'OPTIONS,POST'
            },
            'body': json.dumps({'message': 'Preflight handshake approved.'})
        }
    
    # -------------------------------------------------------------------------
    # 2. PAYLOAD PARSING
    # Parse out the incoming payload data gracefully.
    # -------------------------------------------------------------------------
    try:
        # Check if data is coming from a raw API Gateway proxy trigger or direct json body
        if 'body' in event:
            body_data = json.loads(event['body'])
        else:
            body_data = event
            
        customer_name = body_data.get('name', 'N/A')
        customer_phone = body_data.get('phone', 'N/A')
        vehicle_details = body_data.get('vehicle', 'N/A')
        reported_issue = body_data.get('issue', 'N/A')
        requested_date = body_data.get('date', 'N/A')
        
    except Exception as parse_error:
        print(f"Payload parsing error: {str(parse_error)}")
        return {
            'statusCode': 400,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'OPTIONS,POST'
            },
            'body': json.dumps({'message': 'Malformed data payload configuration.'})
        }

    # 3. Construct clean communication structures
    notification_subject = f"New Appointment Request: {customer_name}"
    notification_body = (
        f"My Choice Auto Service - Appointment Details:\n"
        f"=========================================\n"
        f"Customer Name: {customer_name}\n"
        f"Phone Number: {customer_phone}\n"
        f"Vehicle: {vehicle_details}\n"
        f"Reported Issue: {reported_issue}\n"
        f"Preferred Date: {requested_date}\n"
        f"=========================================\n"
    )

    # Define verified transmission identities (Using your personal verified address for testing)
    TARGET_EMAIL = "arfa787.sa@gmail.com" 

    execution_errors = []

    # 4. Execution Component A: Process the Email via Amazon SES
    try:
        ses_client.send_email(
            Source=TARGET_EMAIL,
            Destination={'ToAddresses': [TARGET_EMAIL]},
            Message={
                'Subject': {'Data': notification_subject},
                'Body': {'Text': {'Data': notification_body}}
            }
        )
        print("SES Email notification processed successfully.")
    except ClientError as ses_error:
        print(f"SES Failure: {ses_error.response['Error']['Message']}")
        execution_errors.append(f"Email error: {ses_error.response['Error']['Message']}")

    # 5. Execution Component B: Process the SMS text via Amazon SNS
    # This block is safely isolated so it wont crash your email stream while sandbox removal updates process!
    try:
        # Retrieve the exact SNS Topic ARN created in Step 28-B
        TOPIC_ARN = "arn:aws:sns:ca-central-1:303238378489:MechanicFormNotifications"
        
        sns_client.publish(
            TopicArn=TOPIC_ARN,
            Message=f"Appt Request: {customer_name} ({customer_phone}) - {vehicle_details}. Check email for issue details.",
            Subject="New Lead Alert"
        )
        print("SNS Text notification processed successfully.")
    except ClientError as sns_error:
        print(f"SNS Sandbox/Permission Bypass Active: {sns_error.response['Error']['Message']}")
        # We catch the sandbox errors gracefully so the total function response still finishes cleanly!

    # 6. Return clean API Gateway friendly responses
    if len(execution_errors) == 0 or (len(execution_errors) == 1 and "Email" not in execution_errors[0]):
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'OPTIONS,POST'
            },
            'body': json.dumps({'message': 'Appointment request routed successfully!'})
        }
    else:
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'OPTIONS,POST'
            },
            'body': json.dumps({'message': 'Failed to process infrastructure pipelines.', 'details': execution_errors})
        }