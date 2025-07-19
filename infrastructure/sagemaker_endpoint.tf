variable "champion_model_name" {
  description = "The name of the currently deployed champion model."
  type        = string
}

variable "challenger_model_name" {
  description = "The name of the new challenger model for the A/B test. Can be empty."
  type        = string
  default     = ""
}

variable "challenger_weight" {
  description = "The percentage of traffic (0-100) to route to the challenger model."
  type        = number
  default     = 0
}

resource "aws_sagemaker_endpoint_configuration" "propensity_endpoint_config" {
  name = "propensity-endpoint-config-ab-test"
  # This lifecycle block prevents Terraform from destroying the old config before the new one is active
  lifecycle {
    create_before_destroy = true
  }

  # --- Champion Model Variant ---
  production_variants {
    variant_name           = "champion"
    model_name             = var.champion_model_name
    instance_type          = "ml.c5.xlarge"
    initial_instance_count = 2
    initial_variant_weight = 100 - var.challenger_weight
  }

  # --- Challenger Model Variant (Created Conditionally) ---
  dynamic "production_variants" {
    # This block is only created if a challenger_model_name is provided
    for_each = var.challenger_model_name != "" ? [1] : []
    content {
      variant_name           = "challenger"
      model_name             = var.challenger_model_name
      instance_type          = "ml.c5.xlarge"
      initial_instance_count = 2 # Start with same capacity for fair performance test
      initial_variant_weight = var.challenger_weight
    }
  }
}

resource "aws_sagemaker_endpoint" "propensity_endpoint" {
  name                 = "propensity-endpoint"
  endpoint_config_name = aws_sagemaker_endpoint_configuration.propensity_endpoint_config.name
}