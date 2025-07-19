resource "aws_s3_bucket" "raw_events_archive" {
  bucket = "ecom-propensity-raw-events-archive"

  tags = {
    Project = "EcomPropensity"
  }
}

resource "aws_s3_bucket" "lambda_code_bucket" {
  bucket = "ecom-propensity-lambda-code-artifacts"
  
  tags = {
    Project = "EcomPropensity"
  }
}