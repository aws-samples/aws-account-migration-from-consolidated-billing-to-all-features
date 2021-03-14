'''
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
'''

import boto3
import botocore
import os

ROLE_ARN=os.environ['ROLE_ARN']
OLD_ORG_MA=os.environ['OLD_ORG_MA']
OU_TABLE_NAME=os.environ['OU_TABLE_NAME']
ACCOUNT_TABLE_NAME=os.environ['ACCOUNT_TABLE_NAME']

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
session_regular=aws_session()
    
org_client=session_assumed.client('organizations')
ddb_client=boto3.client('dynamodb')
        
def findOrgInfo(session_assumed, account):
    org_client=session_assumed.client('organizations')
    org_info=org_client.list_accounts()
    
    for accounts in org_info['Accounts']:
        account_id=accounts['Id']
        account_name=accounts['Name']
        account_email=accounts['Email']
        account_arn=accounts['Arn']
        print(account_id + '|' + account_name + '|' + account_email + '|' + account_arn)
        
        try:
            parent_info=org_client.list_parents(ChildId=account_id)
            for parents in parent_info['Parents']:
                parent_id=parents['Id']
                parent_type=parents['Type']
                print(account_id + '|' + account_name + '|' + account_email + '|' + account_arn + '|' + parent_id + '|' + parent_type)
                
                while parent_type != "ROOT":
                    print('working on account: ' + account_name)
                    ou_id=parent_id
                    ou_type=parent_type
                    ou_info=org_client.describe_organizational_unit(OrganizationalUnitId=parent_id)
                    ou_name=ou_info['OrganizationalUnit']['Name']
                    ou_arn=ou_info['OrganizationalUnit']['Arn']
                    print(ou_id + '|' + ou_name + '|' + ou_arn + '|' + ou_type)                #print('parent info')
                    parent_info=org_client.list_parents(ChildId=parent_id)
                    parent_id=parent_info['Parents'][0]['Id']
                    parent_type=parent_info['Parents'][0]['Type']
        except botocore.exceptions.ClientError as error:
            print ('Caught exception listing parents')
            print(error)

def getOuInfo(org_client, parent_id, indent):
    paginator=org_client.get_paginator('list_children')
    iterator=paginator.paginate(ParentId=parent_id, ChildType='ORGANIZATIONAL_UNIT')
    indent += 1
    for page in iterator:
        for ou in page['Children']:
            try:
                ou_info=org_client.describe_organizational_unit(OrganizationalUnitId=ou['Id'])
                ou_id=ou_info['OrganizationalUnit']['Id']
                ou_name=ou_info['OrganizationalUnit']['Name']
            except botocore.exceptions.ClientError as error:
                print ('Caught exception describing organiation')
                print(error)

            try:
                parent_info=org_client.list_parents(ChildId=ou_id)
                for ids in parent_info['Parents']:
                    ou_parent_id=ids['Id']
                    ou_parent_type=ids['Type']
                    if ou_parent_type == "ROOT":
                        ou_parent_name=org_client.list_roots()["Roots"][0]["Name"]
                    if ou_parent_type == "ORGANIZATIONAL_UNIT":
                        ou_parent_info=org_client.describe_organizational_unit(OrganizationalUnitId=ou_parent_id)
                        ou_parent_name=ou_parent_info['OrganizationalUnit']['Name']
                #print(f"{'-' * indent}" + " | " + ou_id + " | " + ou_name + " | " + ou_arn )
                print(f"{'-' * indent}" + " | " + ou_id + " | " + ou_name)
            except botocore.exceptions.ClientError as error:
                print ('Caught exception listing parents')
                print(error)

            try:
                ddb_client.put_item(
                TableName=OU_TABLE_NAME,
                Item={
                    'OuId': {'S': ou_id},
                    'OuName': {'S': ou_name},
                    'OuParentId': {'S': ou_parent_id},
                    'OuParentType': {'S': ou_parent_type},
                    'OuParentName': {'S': ou_parent_name}
                })

                getAccountInfo(org_client, ou['Id'], indent)
                getOuInfo(org_client, ou['Id'], indent)
            except botocore.exceptions.ClientError as error:
                print ('Caught exception putting item in the DyanmodDb Table')
                print(error)

def getAccountInfo(org_client, parent_id, indent):
    try:
        account_paginator=org_client.get_paginator('list_children')
        account_iterator=account_paginator.paginate(ParentId=parent_id, ChildType='ACCOUNT')
        indent += 1
    except botocore.exceptions.ClientError as error:
        print ('Caught exception listing children')
        print(error)

    for account_page in account_iterator:
        for account in account_page['Children']: 
            try:           
                account_info=org_client.describe_account(AccountId=account['Id'])
                account_id=account_info['Account']['Id']
                account_name=account_info['Account']['Name']
                account_email=account_info['Account']['Email']
                account_arn=account_info['Account']['Arn']
                account_status=account_info['Account']['Status']
                print(f"{'-' * indent}" + " | " +  account_id + " | " + account_name + " | " + account_email + " | " + account_status)
            except botocore.exceptions.ClientError as error:
                print ('Caught exception describing account')
                print(error)

            try:
                parent_info=org_client.list_parents(ChildId=account_id)
                for ids in parent_info['Parents']:
                    account_parent_id=ids['Id']
                    account_parent_type=ids['Type']
            except botocore.exceptions.ClientError as error:
                print ('Caught exception listing parents')
                print(error)
                
            account_parent_info=org_client.describe_organizational_unit(OrganizationalUnitId=account_parent_id)
            account_parent_name=account_parent_info['OrganizationalUnit']['Name']
            try:
                ddb_client.put_item(
                TableName=ACCOUNT_TABLE_NAME,
                Item={
                    'AccountId': {'S': account_id},
                    'AccountName': {'S': account_name},
                    'AccountEmail': {'S': account_email},
                    #'AccountArn': {'S': account_arn},
                    'AccountParentId': {'S': account_parent_id},
                    'AccountParentName': {'S': account_parent_name},
                    'AccountParentType': {'S': account_parent_type},
                    'AccountStatus': {'S': account_status}
                })
            except botocore.exceptions.ClientError as error:
                print ('Caught exception putting item in the DyanmodDb Table')
                print(error)
    
def getMasterAccountInfo(org_client, account_number):
    try:
        account_info=org_client.describe_account(AccountId=account_number)
        account_id=account_info['Account']['Id']
        account_name=account_info['Account']['Name']
        account_email=account_info['Account']['Email']
        account_arn=account_info['Account']['Arn']
        account_status=account_info['Account']['Status']
    except botocore.exceptions.ClientError as error:
        print ('Caught exception describing account')
        print(error)

    try:
        parent_info=org_client.list_parents(ChildId=account_id)
        for ids in parent_info['Parents']:
            account_parent_id=ids['Id']
            account_parent_type=ids['Type']
    except botocore.exceptions.ClientError as error:
        print ('Caught exception listing parents')
        print(error)

    try:        
        ddb_client.put_item(
        TableName=ACCOUNT_TABLE_NAME,
        Item={
            'AccountId': {'S': account_id},
            'AccountName': {'S': account_name},
            'AccountEmail': {'S': account_email},
            'AccountStatus': {'S': account_status},
            'AccountParentId': {'S': account_parent_id},
            'AccountParentName': {'S': "ROOT"},
            'AccountParentType': {'S': account_parent_type},
        })
        #print(" "+ account_id + " | " + account_name + " | " + account_email + " | " + account_status)
    except botocore.exceptions.ClientError as error:
        print ('Caught exception putting item in the DyanmodDb Table')
        print(error)
    
def lambda_handler(event, context):
    root_id=org_client.list_roots()["Roots"][0]["Id"]
    root_name=org_client.list_roots()["Roots"][0]["Name"]
    root_arn=org_client.list_roots()["Roots"][0]["Arn"]
    print(" "+ root_id + " | " + root_name)

    getMasterAccountInfo(org_client, OLD_ORG_MA)
    getOuInfo(org_client, root_id, 0)