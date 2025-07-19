# Raw events stream, directly from API Gateway
resource "aws_kinesis_stream" "raw_events" {
  name             = "raw-events-stream"
  shard_count      = 2
  retention_period = 24

  tags = {
    Project = "EcomPropensity"
  }
}

# Processed events stream, output from the Lambda function
resource "aws_kinesis_stream" "processed_events" {
  name             = "processed-events-stream"
  shard_count      = 2
  retention_period = 48

  tags = {
    Project = "EcomPropensity"
  }
}

# Kinesis Firehose for archiving raw events to S3
resource "aws_kinesis_firehose_delivery_stream" "raw_archive_stream" {
  name        = "raw-events-archive-stream"
  destination = "extended_s3"

  extended_s3_configuration {
    role_arn   = aws_iam_role.firehose_role.arn
    bucket_arn = aws_s3_bucket.raw_events_archive.arn
    prefix     = "raw-events/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/hour=!{timestamp:HH}/"
    error_output_prefix = "raw-events-errors/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/hour=!{timestamp:HH}/!{firehose:error-output-type}"
    
    # Buffer hints for creating fewer, larger files in S3
    buffer_size           = 128 # MB
    buffer_interval       = 300 # seconds
    compression_format    = "GZIP"
  }
}