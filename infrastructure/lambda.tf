data "archive_file" "ingestion_lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src/data_ingestion/"
  output_path = "${path.module}/../dist/data_ingestion.zip"
}

resource "aws_lambda_function" "ingestion_processor" {
  function_name = "ecom-ingestion-processor"
  role          = aws_iam_role.lambda_exec_role.arn

  filename         = data_archive_file.ingestion_lambda_zip.output_path
  source_code_hash = data_archive_file.ingestion_lambda_zip.output_base64sha256

  handler = "app.lambda_handler"
  runtime = "python3.9"
  timeout = 60
  memory_size = 256
}

resource "aws_lambda_event_source_mapping" "ingestion_trigger" {
  event_source_arn  = aws_kinesis_stream.raw_events.arn
  function_name     = aws_lambda_function.ingestion_processor.arn
  starting_position = "LATEST"
  batch_size        = 100
}