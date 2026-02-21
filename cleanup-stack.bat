@echo off
:: AWS Crypto & Forex Trading System - Cleanup Script
:: This script removes all deployed AWS resources

setlocal enabledelayedexpansion

echo 🧹 AWS Crypto ^& Forex Trading System - Cleanup
echo ==================================================

:: Configuration
set STACK_NAME=crypto-forex-trading-system
set S3_BUCKET=forex-ai-models
set AWS_REGION=us-east-1

echo ⚠ WARNING: This will delete ALL deployed resources including:
echo   - CloudFormation stack: %STACK_NAME%
echo   - S3 bucket: %S3_BUCKET%
echo   - S3 bucket: %S3_BUCKET%-dashboard
echo   - All Lambda functions, DynamoDB tables, and CloudWatch logs
echo   - ALL TRADING DATA AND AI MODELS WILL BE LOST!
echo.

set /p CONFIRM="Are you sure you want to continue? (yes/no): "
if /i not "%CONFIRM%"=="yes" (
    echo Cleanup cancelled.
    pause
    exit /b 0
)

echo.
echo Starting cleanup process...

:: Check if AWS CLI is configured
aws sts get-caller-identity >nul 2>&1
if errorlevel 1 (
    echo ✗ AWS CLI is not configured. Please run 'aws configure' first.
    pause
    exit /b 1
)
echo ✓ AWS CLI is configured

:: Empty and delete S3 buckets first (required before stack deletion)
echo.
echo Cleaning up S3 buckets...

:: Empty main bucket
echo Emptying S3 bucket: %S3_BUCKET%
aws s3 rm s3://%S3_BUCKET% --recursive >nul 2>&1
if not errorlevel 1 (
    echo ✓ Emptied S3 bucket: %S3_BUCKET%
)

:: Delete main bucket
aws s3 rb s3://%S3_BUCKET% >nul 2>&1
if not errorlevel 1 (
    echo ✓ Deleted S3 bucket: %S3_BUCKET%
) else (
    echo ⚠ Could not delete S3 bucket: %S3_BUCKET% (may not exist)
)

:: Empty and delete dashboard bucket
set DASHBOARD_BUCKET=%S3_BUCKET%-dashboard
echo Emptying S3 bucket: %DASHBOARD_BUCKET%
aws s3 rm s3://%DASHBOARD_BUCKET% --recursive >nul 2>&1
if not errorlevel 1 (
    echo ✓ Emptied S3 bucket: %DASHBOARD_BUCKET%
)

aws s3 rb s3://%DASHBOARD_BUCKET% >nul 2>&1
if not errorlevel 1 (
    echo ✓ Deleted S3 bucket: %DASHBOARD_BUCKET%
) else (
    echo ⚠ Could not delete S3 bucket: %DASHBOARD_BUCKET% (may not exist)
)

:: Delete CloudFormation stack
echo.
echo Deleting CloudFormation stack: %STACK_NAME%
aws cloudformation delete-stack --stack-name %STACK_NAME% --region %AWS_REGION%
if errorlevel 1 (
    echo ⚠ Could not initiate stack deletion (may not exist)
) else (
    echo ✓ Stack deletion initiated...
    echo   Waiting for stack deletion to complete (this may take several minutes)...
    
    :: Wait for stack deletion to complete
    aws cloudformation wait stack-delete-complete --stack-name %STACK_NAME% --region %AWS_REGION%
    if errorlevel 1 (
        echo ⚠ Stack deletion may have failed or timed out
        echo   Check AWS Console for stack status
    ) else (
        echo ✓ CloudFormation stack deleted successfully
    )
)

:: Clean up local artifacts
echo.
echo Cleaning up local artifacts...

if exist "stack-outputs.json" (
    del stack-outputs.json
    echo ✓ Removed stack-outputs.json
)

if exist "dashboard-url.txt" (
    del dashboard-url.txt
    echo ✓ Removed dashboard-url.txt
)

if exist "aws-java-lambdas\target" (
    rmdir /s /q aws-java-lambdas\target
    echo ✓ Removed Java build artifacts
)

if exist "aws-infrastructure\lambda-packages" (
    rmdir /s /q aws-infrastructure\lambda-packages
    echo ✓ Removed Python Lambda packages
)

if exist "aws-infrastructure\.aws-sam" (
    rmdir /s /q aws-infrastructure\.aws-sam
    echo ✓ Removed SAM build artifacts
)

:: Clean up CloudWatch logs (optional)
echo.
set /p CLEAN_LOGS="Do you want to delete CloudWatch logs? (yes/no): "
if /i "%CLEAN_LOGS%"=="yes" (
    echo Deleting CloudWatch log groups...
    
    :: Get all log groups for our stack
    for /f "tokens=*" %%g in ('aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/crypto-forex" --query "logGroups[].logGroupName" --output text --region %AWS_REGION% 2^>nul') do (
        aws logs delete-log-group --log-group-name %%g --region %AWS_REGION% >nul 2>&1
        echo ✓ Deleted log group: %%g
    )
    
    :: Also try to delete Step Functions logs
    aws logs delete-log-group --log-group-name "/aws/stepfunctions/TradingWorkflow" --region %AWS_REGION% >nul 2>&1
    echo ✓ Deleted Step Functions log group
)

:: Completion message
echo.
echo ==================================================
echo 🎉 Cleanup completed successfully!
echo ==================================================
echo.
echo The following resources have been removed:
echo ✓ CloudFormation stack and all AWS resources
echo ✓ S3 buckets and stored data
echo ✓ Local build artifacts
if /i "%CLEAN_LOGS%"=="yes" (
    echo ✓ CloudWatch log groups
)
echo.
echo Your AWS account is now clean of this trading system.
echo To redeploy, run: deploy-stack.bat
echo.
pause