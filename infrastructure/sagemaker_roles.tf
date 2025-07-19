# IAM Role that SageMaker Training Jobs will assume
resource "aws_iam_role" "sagemaker_training_role" {
  name = "sagemaker-training-execution-role"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [{
      Action    = "sts:AssumeRole",
      Effect    = "Allow",
      Principal = { Service = "sagemaker.amazonaws.com" },
    }],
  })
}

# Policy allowing access to S3, ECR, and CloudWatch Logs
resource "aws_iam_policy" "sagemaker_training_policy" {
  name = "sagemaker-training-policy"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
        Resource = ["arn:aws:s3:::ecom-propensity-*", "arn:aws:s3:::ecom-propensity-*/*"],
      },
      {
        Effect   = "Allow",
        Action   = ["ecr:GetAuthorizationToken", "ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"],
        Resource = "*",
      },
      {
        Effect   = "Allow",
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
        Resource = "arn:aws:logs:*:*:*",
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "sagemaker_training_attach" {
  role       = aws_iam_role.sagemaker_training_role.name
  policy_arn = aws_iam_policy.sagemaker_training_policy.arn
}

# Define an ECR repository to store our training container
resource "aws_ecr_repository" "training_repo" {
  name = "ecom-propensity/training"
}