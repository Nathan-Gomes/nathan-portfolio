# Deploying the Connector to AWS Lambda (essentially free)

This deploys the MCP server as an AWS Lambda function with a public
Function URL -- no EC2, no API Gateway, no custom domain needed for v1.
Chosen specifically because Lambda's "Always Free" tier (1M requests +
400,000 GB-seconds of compute per month) never expires, regardless of
when your AWS account was created -- unlike EC2/Lightsail free tiers,
which depend on account age. For one person occasionally asking Claude
questions, this will cost $0/month.

## What you need first

- AWS CLI installed and configured (`aws configure`) with credentials that
  can create ECR repos, Lambda functions, and IAM roles.
- Docker installed and running locally (used only to build the image --
  it still deploys to Lambda, not to a container host).

## 0. One-time variables

```bash
export AWS_REGION=us-east-1          # or your preferred region
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export REPO_NAME=portfolio-intelligence-mcp
export FUNCTION_NAME=portfolio-intelligence-mcp
```

## 1. Create an ECR repository and push the image

```bash
aws ecr create-repository --repository-name $REPO_NAME --region $AWS_REGION

aws ecr get-login-password --region $AWS_REGION \
  | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# From the portfolio-intel/ project root (so the Dockerfile's relative
# COPY paths like server/... and db/... resolve correctly):
docker build -t $REPO_NAME -f deploy/Dockerfile .

docker tag $REPO_NAME:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:latest
```

## 2. Create the IAM execution role (one-time)

```bash
aws iam create-role \
  --role-name portfolio-intelligence-lambda-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}]
  }'

aws iam attach-role-policy \
  --role-name portfolio-intelligence-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

Wait ~10 seconds after creating the role before using it below (IAM takes a moment to propagate).

## 3. Create the Lambda function

```bash
aws lambda create-function \
  --function-name $FUNCTION_NAME \
  --package-type Image \
  --code ImageUri=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:latest \
  --role arn:aws:iam::$AWS_ACCOUNT_ID:role/portfolio-intelligence-lambda-role \
  --timeout 15 \
  --memory-size 512 \
  --region $AWS_REGION
```

## 4. Create a public Function URL

```bash
aws lambda create-function-url-config \
  --function-name $FUNCTION_NAME \
  --auth-type NONE \
  --region $AWS_REGION
```

This returns a `FunctionUrl` like:
`https://abc123xyz.lambda-url.us-east-1.on.aws/`

Copy that hostname (the part between `https://` and the next `/`).

Also allow public invocation (required alongside auth-type NONE):

```bash
aws lambda add-permission \
  --function-name $FUNCTION_NAME \
  --statement-id FunctionURLAllowPublicAccess \
  --action lambda:InvokeFunctionUrl \
  --principal "*" \
  --function-url-auth-type NONE \
  --region $AWS_REGION
```

## 5. Configure environment variables (required, not optional)

The handler rejects requests from hosts it doesn't recognize (DNS-rebinding
protection) -- so it needs to know its own Function URL hostname. Also set
a shared secret so random internet traffic can't call your tools.

```bash
# Generate a secret once and save it somewhere safe -- you'll need to give
# this same value to Claude when registering the connector.
export MCP_SECRET=$(openssl rand -hex 24)
echo "Save this secret: $MCP_SECRET"

aws lambda update-function-configuration \
  --function-name $FUNCTION_NAME \
  --environment "Variables={MCP_ALLOWED_HOSTS=abc123xyz.lambda-url.us-east-1.on.aws,MCP_SHARED_SECRET=$MCP_SECRET}" \
  --region $AWS_REGION
```

Replace `abc123xyz.lambda-url.us-east-1.on.aws` with your actual Function URL host from step 4.

## 6. Test it

```bash
curl -s https://abc123xyz.lambda-url.us-east-1.on.aws/ \
  -H "Content-Type: application/json" \
  -H "x-mcp-secret: $MCP_SECRET" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | python3 -m json.tool
```

You should see all 8 tools listed. If you get a 421, double-check
`MCP_ALLOWED_HOSTS` matches your Function URL host exactly (no `https://`,
no trailing slash). If you get a 403, double-check `x-mcp-secret` matches
`MCP_SHARED_SECRET`.

## Updating the code later

Whenever you change `server/*.py`, rebuild and push a new image, then tell
Lambda to use it:

```bash
docker build -t $REPO_NAME -f deploy/Dockerfile .
docker tag $REPO_NAME:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:latest

aws lambda update-function-code \
  --function-name $FUNCTION_NAME \
  --image-uri $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:latest \
  --region $AWS_REGION
```

## What this does NOT include (kept out on purpose, to stay free/simple)

- **Custom domain** (`mcp.nathan-gomes.com`) -- the raw Function URL works
  fine for registering a Claude connector. Adding a custom domain needs
  CloudFront + ACM + Route 53 in front, which is more moving parts for
  zero functional benefit at this stage. Revisit later if you want it.
- **Updating the sample data** -- the database is baked into the image at
  build time (read-only at runtime). To change it, edit `db/seed_data.py`
  locally, run it, then rebuild/push the image as above.
- **Persistent audit log across cold starts** -- audit entries write to
  `/tmp`, which Lambda wipes on a cold start. Fine for a personal pilot;
  swap in DynamoDB later if you want it to persist.

## Cost reality check

Lambda's Always Free tier: 1,000,000 requests/month and 400,000 GB-seconds
of compute/month, forever, no expiry. At 512MB memory and sub-second
executions, you'd need roughly 750,000+ invocations in a month before
compute charges even start -- for one person occasionally asking Claude
about a property, this stays at $0. ECR storage has a small always-free
allowance too (500MB); this image is well under that.
