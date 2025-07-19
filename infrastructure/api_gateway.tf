# IAM Role for API Gateway to write to Kinesis
resource "aws_iam_role" "api_gateway_kinesis_role" {
  name = "api-gateway-kinesis-role"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [{
      Action    = "sts:AssumeRole",
      Effect    = "Allow",
      Principal = { Service = "apigateway.amazonaws.com" },
    }],
  })
}

resource "aws_iam_role_policy" "api_gateway_kinesis_policy" {
  name = "api-gateway-kinesis-policy"
  role = aws_iam_role.api_gateway_kinesis_role.id
  policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [{
      Action   = ["kinesis:PutRecord", "kinesis:PutRecords"],
      Effect   = "Allow",
      Resource = aws_kinesis_stream.raw_events.arn,
    }],
  })
}

# API Gateway v2 (HTTP API)
resource "aws_apigatewayv2_api" "event_api" {
  name          = "ecom-event-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "kinesis_integration" {
  api_id           = aws_apigatewayv2_api.event_api.id
  integration_type = "AWS_PROXY"
  integration_subtype = "Kinesis-PutRecord"
  credentials_arn    = aws_iam_role.api_gateway_kinesis_role.arn
  request_parameters = {
    "StreamName"   = aws_kinesis_stream.raw_events.name
    "Data"         = "$request.body"
    "PartitionKey" = "$context.requestId"
  }
}

resource "aws_apigatewayv2_route" "post_events" {
  api_id    = aws_apigatewayv2_api.event_api.id
  route_key = "POST /events"
  target    = "integrations/${aws_apigatewayv2_integration.kinesis_integration.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.event_api.id
  name        = "$default"
  auto_deploy = true
}