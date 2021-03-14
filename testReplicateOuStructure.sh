sam local invoke replicateOuStructure --env-vars tests/testAll.json --profile $1 --parameter-overrides "ParameterKey=OldOrgScanRole,ParameterValue=arn:aws:iam::111122223333:role/OrgInfoRole"
