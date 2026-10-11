# HazardIQ - AWS Services Deployment Guide

This guide walks you through deploying the **HazardIQ** backend onto AWS services using **AWS App Runner**, **Amazon DynamoDB**, **Amazon S3**, and **Amazon Bedrock**.

---

## 1. Architecture on AWS

- **Application Compute:** AWS App Runner (fully-managed HTTPS container runtime with autoscaling).
- **Hazard Photos:** Amazon S3 (`hazardiq-hazard-photos-...`) with private ACLs and server-side `AES256` encryption.
- **Report Database:** Amazon DynamoDB (`HazardIQ-Reports`) with On-Demand (PAY_PER_REQUEST) capacity.
- **Multimodal AI Vision:** Amazon Bedrock with **Amazon Nova Lite** (`amazon.nova-lite-v1:0`) or Claude 3 Haiku (`anthropic.claude-3-haiku-20240307-v1:0`).
- **Security & IAM:** Least-privilege IAM Instance Role (no hardcoded credentials).

---

## 2. Step 1: Deploy Infrastructure with AWS CloudFormation

Run the following command in your PowerShell terminal using the AWS CLI:

```powershell
aws cloudformation deploy `
  --template-file aws/cloudformation.yaml `
  --stack-name HazardIQ-Infrastructure `
  --capabilities CAPABILITY_NAMED_IAM `
  --parameter-overrides Environment=production
```

This stack automatically provisions:
1. DynamoDB table: `HazardIQ-Reports`
2. Private S3 bucket: `hazardiq-hazard-photos-<account-id>-<region>`
3. IAM Instance Role: `HazardIQ-AppRunner-InstanceRole-production`

### Retrieve Created Resource Names:
```powershell
aws cloudformation describe-stacks `
  --stack-name HazardIQ-Infrastructure `
  --query "Stacks[0].Outputs" `
  --output table
```

---

## 3. Step 2: Enable Amazon Bedrock Model Access

1. Open the [AWS Bedrock Console](https://console.aws.amazon.com/bedrock/).
2. In the left navigation, choose **Model access**.
3. Click **Modify model access**.
4. Check **Amazon Nova Lite** (`amazon.nova-lite-v1:0`) or **Claude 3 Haiku**.
5. Save changes and confirm status is **Access granted**.

---

## 4. Step 3: Build & Push Container to Amazon ECR

### 1. Authenticate Docker with Amazon ECR:
```powershell
$AWS_ACCOUNT_ID = (aws sts get-caller-identity --query Account --output text)
$AWS_REGION = "us-east-1"
$ECR_REPO = "hazardiq-backend"

# Create repository if not already created
aws ecr create-repository --repository-name $ECR_REPO --region $AWS_REGION

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
```

### 2. Build and Tag Docker Image:
```powershell
docker build -t "$ECR_REPO`:latest" .
docker tag "$ECR_REPO`:latest" "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO`:latest"
```

### 3. Push Image to ECR:
```powershell
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO`:latest"
```

---

## 5. Step 4: Create AWS App Runner Service

### Option A: Via AWS Console (Recommended for First Time)
1. Navigate to **AWS App Runner** in the AWS Console.
2. Click **Create service**.
3. **Source:** Select **Container registry** -> **Amazon ECR** -> Choose image `hazardiq-backend:latest`.
4. **Deployment trigger:** Choose **Automatic** or **Manual**.
5. **ECR access role:** Select default or create new App Runner ECR access role.
6. **Service settings:**
   - **Service name:** `hazardiq-backend`
   - **vCPU & Memory:** `1 vCPU`, `2 GB`
   - **Port:** `8000`
7. **Environment variables:**
   | Key | Value |
   | :--- | :--- |
   | `ENVIRONMENT` | `production` |
   | `ENABLE_DYNAMODB` | `true` |
   | `DYNAMODB_TABLE_REPORTS` | `HazardIQ-Reports` |
   | `ENABLE_S3` | `true` |
   | `S3_BUCKET_PHOTOS` | `hazardiq-hazard-photos-<account-id>-<region>` |
   | `ENABLE_BEDROCK` | `true` |
   | `BEDROCK_MODEL_ID` | `amazon.nova-lite-v1:0` |
   | `AWS_REGION` | `us-east-1` |
   | `ALLOWED_ORIGINS` | `https://main.d123456abcdef.amplifyapp.com` (Your frontend URL) |
8. **Security -> Instance Role:**
   - Select `HazardIQ-AppRunner-InstanceRole-production` (created in Step 1).
9. **Health check:**
   - Protocol: `HTTP`
   - Path: `/health`
   - Interval: `10`
   - Timeout: `5`
   - Healthy threshold: `1`
   - Unhealthy threshold: `5`
10. Click **Create & deploy**.

---

## 6. Step 5: Verification & Testing in Production

Once App Runner displays status **Running**:

### 1. Test Service Health Check:
```powershell
curl https://<your-apprunner-domain>.awsapprunner.com/health
```

Expected Response:
```json
{
  "status": "ok",
  "app_name": "HazardIQ Backend",
  "version": "0.1.0",
  "environment": "production",
  "services": {
    "weather_service": "online (Open-Meteo, cache=300s)",
    "storage_backend": "DynamoDB (active)",
    "bedrock_vision": "enabled (model=amazon.nova-lite-v1:0)",
    "s3_photo_storage": "enabled (hazardiq-hazard-photos-...)",
    "policy_engine": "cedar_spec_v1 (deterministic_python_evaluator)"
  }
}
```

### 2. Test Hotspots Listing:
```powershell
curl https://<your-apprunner-domain>.awsapprunner.com/api/hotspots
```

### 3. Interactive API Documentation:
Visit `https://<your-apprunner-domain>.awsapprunner.com/docs` in your browser.
