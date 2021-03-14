'''
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
'''

import boto3
import botocore
import os

ACCOUNT_TABLE_NAME=os.environ['ACCOUNT_TABLE_NAME']
OU_TABLE_NAME=os.environ['OU_TABLE_NAME']
ACCEPT_ROLE_NAME=os.environ['ACCEPT_ROLE_NAME']

def aws_session(role_arn=None, session_name='ma_session'):
    """
    If role_arn is given assumes a role and returns boto3 session
    otherwise return a regular session with the current IAM user/role
    """
    if role_arn:
        client=boto3.client('sts')
        try:
            response=client.assume_role(RoleArn=role_arn, RoleSessionName=session_name)
            session=boto3.Session(
                aws_access_key_id=response['Credentials']['AccessKeyId'],
                aws_secret_access_key=response['Credentials']['SecretAccessKey'],
                aws_session_token=response['Credentials']['SessionToken'])
            return session
        except botocore.exceptions.ClientError as error:
            print ('Caught exception creating a session')
            print(error)
    else:
        return boto3.Session()

ddb_client=boto3.client('dynamodb')
new_org_client=boto3.client('organizations')

def acceptInvitation(new_root_id):
    try:
        response=ddb_client.scan(
            TableName=ACCOUNT_TABLE_NAME,
            AttributesToGet=['AccountId']
            )
    except botocore.exceptions.ClientError as error:
        print ('Caught exception scanning DynamoDB table')
        print(error)

    for account in response['Items']:
        account_id=account['AccountId']['S']
        try:
            account_info=ddb_client.get_item(
                TableName=ACCOUNT_TABLE_NAME,
                Key={
                    'AccountId': {'S': account_id}
                },
                AttributesToGet=[
                    "AccountParentType",
                    "HandshakeId",
                    "AccountParentName"
                ]
            )
            account_parent_type=account_info['Item']['AccountParentType']['S']
            account_parent_name=account_info['Item']['AccountParentName']['S']
            if account_parent_type != "ROOT":    
                handshake_id=account_info['Item']['HandshakeId']['S']
        except botocore.exceptions.ClientError as error:
            print ('Caught exception getting item')
            print(error)
        
        #print(account_parent_type)
        #print('account parent type is ' + account_parent_type)
        if account_parent_type == "ROOT":
            print('Skipping Master Account for now.., will work on it later')
        else:
            ACCEPT_ROLE_ARN="arn:aws:iam::"+account_id+":role/"+ACCEPT_ROLE_NAME
            try:
                ou_info=ddb_client.get_item(
                    TableName=OU_TABLE_NAME,
                    Key={
                        'OuName': {'S': account_parent_name}
                    },
                    AttributesToGet=[
                        "NewOuId"
                    ]
                )
                new_ou_id=ou_info['Item']['NewOuId']['S']
            except botocore.exceptions.ClientError as error:
                print ('Caught exception getting item')
                print(error)
            
            try:
                member_session_assumed = aws_session(role_arn=ACCEPT_ROLE_ARN, session_name='member_session')
                member_org_client = member_session_assumed.client('organizations')
            except botocore.exceptions.ClientError as error:
                print ('Caught exception assuming role in member account')
                print(error)

            try:
                print(account_id + ' is leaving old orginization')
                leave_response = member_org_client.leave_organization()
                print(leave_response)
            except botocore.exceptions.ClientError as error:
                print ('Caught exception leaving old organization')
                print(error)

            try:
                print('Accepting inviation for ' + account_id)
                accept_response = member_org_client.accept_handshake(
                    HandshakeId = handshake_id
                )
                print(accept_response)
                # update DDB Table with success for every account
            except botocore.exceptions.ClientError as error:
                print ('Caught exception accepting invitation')
                print(error)

            try:    
                print('Moving ' + account_id + ' to the new Org under the OU ' + new_ou_id)
                move_response = new_org_client.move_account(
                    AccountId=account_id,
                    SourceParentId=new_root_id,
                    DestinationParentId=new_ou_id
                )
                print(move_response)
            except botocore.exceptions.ClientError as error:
                print ('Caught exception moving account to the correct OU in the new Org')
                print(error)

def lambda_handler(event, context):
    try:
        new_root_id=new_org_client.list_roots()["Roots"][0]["Id"]
    except botocore.exceptions.ClientError as error:
        print ('Caught exception listing roots')
        print(error)    

    acceptInvitation(new_root_id)
    