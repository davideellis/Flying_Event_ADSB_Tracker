variable "aws_region" {
  description = "AWS region for Lightsail resources."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Base name for Terraform-managed resources."
  type        = string
  default     = "flying-event-adsb-tracker"
}

variable "availability_zone" {
  description = "Lightsail availability zone."
  type        = string
  default     = "us-east-1a"
}

variable "lightsail_bundle_id" {
  description = "Lightsail instance bundle sized to keep monthly costs low."
  type        = string
  default     = "nano_3_0"
}

variable "lightsail_blueprint_id" {
  description = "Lightsail OS blueprint."
  type        = string
  default     = "ubuntu_24_04"
}

variable "public_key_path" {
  description = "Optional path to a local SSH public key to register with Lightsail."
  type        = string
  default     = ""
}

variable "domain_name" {
  description = "Optional DNS name for the application."
  type        = string
  default     = ""
}
