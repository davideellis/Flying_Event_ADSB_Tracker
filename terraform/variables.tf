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

variable "repo_url" {
  description = "Git repository URL the instance should clone during bootstrap."
  type        = string
  default     = "https://github.com/davideellis/Flying_Event_ADSB_Tracker.git"
}

variable "repo_branch" {
  description = "Git branch to deploy on the Lightsail instance."
  type        = string
  default     = "main"
}

variable "app_secret_key" {
  description = "Secret key used for session signing in production."
  type        = string
  sensitive   = true
}

variable "bootstrap_admin_email" {
  description = "Initial admin email for production bootstrap."
  type        = string
  default     = "admin@example.com"
}

variable "bootstrap_admin_password" {
  description = "Initial admin password for production bootstrap."
  type        = string
  sensitive   = true
}

variable "postgres_password" {
  description = "Password for the Postgres container on the production host."
  type        = string
  sensitive   = true
}

variable "adsb_provider" {
  description = "ADSB provider implementation to use in production."
  type        = string
  default     = "http"
}

variable "adsb_poll_seconds" {
  description = "Polling interval for active events."
  type        = number
  default     = 10
}

variable "adsb_http_base_url" {
  description = "Base URL for the HTTP ADSB provider."
  type        = string
  default     = "https://api.adsb.lol"
}

variable "adsb_http_area_path_template" {
  description = "Area-query path template for the HTTP ADSB provider."
  type        = string
  default     = "/v2/lat/{lat}/lon/{lon}/dist/{dist}"
}
