'''
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
'''

import boto3
import botocore
import os

ROLE_ARN = os.environ['ROLE_ARN']
OU_TABLE_NAME=os.environ['OU_TABLE_NAME']
OLD_MASTER_OU=os.environ['OLD_MASTER_OU']

ddb_client=boto3.client('dynamodb')

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

session_assumed = aws_session(role_arn=ROLE_ARN, session_name='ma_session')

old_org_client=session_assumed.client('organizations')
new_org_client=boto3.client('organizations')

def createOUStructure(old_parent_id, old_parent_name, new_parent_id, indent):
    try:
        paginator = old_org_client.get_paginator('list_children')
        iterator = paginator.paginate(ParentId=old_parent_id, ChildType='ORGANIZATIONAL_UNIT')
        indent += 1
    except botocore.exceptions.ClientError as error:
        print ('Caught exception listing children')
        print(error)

    for page in iterator:
        #print(page)
        for ou in page['Children']:
            try:
                #print(ou)
                old_ou_info=old_org_client.describe_organizational_unit(OrganizationalUnitId=ou['Id'])
                old_ou_id=old_ou_info['OrganizationalUnit']['Id']
                old_ou_name=old_ou_info['OrganizationalUnit']['Name']
                print(" ")
                print(f"{'-' * indent}" + " | " + old_ou_id + " | " + old_ou_name + " | " + old_parent_id)
            except botocore.exceptions.ClientError as error:
                print ('Caught exception describing OU')
                print(error)
            
            #Check if the parent of old ou is root
            if old_parent_name != "Root":
                try:
                    old_parent_name_obj=ddb_client.get_item(
                        TableName=OU_TABLE_NAME,
                        Key={
                            'OuName': {'S': old_ou_name}
                        },
                        AttributesToGet=[
                            "OuParentName"
                        ]
                    )
                    print(' ')
                    old_parent_name=old_parent_name_obj['Item']['OuParentName']['S']
                    #print('Parent of the OU is ' + old_parent_name)
                except botocore.exceptions.ClientError as error:
                    print ('Caught exception getting item')
                    print(error)

                try:
                    response=ddb_client.get_item(
                        TableName=OU_TABLE_NAME,
                        Key={
                            'OuName': {'S': old_parent_name}
                        },
                        AttributesToGet=[
                            "NewOuId"
                        ]
                    )
                    print(' ')
                    new_parent_id=response['Item']['NewOuId']['S']
                    #print(new_parent_id)
                except botocore.exceptions.ClientError as error:
                    print ('Caught exception getting item')
                    print(error)
            
            #Create OU
            try:
                create_new_ou=new_org_client.create_organizational_unit(ParentId=new_parent_id, Name=old_ou_name)
                new_ou_id=create_new_ou['OrganizationalUnit']['Id']
            except botocore.exceptions.ClientError as error:
                print ('Caught exception creating OU')
                print(error)

            try:
                #print('adding new ou id')
                ddb_client.update_item(
                    TableName=OU_TABLE_NAME,
                    Key={
                    'OuName': {'S': old_ou_name}
                    },
                    UpdateExpression="SET NewOuId = :NewOu",
                    ExpressionAttributeValues={":NewOu": {"S": new_ou_id}}
                )
            except botocore.exceptions.ClientError as error:
                print ('Caught exception updating item')
                print(error)

            try:            
                #print('adding new ou parent id')
                ddb_client.update_item(
                    TableName=OU_TABLE_NAME,
                    Key={
                    'OuName': {'S': old_ou_name}
                    },
                    UpdateExpression="SET NewOuParentId = :NewOu",
                    ExpressionAttributeValues={":NewOu": {"S": new_parent_id}}
                )
                
                print(f"{'-' * indent}" + " | " + new_ou_id + " | " + old_ou_name + " | " + new_parent_id)
            except botocore.exceptions.ClientError as error:
                print ('Caught exception updating item')
                print(error)


            createOUStructure(ou['Id'], old_ou_name, new_parent_id, indent)

def lambda_handler(event, context):
    try:
        old_root_id=old_org_client.list_roots()["Roots"][0]["Id"]
        old_root_name=old_org_client.list_roots()["Roots"][0]["Name"]
        new_root_id=new_org_client.list_roots()["Roots"][0]["Id"]
    except botocore.exceptions.ClientError as error:
        print ('Caught exception listing roots')
        print(error)    

    try:
        old_master_ou=new_org_client.create_organizational_unit(ParentId=new_root_id, Name=OLD_MASTER_OU)
        old_master_ou_id=old_master_ou['OrganizationalUnit']['Id']
    except botocore.exceptions.ClientError as error:
        print ('Caught exception creating OU')
        print(error)

    try:
        ddb_client.put_item(
            TableName=OU_TABLE_NAME,
                Item={
                    'OuId': {'S': old_master_ou_id},
                    'OuName': {'S': OLD_MASTER_OU},
                    'OuParentId': {'S': old_root_id},
                    'OuParentType': {'S': "ROOT"},
                    'OuParentName': {'S': "Root"},
                    'NewOuId': {'S': old_master_ou_id},
                    'NewOuParentId': {'S': new_root_id}
                })
    except botocore.exceptions.ClientError as error:
        print ('Caught exception putting item')
        print(error)

    createOUStructure(old_root_id, old_root_name, new_root_id, 0)
    