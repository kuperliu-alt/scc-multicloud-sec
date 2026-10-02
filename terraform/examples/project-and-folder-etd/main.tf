terraform {
  required_version = ">= 1.3.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0.0"
    }
    null = {
      source  = "hashicorp/null"
      version = ">= 3.2.0"
    }
    http = {
      source  = "hashicorp/http"
      version = ">= 3.4.0"
    }
  }
}

variable "folder_id" {
  description = "Optional GCP Folder ID (numeric) where ETD policy should be configured once and inherited by child projects. Leave empty to skip folder-level configuration."
  type        = string
  default     = ""
}

variable "project_ids" {
  description = "List of GCP Project IDs to prepare (enable APIs) and configure/verify for SCC Event Threat Detection."
  type        = list(string)
  default     = []
}

variable "project_enablement_state" {
  description = "Intended enablement state for individual projects. Use INHERITED when folder_id is configured, or ENABLED for standalone project-level configuration."
  type        = string
  default     = "ENABLED"
}

variable "module_overrides" {
  description = "Map of built-in ETD detector modules to explicitly enable or disable."
  type = map(object({
    enablement_state = string
    configuration    = optional(map(any))
  }))
  default = {
    PERSISTENCE_IAM_ANOMALOUS_GRANT = {
      enablement_state = "ENABLED"
    }
    MALWARE_BAD_DOMAIN = {
      enablement_state = "ENABLED"
    }
    CRYPTOMINING_POOL_DOMAIN = {
      enablement_state = "ENABLED"
    }
  }
}

# 1. Enable prerequisite SCC APIs on all target projects in the fleet
resource "google_project_service" "scc_apis" {
  for_each = {
    for pair in setproduct(toset(var.project_ids), toset([
      "securitycentermanagement.googleapis.com",
      "securitycenter.googleapis.com",
      "cloudresourcemanager.googleapis.com",
    ])) : "${pair[0]}/${pair[1]}" => {
      project = pair[0]
      service = pair[1]
    }
  }

  project            = each.value.project
  service            = each.value.service
  disable_on_destroy = false
}

# 2. Optional Folder-Level ETD Policy (Recommended when team has Folder access, no Org ownership)
module "folder_etd_policy" {
  count  = var.folder_id != "" ? 1 : 0
  source = "../../modules/scc-etd-service"

  parent                    = "folders/${var.folder_id}"
  intended_enablement_state = "ENABLED"
  execution_mode            = "REST_API"
  modules                   = var.module_overrides
}

# 3. Per-Project ETD Configuration & Live Tier/Effective-State Readback
module "project_etd_service" {
  for_each = toset(var.project_ids)
  source   = "../../modules/scc-etd-service"

  parent                    = "projects/${each.value}"
  intended_enablement_state = var.project_enablement_state
  execution_mode            = "REST_API"
  modules                   = var.project_enablement_state == "INHERITED" ? {} : var.module_overrides

  depends_on = [
    google_project_service.scc_apis,
    module.folder_etd_policy,
  ]
}

output "project_etd_status" {
  description = "Per-project SCC billing tier, intended state, effective ETD state, and enabled detector count."
  value = {
    for pid, mod in module.project_etd_service : pid => {
      billing_tier               = mod.billing_tier
      intended_enablement_state  = mod.intended_enablement_state
      effective_enablement_state = mod.effective_enablement_state
      enabled_module_count       = mod.enabled_module_count
      onboarding_console_url     = mod.billing_tier == "PREMIUM" ? null : "https://console.cloud.google.com/security/command-center/onboarding?project=${pid}"
    }
  }
}
