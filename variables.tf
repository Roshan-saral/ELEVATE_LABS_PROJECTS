## infra/variables.tf (Revised for Cloud Run)

# -----------------------------------------------------------------------------
# GCP Core Configuration Variables
# -----------------------------------------------------------------------------

variable "gcp_project_id" {
  description = "The ID of the GCP project (e.g., weatherdashboard-bc3d3)."
  type        = string
}

variable "gcp_region" {
  description = "The region for the Google Provider and Cloud Run deployment (e.g., us-central1)."
  type        = string
  default     = "us-central1"
}

# App Engine variable removed

variable "firestore_location" {
  description = "The multi-region or regional location for the Firestore Database (e.g., nam5, eur3)."
  type        = string
  default     = "nam5"
}

# -----------------------------------------------------------------------------
# Cloud Run & Deployment Variables
# -----------------------------------------------------------------------------

variable "cloud_run_service_name" {
  description = "The desired name for the Cloud Run service."
  type        = string
  default     = "weather-dashboard-app"
}

variable "docker_image_path" {
  description = "The full path to the Docker image in Artifact/Container Registry (e.g., gcr.io/project-id/image-name:tag)."
  type        = string
}


# -----------------------------------------------------------------------------
# App Secrets and Credentials (Sensitive)
# -----------------------------------------------------------------------------
# NOTE: These variables are marked 'sensitive' and their values should be 
# provided via a separate 'terraform.tfvars' file that is NOT committed to Git.

variable "openweather_api_key" {
  description = "The OpenWeatherMap API Key."
  type        = string
  sensitive   = true 
}

# --- Firebase Service Account Credentials ---
# Note: It's often better to put the whole JSON content into one variable and 
# store it in Secret Manager, but keeping your original variables for structure.

variable "firebase_type" {
  description = "The 'type' field from the Firebase Service Account JSON file (should be 'service_account')."
  type        = string
  sensitive   = true
}



variable "firebase_private_key_id" {
  description = "The 'private_key_id' from the Firebase Service Account JSON file."
  type        = string
  sensitive   = true
}

variable "firebase_private_key" {
  description = "The entire 'private_key' string from the JSON file, including BEGIN/END lines and escaped newlines (e.g., \\n)."
  type        = string
  sensitive   = true
}

variable "firebase_client_id" {
  description = "The 'client_id' from the Firebase Service Account JSON file."
  type        = string
  sensitive   = true
}


variable "firebase_client_email" {
  description = "The 'client_email' from the Firebase Service Account JSON file."
  type        = string
  sensitive   = true
}

# The following 5 variables are also required by your Python code's reconstruction logic:

variable "firebase_auth_uri" {
  description = "The 'auth_uri' from the Firebase Service Account JSON file."
  type        = string
  sensitive   = true
}

variable "firebase_token_uri" {
  description = "The 'token_uri' from the Firebase Service Account JSON file."
  type        = string
  sensitive   = true
}

variable "firebase_auth_provider_x509_cert_url" {
  description = "The 'auth_provider_x509_cert_url' from the Firebase JSON."
  type        = string
  sensitive   = true
}

variable "firebase_client_x509_cert_url" {
  description = "The 'client_x509_cert_url' from the Firebase Service Account JSON file."
  type        = string
  sensitive   = true
}