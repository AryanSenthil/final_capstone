# AWS Deployment Guide

This guide covers deploying your capstone project to AWS with user-provided API keys.

## Architecture Overview

- **Backend**: FastAPI on port 8000
- **Frontend**: Express + Vite on port 5000
- **API Keys**: Users provide their own OpenAI API key via the Settings dialog
- **Data Persistence**: CSV-based storage (no database required)

## Prerequisites

1. AWS account with appropriate permissions
2. Docker installed locally
3. AWS CLI configured
4. Domain name (optional, but recommended)

## Deployment Options

### Option 1: AWS ECS (Elastic Container Service) - Recommended

Best for production workloads with automatic scaling.

#### Steps:

1. **Build and push Docker images to ECR**:
```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <your-account-id>.dkr.ecr.us-east-1.amazonaws.com

# Create ECR repositories
aws ecr create-repository --repository-name capstone-backend
aws ecr create-repository --repository-name capstone-frontend

# Build and tag images
docker-compose build
docker tag capstone-backend:latest <your-account-id>.dkr.ecr.us-east-1.amazonaws.com/capstone-backend:latest
docker tag capstone-frontend:latest <your-account-id>.dkr.ecr.us-east-1.amazonaws.com/capstone-frontend:latest

# Push to ECR
docker push <your-account-id>.dkr.ecr.us-east-1.amazonaws.com/capstone-backend:latest
docker push <your-account-id>.dkr.ecr.us-east-1.amazonaws.com/capstone-frontend:latest
```

2. **Create ECS Task Definition** with volumes for data persistence:
   - Backend: Map EFS volumes to `/app/database`, `/app/models`, `/app/.env`
   - Frontend: Map to backend via service discovery

3. **Create ECS Service** with Application Load Balancer
   - Route `/api/*` to backend
   - Route `/*` to frontend

4. **Setup EFS (Elastic File System)** for data persistence:
   - Database files
   - Trained models
   - `.env` file (for API key storage)

### Option 2: AWS EC2 with Docker Compose

Simpler setup, good for smaller deployments.

#### Steps:

1. **Launch EC2 instance**:
   - AMI: Amazon Linux 2 or Ubuntu
   - Instance type: t3.medium or larger (for model training)
   - Security groups: Open ports 80, 443, 5000, 8000
   - Storage: 30GB+ EBS volume
   - **Note**: SSH key is stored in `~/.ssh/capstone-key.pem` (never commit to git)

2. **Install Docker and Docker Compose**:
```bash
# For Amazon Linux 2
sudo yum update -y
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ec2-user

# Install docker-compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

3. **Clone repository and deploy**:
```bash
git clone <your-repo-url>
cd final_capstone
docker-compose up -d
```

4. **Setup reverse proxy with Nginx** (optional):
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Option 3: AWS Lightsail

Easiest option for small projects with fixed pricing.

1. Create Lightsail container service
2. Push images to Lightsail
3. Configure service with 2 containers (backend + frontend)
4. Attach persistent storage

## User API Key Configuration

After deployment, users will configure their OpenAI API key via the frontend:

1. Navigate to **Settings** (gear icon in the UI)
2. Click **OpenAI API Key Configuration**
3. Paste their API key from [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
4. Click **Save API Key**

The key is:
- Stored in `/app/.env` on the backend container
- Persisted via volume mount (won't be lost on restart)
- Never transmitted in logs or exposed to other users
- Masked in the UI (shows `sk-proj...****`)

## Alternative: AWS Secrets Manager (More Secure)

For production, consider storing API keys in AWS Secrets Manager:

1. **Create secret in AWS Secrets Manager**:
```bash
aws secretsmanager create-secret \
  --name capstone/openai-api-key \
  --secret-string '{"api_key":"user-api-key"}'
```

2. **Grant ECS task IAM role permission** to read the secret

3. **Modify backend code** to read from Secrets Manager:
```python
import boto3
client = boto3.client('secretsmanager')
secret = client.get_secret_value(SecretId='capstone/openai-api-key')
api_key = json.loads(secret['SecretString'])['api_key']
```

## Environment Variables

For AWS deployment, set these in your task definition or EC2 environment:

```bash
# Backend
PYTHONUNBUFFERED=1

# Frontend
NODE_ENV=production
PORT=5000
BACKEND_URL=http://backend:8000  # For ECS service discovery
# OR
BACKEND_URL=http://localhost:8000  # For EC2 same-host deployment
```

## Data Persistence Strategy

The application uses file-based storage:

- **Database**: CSV files in `/app/database`
- **Models**: Trained ML models in `/app/models`
- **Raw data**: Input files in `/app/raw_database`
- **Config**: `.env` file in `/app`

**For ECS**: Use EFS volumes mounted to these paths
**For EC2**: Docker volumes already configured in docker-compose.yml

## Health Checks

Both containers have built-in health checks:

- **Backend**: `http://localhost:8000/api/labels`
- **Frontend**: `http://localhost:5000`

Configure ALB/ELB to use these endpoints.

## Cost Estimates (Monthly)

### EC2 Option:
- t3.medium instance: ~$30
- 30GB EBS: ~$3
- Data transfer: ~$10
- **Total: ~$43/month**

### ECS Fargate Option:
- 1 vCPU, 2GB RAM: ~$15-20
- EFS storage (5GB): ~$1.50
- ALB: ~$16
- **Total: ~$33-38/month**

### Lightsail Option:
- Container service (2GB RAM): ~$40/month
- **Total: ~$40/month**

## Security Checklist

- [ ] HTTPS enabled (use AWS Certificate Manager)
- [ ] API keys stored securely (not in docker-compose.yml)
- [ ] Security groups restrict access to necessary ports only
- [ ] Regular backups of data volumes
- [ ] CloudWatch logging enabled
- [ ] IAM roles follow least-privilege principle

## Monitoring

Setup CloudWatch alarms for:
- CPU/Memory usage > 80%
- Container restart count
- Health check failures
- Disk space usage

## Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs backend
docker-compose logs frontend

# Or for ECS
aws ecs describe-tasks --cluster <cluster> --tasks <task-id>
```

### API key not persisting
- Verify `.env` file is mounted as volume
- Check file permissions in container
- Ensure EFS mount point is correct (for ECS)

### Models not loading
- Check `/app/models` directory permissions
- Verify volume mount is configured
- Ensure sufficient disk space

## Support

For issues specific to:
- **Docker**: Check docker-compose.yml and Dockerfiles
- **AWS**: Review CloudFormation/ECS logs
- **API Key**: Check Settings API at `/api/settings/api-key`
