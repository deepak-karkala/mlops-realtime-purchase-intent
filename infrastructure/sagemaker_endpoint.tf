resource "aws_ecr_repository" "serving_repo" {
  name = "ecom-propensity/serving"
}

resource "aws_sagemaker_model" "propensity_model" {
  name               = "propensity-model-${var.model_version}" # Versioned model
  execution_role_arn = aws_iam_role.sagemaker_training_role.arn # Reuse role for simplicity
  
  primary_container {
    image = "${aws_ecr_repository.serving_repo.repository_url}:${var.image_tag}"
    environment = {
      "MODEL_VERSION" = var.model_version
    }
  }
}

resource "aws_sagemaker_endpoint_configuration" "propensity_endpoint_config" {
  name = "propensity-endpoint-config-${var.model_version}"

  production_variants {
    variant_name           = "v1" # This would be the old variant in a canary
    model_name             = aws_sagemaker_model.propensity_model.name
    instance_type          = "ml.c5.xlarge"
    initial_instance_count = 2
    initial_variant_weight = 1.0 # In a canary, this would be updated
  }
  
  # When doing a canary, you would add a second production_variant block
  # for the new model and adjust the initial_variant_weight.
}

resource "aws_sagemaker_endpoint" "propensity_endpoint" {
  name                 = "propensity-endpoint"
  endpoint_config_name = aws_sagemaker_endpoint_configuration.propensity_endpoint_config.name
}