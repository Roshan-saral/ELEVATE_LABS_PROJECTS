## infra/main.tf (Revised for Cloud Run & Full Automation)

# 1. Configure Providers
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    # Add the random provider for generating unique IDs
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "google" {
  project = var.gcp_project_id 
  region  = var.gcp_region 
}

# 2. Enable Required APIs (App Engine removed, Cloud Run added)

# Cloud Run API
resource "google_project_service" "cloudrun_api" {
  project            = var.gcp_project_id
  service            = "run.googleapis.com"
  # Set to true so API is disabled on terraform destroy
  disable_on_destroy = true 
}

# Firestore API
resource "google_project_service" "firestore_api" {
  project            = var.gcp_project_id
  service            = "firestore.googleapis.com"
  # Set to true so API is disabled on terraform destroy
  disable_on_destroy = true 
}

resource "google_project_service" "compute_api" {
  project            = var.gcp_project_id
  service            = "compute.googleapis.com"
  disable_on_destroy = true
}

# 3. Create a Basic Firestore Database Instance
# NOTE: Removed dependency on the now-deleted google_app_engine_application.app
resource "google_firestore_database" "database" {
  project     = var.gcp_project_id
  name        = "(default)" 
  location_id = var.firestore_location 
  type        = "FIRESTORE_NATIVE"
  depends_on  = [google_project_service.firestore_api]
}

resource "google_project_service" "artifact_registry_api" {
  project            = var.gcp_project_id
  service            = "artifactregistry.googleapis.com"
  disable_on_destroy = true
}

# 4. IAM Role Assignment for Cloud Run to Access Firestore

# NOTE: This section requires the Cloud Run service resource (app_service) 
# to be defined elsewhere so its unique service_identity attribute is available.
# Data source to fetch the email of the project's default Compute Engine SA
data "google_compute_default_service_account" "default_sa" {
  project = var.gcp_project_id
  depends_on = [google_project_service.compute_api]
}


# 4a. Grant Firestore Data Access Role (roles/datastore.user)
resource "google_project_iam_member" "cloudrun_firestore_access" {
  project = var.gcp_project_id
  role    = "roles/datastore.user"
  # Use the default Compute SA email
  member  = "serviceAccount:${data.google_compute_default_service_account.default_sa.email}"
}