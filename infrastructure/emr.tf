# ------------------------------------------------------------------
# ROLES AND PROFILES FOR ALL EMR CLUSTERS (Batch & Streaming)
# These foundational components are defined once and used by both provisioning methods.
# ------------------------------------------------------------------

resource "aws_iam_role" "emr_service_role" {
  name = "emr_service_role"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [{ Action = "sts:AssumeRole", Effect = "Allow", Principal = { Service = "elasticmapreduce.amazonaws.com" } }],
  })
}
# Attach AWS managed policy for EMR service role
resource "aws_iam_role_policy_attachment" "emr_service_policy_attach" {
  role       = aws_iam_role.emr_service_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceRole"
}

resource "aws_iam_role" "emr_ec2_role" {
  name = "emr_ec2_instance_role"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [{ Action = "sts:AssumeRole", Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" } }],
  })
}
# Attach AWS managed policy for EMR EC2 role
resource "aws_iam_role_policy_attachment" "emr_ec2_policy_attach" {
  role       = aws_iam_role.emr_ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceforEC2Role"
}

# This instance profile is used by the EC2 instances in BOTH clusters
resource "aws_iam_instance_profile" "emr_instance_profile" {
  name = "emr_ec2_instance_profile"
  role = aws_iam_role.emr_ec2_role.name
}

# ------------------------------------------------------------------
# PERSISTENT STREAMING CLUSTER (Managed by Terraform)
# This is the long-running cluster for our 24/7 real-time feature pipeline.
# ------------------------------------------------------------------

resource "aws_emr_cluster" "streaming_cluster" {
  name          = "ecom-propensity-streaming-cluster"
  release_label = "emr-6.9.0"
  applications  = ["Spark"]

  # This cluster is kept alive
  keep_job_flow_alive_when_no_steps = true
  termination_protection            = true

  ec2_attributes {
    instance_profile = aws_iam_instance_profile.emr_instance_profile.arn
    # Additional networking configurations (subnet_id, security_groups) go here
  }

  master_instance_group {
    instance_type  = "m5.xlarge"
    instance_count = 1
  }

  core_instance_group {
    instance_type  = "m5.xlarge"
    instance_count = 2 # Start with 2 and autoscale
    # Autoscaling configurations would be defined here
  }

  # The service and job flow roles defined above are used here
  service_role = aws_iam_role.emr_service_role.arn

  tags = {
    Project = "EcomPropensity"
    Type    = "PersistentStreaming"
  }
}

# Note: The Airflow DAG does NOT reference this resource directly. 
# It creates its own separate, transient cluster but uses the same IAM roles and profiles.