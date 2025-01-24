# Define required providers and their versions
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
    godaddy = {
      source  = "n3integration/godaddy"
      version = "~> 1.9.0"
    }
  }
}

# Configure the Google Cloud provider
provider "google" {
  project = "pdftable-app"
  region  = "us-central1"
}

# Configure the GoDaddy provider
provider "godaddy" {
  key    = var.godaddy_api_key
  secret = var.godaddy_api_secret
}

# Cloud Run service configuration
resource "google_cloud_run_service" "app" {
  name     = "pdf-table-extractor"
  location = "us-central1"

  template {
    spec {
      containers {
        image = "gcr.io/${var.project_id}/pdf-table-extractor:latest"
        ports {
          container_port = 8080
        }
        resources {
          limits = {
            cpu    = "1000m"
            memory = "2Gi"
          }
        }
      }
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale"     = "1"
        "autoscaling.knative.dev/maxScale"     = "10"
        "run.googleapis.com/cpu-throttling"    = "false"
        "run.googleapis.com/execution-timeout" = "3600s"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

# Public access IAM configuration
resource "google_cloud_run_service_iam_member" "public" {
  service  = google_cloud_run_service.app.name
  location = google_cloud_run_service.app.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Google Cloud DNS zone configuration
resource "google_dns_managed_zone" "pdftable" {
  name        = "pdftable-zone"
  dns_name    = "pdftable.online."
  description = "DNS zone for pdf-table-extractor"
}

# GoDaddy nameserver configuration
resource "godaddy_domain_record" "nameservers" {
  domain      = "pdftable.online"
  nameservers = google_dns_managed_zone.pdftable.name_servers

  depends_on = [google_dns_managed_zone.pdftable]
}

# Cloud Run domain mapping
resource "google_cloud_run_domain_mapping" "default" {
  location = google_cloud_run_service.app.location
  name     = "pdftable.online"

  metadata {
    namespace = var.project_id
  }

  spec {
    route_name = google_cloud_run_service.app.name
  }

  depends_on = [google_dns_managed_zone.pdftable]
}

# Variables
variable "project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "pdftable-app"
}

variable "godaddy_api_key" {
  description = "GoDaddy API Key from developer.godaddy.com"
  type        = string
  sensitive   = true
}

variable "godaddy_api_secret" {
  description = "GoDaddy API Secret from developer.godaddy.com"
  type        = string
  sensitive   = true
}

# Outputs
output "nameservers" {
  description = "Google Cloud DNS nameservers"
  value       = google_dns_managed_zone.pdftable.name_servers
}

output "service_url" {
  description = "Cloud Run service URL"
  value       = google_cloud_run_service.app.status[0].url
}

output "domain_status" {
  description = "Domain mapping status"
  value       = google_cloud_run_domain_mapping.default.status
}
