## infra/cloud_run_deployment.tf (Cloud Run Service & Firestore Index)

# Generates a unique ID to append to the service name, ensuring uniqueness 
# when working with the random provider.
resource "random_id" "suffix" {
  byte_length = 3 # Generates 6 hex characters, e.g., "a3f5b7"
}

# 1. Define the Cloud Run Service
resource "google_cloud_run_v2_service" "app_service" {
  # Append a short unique suffix to the service name
  name     = "${var.cloud_run_service_name}-${random_id.suffix.hex}" 
  location = var.gcp_region 
  project  = var.gcp_project_id

  template {
    # ----------------------------------------------------
    # Scaling, Concurrency, and Timeout Configurations (Optimized for Streamlit)
    # ----------------------------------------------------
    scaling {
      min_instance_count = 0 # Scale to zero when idle (cost-saving)
      max_instance_count = 10 # Maximum instances allowed
    }
    
    # Limit concurrent requests to 50 per instance (safer for stateful apps like Streamlit)
    max_instance_request_concurrency = 50 
    
    # Set request timeout to 10 minutes (600 seconds) for long sessions
    timeout = "600s" 

    containers {
  # Use the image path provided in terraform.tfvars
  image = var.docker_image_path 
  ports {
    container_port = 8080 
  }
  env {
        name  = "RELOAD_TRIGGER"
        value = timestamp()  # Forces a change on every `terraform apply`
  }
  # Inject the API Key as a secure Environment Variable
  env {
    name  = "OPENWEATHER_API_KEY"
    value = var.openweather_api_key
  }
  
  # Inject Firebase/Firestore Service Account Credentials (NEW ADDITIONS)
  env {
     name = "FIREBASE_TYPE"
     value = var.firebase_type 
  }

  env { 
    name = "FIREBASE_PROJECT_ID" 
    value = var.gcp_project_id 
    } # Usually the GCP project ID

  env { 
    name = "FIREBASE_PRIVATE_KEY_ID" 
    value = var.firebase_private_key_id 
    }

  env {
   name = "FIREBASE_PRIVATE_KEY"
   value = var.firebase_private_key 
   }
  env { 
    name = "FIREBASE_CLIENT_EMAIL" 
    value = var.firebase_client_email 
  }
  env { 
  name = "FIREBASE_CLIENT_ID" 
  value = var.firebase_client_id 
  }
  env { 
    name = "FIREBASE_AUTH_URI"
     value = var.firebase_auth_uri
 }
  env { 
  name = "FIREBASE_TOKEN_URI" 
  value = var.firebase_token_uri 
  }
  env { 
    name = "FIREBASE_AUTH_PROVIDER_X509_CERT_URL" 
    value = var.firebase_auth_provider_x509_cert_url 
  }
  env { 
  name = "FIREBASE_CLIENT_X509_CERT_URL" 
  value = var.firebase_client_x509_cert_url 
  }
  
  # NOTE: The application code must be configured to read these environment variables 
  # and use them to initialize the Firebase Admin SDK.
}
    
    # Optional: Enable dedicated CPU for better background processing 
    # Uncomment the line below if you require CPU to be allocated even when idle:
    # dedicated_cpu = true 
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
  
  depends_on = [google_project_service.cloudrun_api]
}

# 2. IAM Policy to Allow Unauthenticated Access (Public Service)
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  location = google_cloud_run_v2_service.app_service.location
  project  = google_cloud_run_v2_service.app_service.project
  name     = google_cloud_run_v2_service.app_service.name
  role     = "roles/run.invoker"
  member   = "allUsers" # Makes the service publicly accessible
  depends_on = [google_cloud_run_v2_service.app_service]
}

# 3. Define the Custom Firestore Index
resource "google_firestore_index" "history_query_index" {
  project     = var.gcp_project_id
  collection  = "weather_history"
  database    = google_firestore_database.database.name
  api_scope   = "DATASTORE_MODE_API"
  query_scope = "COLLECTION_GROUP"

  fields {
    field_path = "city"
    order      = "ASCENDING"
  }
  
  fields {
    field_path = "timestamp"
    order      = "DESCENDING"
  }
  depends_on = [google_firestore_database.database]
}

# Output the Service URL for easy access
output "cloud_run_url" {
  description = "The publicly accessible URL for the Cloud Run service."
  value       = google_cloud_run_v2_service.app_service.uri
}