# Lambda container image for the portfolio-intelligence MCP connector.
# Base image matches Lambda's actual runtime so native wheels (rpds-py,
# pydantic-core, etc. pulled in by the mcp package) are guaranteed compatible.
FROM public.ecr.aws/lambda/python:3.12

# --- Dependencies ---
COPY deploy/requirements-lambda.txt ${LAMBDA_TASK_ROOT}/requirements.txt
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

# --- Application code (kept as server/ + db/, matching local dev layout,
# since business_logic.py resolves the database path relative to its own
# folder -- flattening these would break that path resolution) ---
COPY server/business_logic.py ${LAMBDA_TASK_ROOT}/server/business_logic.py
COPY server/mcp_server.py ${LAMBDA_TASK_ROOT}/server/mcp_server.py
COPY server/lambda_handler.py ${LAMBDA_TASK_ROOT}/server/lambda_handler.py
COPY db/portfolio.db ${LAMBDA_TASK_ROOT}/db/portfolio.db

CMD ["server.lambda_handler.handler"]
