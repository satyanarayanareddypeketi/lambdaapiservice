output "api_url" {
  description = "Task API endpoint URL"
  value       = aws_apigatewayv2_stage.default.invoke_url
}

output "lambda_name" {
  description = "Lambda function name"
  value       = aws_myfirstlambdaapi.task_api.function_name
}

output "dynamodb_table" {
  description = "DynamoDB table name"
  value       = aws_dynamodb_table.tasks.name
}
