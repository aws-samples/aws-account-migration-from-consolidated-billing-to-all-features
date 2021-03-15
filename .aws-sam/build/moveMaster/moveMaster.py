'''
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
'''

import boto3
import os
import botocore

ROLE_ARN=os.environ['ROLE_ARN']
ACCOUNT_TABLE_NAME=os.environ['ACCOUNT_TABLE_NAME']
OU_TABLE_NAME=os.environ['OU_TABLE_NAME']
ACCEPT_ROLE_NAME=os.environ['ACCEPT_ROLE_NAME']
OLD_ORG_MA=os.environ['OLD_ORG_MA']
OLD_MASTER_OU=os.environ['OLD_MASTER_OU']

ddb_client=boto3.client('dynamodb')
new_org_client=boto3.client('organizations')
s3_clinet=boto3.client('s3')

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

session_assumed=aws_session(role_arn=ROLE_ARN, session_name='ma_session')    
old_org_client=session_assumed.client('organizations')

def acceptInvitation(old_master_id, account_parent_name, new_root_id):
    # S3 Copy
    # EDP Email
    # ACCEPT_ROLE_ARN="arn:aws:iam::"+old_master_id+":role/"+ACCEPT_ROLE_NAME
    # print('Role name is' + ACCEPT_ROLE_ARN)

    try:
        delete_response = old_org_client.delete_organization()
        print(delete_response)
    except botocore.exceptions.ClientError as error:
        print ('Caught exception deleting old organizations')
        print(error)

    try:
        new_org_invite=new_org_client.invite_account_to_organization(
            Target={
                'Type': 'ACCOUNT',
                'Id': old_master_id            },
            Notes='Invitaion to join the new Org'
            )
        handshake_id=new_org_invite['Handshake']['Id']
        print(handshake_id)
    except botocore.exceptions.ClientError as error:
        print ('Caught exception inviting account')
        print(error)

    try:
        ddb_client.update_item(
            TableName=ACCOUNT_TABLE_NAME,
            Key={
                'AccountId': {'S': old_master_id}
            },
            UpdateExpression="SET HandshakeId = :NewHandshakeId",
            ExpressionAttributeValues={":NewHandshakeId": {"S": handshake_id}}
        )        
    except botocore.exceptions.ClientError as error:
        print ('Caught exception updating item')
        print(error)

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
        print ('Caught exception scanning getting item')
        print(error)

    try:
        accept_response = old_org_client.accept_handshake(
            HandshakeId = handshake_id
        )
        print(accept_response)
    except botocore.exceptions.ClientError as error:
        print ('Caught exception Accepting handshake')
        print(error)

    try:
        move_response = new_org_client.move_account(
            AccountId=old_master_id,
            SourceParentId=new_root_id,
            DestinationParentId=new_ou_id
        )
        print(move_response)
    except botocore.exceptions.ClientError as error:
        print ('Caught exception moving account')
        print(error)
                                
def lambda_handler(event, context):
    new_root_id=new_org_client.list_roots()["Roots"][0]["Id"]
    # **** S3 Copy ****
    # **** EDP Migration ****
    acceptInvitation(OLD_ORG_MA, OLD_MASTER_OU, new_root_id)