# Automating Migration of AWS Accounts from Consolidated Billing to All Features 

This project contains source code and supporting files for a serverless application that you can use to migration accounts from an existing (also referred as "old" in the documentation) AWS Organization with Consolidated Billing to a new AWS Organization with All Features enabled. 

You can deploy the serverless application with the SAM CLI, which includes the following files and folders:

- functions - Code for the application's AWS Lambda functions:
    - scanOldOrg - Scans the old AWS Organization and persists the details of AWSAccounts and AWS Organizational Units in Amazon DynamoDB Tables
    - replicateOuStructure - Replicates the old AWS Organization structure in the new AWS Organization
    - inviteAccounts - Sends invitations from new AWS Organization to all the accounts in the old AWS Organization
    - acceptInvitation - Assumes an IAM role in each member account of the old AWS Organizaton to accept the invitation from the new AWS Organization and moves accounts into the appropriate OUs as per the old AWS Organization's structure.
    - moveMaster - Assumes an IAM role in the Management Account of the old AWS Organization to accept the invitation from the new AWS Organization and moves account into a separate OU dedicated for the Management Account.
- statemachines - Definition for the state machine that orchestrates the account migration workflow.
- template.yaml - A template that defines the application's AWS resources.

The application uses several AWS resources, including AWS Step Functions state machines, AWS Lambda functions and Amazon DynamoDB tables. These resources are defined in the `template.yaml` file. You can update the template to add AWS resources through the same deployment process that updates your application code.

If you prefer to use an integrated development environment (IDE) to build and test the Lambda functions within your application, you can use the AWS Toolkit. The AWS Toolkit is an open source plug-in for popular IDEs that uses the SAM CLI to build and deploy serverless applications on AWS. The AWS Toolkit also adds a simplified step-through debugging experience for Lambda function code. See the following links to get started:

* [PyCharm](https://docs.aws.amazon.com/toolkit-for-jetbrains/latest/userguide/welcome.html)
* [IntelliJ](https://docs.aws.amazon.com/toolkit-for-jetbrains/latest/userguide/welcome.html)
* [VS Code](https://docs.aws.amazon.com/toolkit-for-vscode/latest/userguide/welcome.html)
* [Visual Studio](https://docs.aws.amazon.com/toolkit-for-visual-studio/latest/user-guide/welcome.html)

The AWS Toolkit for VS Code includes full support for state machine visualization, enabling you to visualize your state machine in real time as you build. The AWS Toolkit for VS Code includes a language server for Amazon States Language, which lints your state machine definition to highlight common errors, provides auto-complete support, and code snippets for each state, enabling you to build state machines faster.

## Prerequisites

### Steps in the ** Existing ** AWS Organizations

1.  Copy Cost and Usage Reports (CUR) to the new AWS Organizations by configuring CUR file replication from the source Amazon Simple Storage Service (S3) Bucket in the Management Account of existing AWS Organizations to an S3 bucket in the Management Account of the new AWS Organizations. 
[Instructions to set up rules to replicate objects between buckets](https://aws.amazon.com/blogs/storage/replicating-existing-objects-between-s3-buckets/)

2. Ensure that all the accounts have payment type set to Invoice (AWS Account team will work with the Customer)

3. In every terminal used to run the provided application, ensure the following tools are installed and the code is downloaded:
    1. AWS CLI - [Install the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html)

    The AWS Command Line Interface (AWS CLI) is an open source tool that enables you to interact with AWS services using commands in your command-line shell. With minimal configuration, the AWS CLI enables you to start running commands that implement functionality equivalent to that provided by the browser-based AWS Management Console from the command prompt in your terminal program.

    2.  SAM CLI - [Install the SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)

    The Serverless Application Model Command Line Interface (SAM CLI) is an extension of the AWS CLI that adds functionality for building and testing Lambda applications. It uses Docker to run your functions in an Amazon Linux environment that matches Lambda.

    To use the SAM CLI, you need the following tools:

    * Python Version 3 - [Python 3 installed](https://www.python.org/downloads/)
    * Docker - [Install Docker community edition](https://hub.docker.com/search/?type=edition&offering=community)

    3.  Download the code

        ```
        git clone https://github.com/sguttiko/OrgMigration
        cd OrgMigration
        ```

4.  In the Management Account of the ** Existing AWS Organizations **

    1. Create an IAM Role (OrgInfoRole) with the following permissions

        Update the file iam/OrgInfoTrustPolicy.json with the Account Number of the Management Account in the new AWS Organizations

        ```
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                "Effect": "Allow",
                "Principal": {
                    "AWS": "arn:aws:iam::[111122223333]:root"
                },
                "Action": "sts:AssumeRole",
                "Condition": {}
                }
            ]
        }
        ```

    ```    
    aws iam create-role --role-name OrgInfoRole --assume-role-policy-document file://iam/OrgInfoTrustPolicy.json
    ```
    2. Create an IAM Policy (OrgInfoPolicy) with the following permissions

    ```
    aws iam create-policy --policy-name OrgInfoPolicy --policy-document file://iam/OrgInfoPermissionsPolicy.json
    ```

        ```
        {
            "Policy": {
                "PolicyName": "OrgInfoPolicy",
                "PolicyId": "ANPAT6COOHTEPSAYJ7V3Y",
                "Arn": "[arn:aws:iam::111122223333:policy/OrgInfoPolicy]",
                "Path": "/",
                "DefaultVersionId": "v1",
                "AttachmentCount": 0,
                "PermissionsBoundaryUsageCount": 0,
                "IsAttachable": true,
                "CreateDate": "2021-02-05T03:05:34+00:00",
                "UpdateDate": "2021-02-05T03:05:34+00:00"
            }
        }
        ```
        
        Note the ARN of the policy, you will use it to attach the crated OrgInfoPolicy to the OrgInfoRole.

    3. Attach the IAM policy (OrgInfoPolicy) to the IAM role (OrgInfoRole)

    ```
    aws iam attach-role-policy --role-name OrgInfoRole --policy-arn arn:aws:iam::111122223333:policy/OrgInfoPolicy
    ```

5.  In ** each ** of the Member Accounts of the ** existing AWS Organizations **

    1. Create an IAM Role (NewOrgAcceptHandshakeRole) with the following permissions

        ```
        If you have already configured trusted cross-account IAM roles from the Management Account to all the Member Accounts, you can use AWS CloudFormation Stack Sets to configure the required role (NewOrgAcceptHandshakeRole) in all the Member Accounts from the Management Account

        Otherwise, please proceed with the following steps
        ```

        ```
        git clone https://github.com/sguttiko/OrgMigration
        cd OrgMigration
        ```

        Update the file iam/OrgInfoTrustPolicy.json with the Account Number of the Management Account in the new AWS Organizations


        ```
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                "Effect": "Allow",
                "Principal": {
                    "AWS": "arn:aws:iam::[111122223333]:root"
                },
                "Action": "sts:AssumeRole",
                "Condition": {}
                }
            ]
        }
        ```


    ```
    aws iam create-role --role-name NewOrgAcceptHandshakeRole --assume-role-policy-document file://iam/OrgInfoTrustPolicy.json
    ```
    
    2. Create an IAM Policy (OrgInfoPolicy) with the following permissions

    ```
    aws iam create-policy --policy-name NewOrgAcceptHandshakePolicy --policy-document file://iam/NewOrgAcceptHandshakePolicy.json 
    ```

    ```
        {
            "Policy": {
                "PolicyName": "OrgInfoPolicy",
                "PolicyId": "ANPAT6COOHTEPSAYJ7V3Y",
                "Arn": "[arn:aws:iam::111122223333:policy/NewOrgAcceptHandshakePolicy]",
                "Path": "/",
                "DefaultVersionId": "v1",
                "AttachmentCount": 0,
                "PermissionsBoundaryUsageCount": 0,
                "IsAttachable": true,
                "CreateDate": "2021-02-05T03:05:34+00:00",
                "UpdateDate": "2021-02-05T03:05:34+00:00"
            }
        }
    ```
        
        Note the ARN of the policy, you will use it to attach the crated NewOrgAcceptHandshakePolicy to the NewOrgAcceptHandshakeRole.

    3. Attach the IAM policy (OrgInfoPolicy) to the IAM role (OrgInfoRole)

    ```
    aws iam attach-role-policy --role-name NewOrgAcceptHandshakeRole --policy-arn arn:aws:iam::111122223333:policy/NewOrgAcceptHandshakePolicy
    ```

### Steps in the ** New ** AWS Organizations
1.  Create an Account
2.  Create AWS Organizations in it with All Features

    ```
    aws organizations create-organization
    ```

    ```
        {
            "Organization": {
                "Id": "o-x5ehrxxxxx",
                "Arn": "arn:aws:organizations::444455556666:organization/o-x5ehrxxxxx",
                "FeatureSet": "ALL",
                "MasterAccountArn": "arn:aws:organizations::444455556666:account/o-x5ehrxxxxxx/444455556666",
                "MasterAccountId": "444455556666",
                "MasterAccountEmail": "test@xyz.com",
                "AvailablePolicyTypes": [
                    {
                        "Type": "SERVICE_CONTROL_POLICY",
                        "Status": "ENABLED"
                    }
                ]
            }
        }
    ```
	The account will become the Management Account in the new AWS Organizations
	
3. * **`IMPORTANT`**: 
    
        You will receive an email to the registered email address of the new account with the subject "AWS Organizations email verification request"
        
        Verify email address to invite existing AWS accounts to join your new AWS Organizations.

4. If customer has EDP/PPA on the existing account, add new Management Account to the EDP/PPA (AWS Account Team will help the customer)

## Deploy the application in the Management Account of the New AWS Organizations
To build and deploy your application for the first time, run the following in your shell:

1. Download the code in the terminal for the Management Account of the ** New ** AWS Organizations

    ```
    git clone https://github.com/sguttiko/OrgMigration
    cd OrgMigration
    ```

    **`NOTE`**: Ensure you are running python 3.7 with the following command:
    ```
    $ python --version
    Python 3.7.9
    ```

2. Build and Deploy the application

    ```
    sam build
    sam deploy --guided
    ```

Command `sam build --use-container`: Will build the source of your application. 

Command `sam deploy --guided`: Will package and deploy your application to AWS, with a series of prompts:

* **Stack Name**: The name of the stack to deploy to CloudFormation. This should be unique to your account and region, and a good starting point would be something matching your project name.
* **AWS Region**: The AWS region you want to deploy your app to.
* **Parameter OldOrgMA**: Management Account number of the old AWS Organization
* **Parameter OldOrgScanRole**: ARN of the IAM role in the Management Account of the old AWS Organization to be assumed to scan the Organizational Unit structure.
* **Parameter OldMasterOU**: Name of the Organizational Unit in the new AWS Organization under which the Management Account from the old AWS Organization is moved to
* **Parameter NewOrgAcceptHandshakeRole**: Name of the IAM role in each Member Account of the old AWS Organization which is assumed to accept the invitation from the new AWS Organization. 
* **`NOTE`**: Name of the Parameter "NewOrgAcceptHandshakeRole" has to be the same in all the member accounts.
* **Confirm changes before deploy**: If set to yes, any change sets will be shown to you before execution for manual review. If set to no, the AWS SAM CLI will automatically deploy application changes.
* **Allow SAM CLI IAM role creation**: Many AWS SAM templates, including this example, create AWS IAM roles required for the AWS Lambda function(s) included to access AWS services. By default, these are scoped down to minimum required permissions. To deploy an AWS CloudFormation stack which creates or modified IAM roles, the `CAPABILITY_IAM` value for `capabilities` must be provided. If permission isn't provided through this prompt, to deploy this example you must explicitly pass `--capabilities CAPABILITY_IAM` to the `sam deploy` command.
* **Save arguments to samconfig.toml**: If set to yes, your choices will be saved to a configuration file inside the project, so that in the future you can just re-run `sam deploy` without parameters to deploy changes to your application.

## Run the application

1. Invoke an AWS Step Functions state machine execution with the ARN from Outputs section of the SAM deployment
    ```
    aws stepfunctions start-execution --state-machine-arn [ARN of State Machine from the Output of sam deploy]
    ```
2. Ensure the state machine executed successfully

## Sample deployment

```bash
sam build

    Building codeuri: functions/scanOldOrg/ runtime: python3.7 metadata: {} functions: ['scanOldOrg']
    Running PythonPipBuilder:ResolveDependencies
    Running PythonPipBuilder:CopySource
    Building codeuri: functions/replicateOuStructure/ runtime: python3.7 metadata: {} functions: ['replicateOuStructure']
    Running PythonPipBuilder:ResolveDependencies
    Running PythonPipBuilder:CopySource
    Building codeuri: functions/inviteAccounts/ runtime: python3.7 metadata: {} functions: ['inviteAccounts']
    Running PythonPipBuilder:ResolveDependencies
    Running PythonPipBuilder:CopySource
    Building codeuri: functions/acceptInvitation/ runtime: python3.7 metadata: {} functions: ['acceptInvitation']
    Running PythonPipBuilder:ResolveDependencies
    Running PythonPipBuilder:CopySource
    Building codeuri: functions/moveMaster/ runtime: python3.7 metadata: {} functions: ['moveMaster']
    Running PythonPipBuilder:ResolveDependencies
    Running PythonPipBuilder:CopySource

    Build Succeeded

    Built Artifacts  : .aws-sam/build
    Built Template   : .aws-sam/build/template.yaml

    Commands you can use next
    =========================
    [*] Invoke Function: sam local invoke
    [*] Deploy: sam deploy --guided
```

```
sam deploy --guided

Configuring SAM deploy
======================

        Looking for config file [samconfig.toml] :  Not found

        Setting default arguments for 'sam deploy'
        =========================================
        Stack Name [sam-app]: OrgMigration
        AWS Region [us-east-1]: us-east-1
        Parameter OldOrgMA []: 111122223333
        Parameter OldOrgScanRole []: arn:aws:iam::111122223333:role/OrgInfoRole
        Parameter OldMasterOU []: OldMasterOU
        Parameter NewOrgAcceptHandshakeRole []: NewOrgAcceptHandshakeRole
        #Shows you resources changes to be deployed and require a 'Y' to initiate deploy
        Confirm changes before deploy [y/N]: y
        #SAM needs permission to be able to create roles to connect to the resources in your template
        Allow SAM CLI IAM role creation [Y/n]: y
        Save arguments to configuration file [Y/n]: y
        SAM configuration file [samconfig.toml]: 
        SAM configuration environment [default]: 

        Deploying with following values
        ===============================
        Stack name                   : OrgMigration
        Region                       : us-east-1
        Confirm changeset            : True
        Deployment s3 bucket         : aws-sam-cli-managed-default-samclisourcebucket-unierj59hcp0
        Capabilities                 : ["CAPABILITY_IAM"]
        Parameter overrides          : {"OldOrgMA": "111122223333", "OldOrgScanRole": "arn:aws:iam::111122223333:role/OrgInfoRole", "OldMasterOU": "OldMasterOU", "NewOrgAcceptHandshakeRole": "NewOrgAcceptHandshakeRole"}
        Signing Profiles             : {}

Initiating deployment
=====================
Uploading to OrgMigration/79cd56ac7400ad1537155ca49721279d.template  8675 / 8675.0  (100.00%)

Waiting for changeset to be created..

CloudFormation stack changeset
---------------------------------------------------------------------------------------------------------
Operation                  LogicalResourceId          ResourceType               Replacement              
---------------------------------------------------------------------------------------------------------
+ Add                      OldOrgAccountInfoTable     AWS::DynamoDB::Table       N/A                      
+ Add                      OldOrgOuInfoTable          AWS::DynamoDB::Table       N/A                      
+ Add                      OrgMigrationStateMachine   AWS::IAM::Role             N/A                      
                           Role                                                                           
+ Add                      OrgMigrationStateMachine   AWS::StepFunctions::Stat   N/A                      
                                                      eMachine                                            
+ Add                      acceptInvitationRole       AWS::IAM::Role             N/A                      
+ Add                      acceptInvitation           AWS::Lambda::Function      N/A                      
+ Add                      inviteAccountsRole         AWS::IAM::Role             N/A                      
+ Add                      inviteAccounts             AWS::Lambda::Function      N/A                      
+ Add                      moveMasterRole             AWS::IAM::Role             N/A                      
+ Add                      moveMaster                 AWS::Lambda::Function      N/A                      
+ Add                      replicateOuStructureRole   AWS::IAM::Role             N/A                      
+ Add                      replicateOuStructure       AWS::Lambda::Function      N/A                      
+ Add                      scanOldOrgRole             AWS::IAM::Role             N/A                      
+ Add                      scanOldOrg                 AWS::Lambda::Function      N/A                      
---------------------------------------------------------------------------------------------------------

Changeset created successfully. arn:aws:cloudformation:us-east-1:111122223333:changeSet/samcli-deploy1611540988/92dc5c65-2d84-428c-b11d-fb85978e5515


Previewing CloudFormation changeset before deployment
======================================================
Deploy this changeset? [y/N]: y

2021-01-25 03:15:25 - Waiting for stack create/update to complete

CloudFormation events from changeset
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------
ResourceStatus                             ResourceType                               LogicalResourceId                          ResourceStatusReason                     
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------
CREATE_IN_PROGRESS                         AWS::DynamoDB::Table                       OldOrgAccountInfoTable                     -                                        
CREATE_IN_PROGRESS                         AWS::IAM::Role                             replicateOuStructureRole                   -                                        
CREATE_IN_PROGRESS                         AWS::DynamoDB::Table                       OldOrgOuInfoTable                          -                                        
CREATE_IN_PROGRESS                         AWS::DynamoDB::Table                       OldOrgAccountInfoTable                     Resource creation Initiated              
CREATE_IN_PROGRESS                         AWS::IAM::Role                             replicateOuStructureRole                   Resource creation Initiated              
CREATE_IN_PROGRESS                         AWS::DynamoDB::Table                       OldOrgOuInfoTable                          Resource creation Initiated              
CREATE_COMPLETE                            AWS::IAM::Role                             replicateOuStructureRole                   -                                        
CREATE_COMPLETE                            AWS::DynamoDB::Table                       OldOrgAccountInfoTable                     -                                        
CREATE_COMPLETE                            AWS::DynamoDB::Table                       OldOrgOuInfoTable                          -                                        
CREATE_IN_PROGRESS                         AWS::IAM::Role                             acceptInvitationRole                       -                                        
CREATE_IN_PROGRESS                         AWS::IAM::Role                             inviteAccountsRole                         -                                        
CREATE_IN_PROGRESS                         AWS::IAM::Role                             acceptInvitationRole                       Resource creation Initiated              
CREATE_IN_PROGRESS                         AWS::IAM::Role                             moveMasterRole                             Resource creation Initiated              
CREATE_IN_PROGRESS                         AWS::IAM::Role                             inviteAccountsRole                         Resource creation Initiated              
CREATE_IN_PROGRESS                         AWS::IAM::Role                             moveMasterRole                             -                                        
CREATE_IN_PROGRESS                         AWS::IAM::Role                             scanOldOrgRole                             Resource creation Initiated              
CREATE_IN_PROGRESS                         AWS::IAM::Role                             scanOldOrgRole                             -                                        
CREATE_IN_PROGRESS                         AWS::Lambda::Function                      replicateOuStructure                       -                                        
CREATE_IN_PROGRESS                         AWS::Lambda::Function                      replicateOuStructure                       Resource creation Initiated              
CREATE_COMPLETE                            AWS::Lambda::Function                      replicateOuStructure                       -                                        
CREATE_COMPLETE                            AWS::IAM::Role                             inviteAccountsRole                         -                                        
CREATE_COMPLETE                            AWS::IAM::Role                             acceptInvitationRole                       -                                        
CREATE_COMPLETE                            AWS::IAM::Role                             moveMasterRole                             -                                        
CREATE_COMPLETE                            AWS::IAM::Role                             scanOldOrgRole                             -                                        
CREATE_IN_PROGRESS                         AWS::Lambda::Function                      inviteAccounts                             -                                        
CREATE_IN_PROGRESS                         AWS::Lambda::Function                      scanOldOrg                                 -                                        
CREATE_IN_PROGRESS                         AWS::Lambda::Function                      inviteAccounts                             Resource creation Initiated              
CREATE_IN_PROGRESS                         AWS::Lambda::Function                      moveMaster                                 -                                        
CREATE_IN_PROGRESS                         AWS::Lambda::Function                      acceptInvitation                           -                                        
CREATE_IN_PROGRESS                         AWS::Lambda::Function                      acceptInvitation                           Resource creation Initiated              
CREATE_IN_PROGRESS                         AWS::Lambda::Function                      scanOldOrg                                 Resource creation Initiated              
CREATE_IN_PROGRESS                         AWS::Lambda::Function                      moveMaster                                 Resource creation Initiated              
CREATE_COMPLETE                            AWS::Lambda::Function                      inviteAccounts                             -                                        
CREATE_COMPLETE                            AWS::Lambda::Function                      acceptInvitation                           -                                        
CREATE_COMPLETE                            AWS::Lambda::Function                      moveMaster                                 -                                        
CREATE_COMPLETE                            AWS::Lambda::Function                      scanOldOrg                                 -                                        
CREATE_IN_PROGRESS                         AWS::IAM::Role                             OrgMigrationStateMachineRole               -                                        
CREATE_IN_PROGRESS                         AWS::IAM::Role                             OrgMigrationStateMachineRole               Resource creation Initiated              
CREATE_COMPLETE                            AWS::IAM::Role                             OrgMigrationStateMachineRole               -                                        
CREATE_IN_PROGRESS                         AWS::StepFunctions::StateMachine           OrgMigrationStateMachine                   -                                        
CREATE_IN_PROGRESS                         AWS::StepFunctions::StateMachine           OrgMigrationStateMachine                   Resource creation Initiated              
CREATE_COMPLETE                            AWS::StepFunctions::StateMachine           OrgMigrationStateMachine                   -                                        
CREATE_COMPLETE                            AWS::CloudFormation::Stack                 OrgMigration                               -                                        
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------

CloudFormation outputs from deployed stack
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
Outputs                                                                                                                                                                   
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
Key                 OrgMigrationStateMachineRoleArn                                                                                                                       
Description         IAM Role created for State machine based on the specified SAM Policy Templates                                                                        
Value               arn:aws:iam::111122223333:role/OrgMigration-OrgMigrationStateMachineRole-YMGQ0C2E7IZU                                                                 

Key                 OrgMigrationStateMachineArn                                                                                                                           
Description         Org Migration State machine ARN                                                                                                                       
Value               arn:aws:states:us-east-1:111122223333:stateMachine:OrgMigrationStateMachine-HSCswl9XhNPV                                                              
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------

```

```
aws stepfunctions start-execution --state-machine-arn arn:aws:states:us-east-1:111122223333:stateMachine:OrgMigrationStateMachine-HSCswl9XhNPV
    {
        "executionArn": "arn:aws:states:us-east-1:270747450568:execution:OrgMigrationStateMachine-dqTsdp1lJa8g:64995607-ebf6-4f4f-b137-7b9bb854f681",
        "startDate": "2021-01-25T22:08:05.824000+00:00"
    }
```
## Use the SAM CLI to build locally

Build the Lambda functions in your application with the `sam build --use-container` command.

```bash
sam build --use-container
```

The SAM CLI installs dependencies defined in `functions/*/requirements.txt`, creates a deployment package, and saves it in the `.aws-sam/build` folder.

## Test Lambda functions locally using SAM CLI

You can test the AWS Lambda functions of the application locally with the included scripts
    
    Update the file tests/testAll.json with the appropriate values for ROLE_NAME, OLD_ORG_MA, OU_TABLE_NAME, ACCOUNT_TABLE_NAME, ACCEPT_ROLE_NAME, and OLD_MASTER_OU.

        {
            "scanOldOrg": {
                "ROLE_NAME": "arn:aws:iam::111122223333:role/OrgInfoRole",
                "OLD_ORG_MA": "111122223333",
                "OU_TABLE_NAME": "OrgMigration-OldOrgOuInfoTable-XXXXYYYYZZZZZ",
                "ACCOUNT_TABLE_NAME": "OrgMigration-OldOrgAccountInfoTable-XXXXYYYYZZZZZ"
            },
            "replicateOuStructure": {
                "ROLE_NAME": "arn:aws:iam::111122223333:role/OrgInfoRole",
                "OU_TABLE_NAME": "OrgMigration-OldOrgOuInfoTable-XXXXYYYYZZZZZ",
                "OLD_MASTER_OU": "OldMasterOU"
            },
            "inviteAccounts": {
                "OLD_ORG_MA": "111122223333",
                "ACCOUNT_TABLE_NAME": "OrgMigration-OldOrgAccountInfoTable-XXXXYYYYZZZZZ"
            },
            "acceptInvitation": {
                "OU_TABLE_NAME": "OrgMigration-OldOrgOuInfoTable-1DLH8H3CLQH6Z",
                "ACCOUNT_TABLE_NAME": "OrgMigration-OldOrgAccountInfoTable-8R0FUR3H8YG",
                "ACCEPT_ROLE_NAME": "NewOrgAcceptHandshakeRole"
            },
            "moveMaster": {
                "ROLE_NAME": "arn:aws:iam::111122223333:role/OrgInfoRole",
                "OLD_ORG_MA": "111122223333",
                "OU_TABLE_NAME": "OrgMigration-OldOrgOuInfoTable-XXXXYYYYZZZZZ",
                "ACCOUNT_TABLE_NAME": "OrgMigration-OldOrgAccountInfoTable-XXXXYYYYZZZZZ",
                "ACCEPT_ROLE_NAME": "NewOrgAcceptHandshakeRole",
                "OLD_MASTER_OU": "OldMasterOU"
            }  
        }
    
    Run the following command with the appropriate parameters:
    ```
    `sam local invoke [LambdaFunctionName] --env-vars tests/testAll.json --profile $1 --parameter-overrides "ParameterKey=OldOrgScanRole,ParameterValue=arn:aws:iam::111122223333:role/OrgInfoRole"`

    `sam local invoke scanOldOrg --env-vars tests/testAll.json --profile $1 --parameter-overrides "ParameterKey=OldOrgScanRole,ParameterValue=arn:aws:iam::111122223333:role/OrgInfoRole"`
    ```

    **`NOTE`**: Update account number accordingly.

    Refer to test[LambdaFunctionName].sh for testing each Lambda function separately.

## Add a resource to your application
The application template uses AWS Serverless Application Model (AWS SAM) to define application resources. AWS SAM is an extension of AWS CloudFormation with a simpler syntax for configuring common serverless application resources such as functions, triggers, and APIs. For resources not included in [the SAM specification](https://github.com/awslabs/serverless-application-model/blob/master/versions/2016-10-31.md), you can use standard [AWS CloudFormation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-template-resource-type-ref.html) resource types.

## Fetch, tail, and filter Lambda function logs

To simplify troubleshooting, SAM CLI has a command called `sam logs`. `sam logs` lets you fetch logs generated by your deployed Lambda function from the command line. In addition to printing the logs on the terminal, this command has several nifty features to help you quickly find the bug.

**`NOTE`**: This command works for all AWS Lambda functions; not just the ones you deploy using SAM.

```bash
sam logs -n acceptInvitation --stack-name OrgMigration --tail
```

You can find more information and examples about filtering Lambda function logs in the [SAM CLI Documentation](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-logging.html).

## Cleanup

To delete the sample application that you created, use the AWS CLI. Assuming you used your project name for the stack name, you can run the following:

```bash
aws cloudformation delete-stack --stack-name OrgMigration
```

## Resources

See the [AWS SAM developer guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html) for an introduction to SAM specification, the SAM CLI, and serverless application concepts.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This project is licensed under the Apache-2.0 License.