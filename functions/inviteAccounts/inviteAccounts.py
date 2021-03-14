'''
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
'''

import boto3
import botocore
import os

ACCOUNT_TABLE_NAME=os.environ['ACCOUNT_TABLE_NAME']
OLD_ORG_MA=os.environ['OLD_ORG_MA']

ddb_client=boto3.client('dynamodb')
new_org_client=boto3.client('organizations')

def inviteAccounts():
    try:
        response=ddb_client.scan(
            TableName=ACCOUNT_TABLE_NAME,
            AttributesToGet=['AccountId']
            )
        for account in response['Items']:
            account_id=account['AccountId']['S']
            if account_id != OLD_ORG_MA:
                print('Sending inviation to ' + account_id)
                try:
                    new_org_invite=new_org_client.invite_account_to_organization(
                        Target={
                            'Type': 'ACCOUNT',
                            'Id': account_id            },
                        Notes='Invitaion to join the new Org-New'
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
                            'AccountId': {'S': account_id}
                        },
                        UpdateExpression="SET HandshakeId = :NewHandshakeId",
                        ExpressionAttributeValues={":NewHandshakeId": {"S": handshake_id}}
                    )        
                except botocore.exceptions.ClientError as error:
                    print ('Caught exception updating item')
                    print(error)
            else:
                print('Skipping inviation for old management account: ' + account_id)
    except botocore.exceptions.ClientError as error:
        print ('Caught exception scanning DynamoDB table')
        print(error)

def lambda_handler(event, context):
    inviteAccounts()