provider "aws" {
  region = "us-east-1"  # Change to your desired region
}

# Create IAM role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "stock_analyzer_lambda_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# Attach basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "lambda_basic_policy" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.lambda_role.name
}

# Create ZIP file containing Lambda function code
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_function"
  output_path = "${path.module}/lambda_function.zip"
}

# Create Lambda function
resource "aws_lambda_function" "stock_analyzer" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "stock_analyzer"
  role            = aws_iam_role.lambda_role.arn
  handler         = "main.lambda_handler"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  runtime         = "python3.9"
  timeout         = 900
  memory_size     = 512

  environment {
    variables = {
      PYTHONPATH = "/var/task"
    }
  }
}

# Create API Gateway REST API
resource "aws_api_gateway_rest_api" "stock_analyzer_api" {
  name = "stock_analyzer_api"
}

# Create API Gateway resource
resource "aws_api_gateway_resource" "stock_analyzer_resource" {
  rest_api_id = aws_api_gateway_rest_api.stock_analyzer_api.id
  parent_id   = aws_api_gateway_rest_api.stock_analyzer_api.root_resource_id
  path_part   = "summarize"
}

# Create API Gateway method
resource "aws_api_gateway_method" "stock_analyzer_method" {
  rest_api_id   = aws_api_gateway_rest_api.stock_analyzer_api.id
  resource_id   = aws_api_gateway_resource.stock_analyzer_resource.id
  http_method   = "POST"
  authorization = "NONE"
}

# Create API Gateway integration
resource "aws_api_gateway_integration" "lambda_integration" {
  rest_api_id = aws_api_gateway_rest_api.stock_analyzer_api.id
  resource_id = aws_api_gateway_resource.stock_analyzer_resource.id
  http_method = aws_api_gateway_method.stock_analyzer_method.http_method
  type        = "AWS_PROXY"
  integration_http_method = "POST"
  uri         = aws_lambda_function.stock_analyzer.invoke_arn
}

# Deploy API Gateway
resource "aws_api_gateway_deployment" "stock_analyzer_deployment" {
  rest_api_id = aws_api_gateway_rest_api.stock_analyzer_api.id
  depends_on  = [aws_api_gateway_integration.lambda_integration]
}

# Create API Gateway stage
resource "aws_api_gateway_stage" "stock_analyzer_stage" {
  deployment_id = aws_api_gateway_deployment.stock_analyzer_deployment.id
  rest_api_id   = aws_api_gateway_rest_api.stock_analyzer_api.id
  stage_name    = "prod"
}

# Allow API Gateway to invoke Lambda
resource "aws_lambda_permission" "api_gateway_permission" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.stock_analyzer.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.stock_analyzer_api.execution_arn}/*/*"
}

# Output the API Gateway URL
output "api_gateway_url" {
  value = "${aws_api_gateway_stage.stock_analyzer_stage.invoke_url}/summarize"
}
