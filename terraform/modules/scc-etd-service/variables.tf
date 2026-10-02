variable "scope" {
  description = "Resource hierarchy scope: 'projects', 'folders', or 'organizations'."
  type        = string
  default     = "projects"

  validation {
    condition     = contains(["projects", "folders", "organizations"], var.scope)
    error_message = "scope must be one of: 'projects', 'folders', 'organizations'."
  }
}

variable "target_id" {
  description = "Target GCP Project ID, Folder ID, or Organization ID (do not include the 'projects/' prefix)."
  type        = string

  validation {
    condition     = can(regex("^[a-zA-Z0-9][a-zA-Z0-9._-]{0,62}$", var.target_id))
    error_message = "target_id must be a valid GCP Project ID/Number, Folder ID, or Organization ID."
  }
}

variable "quota_project_id" {
  description = "Optional GCP Project ID used for API quota/billing attribution (X-Goog-User-Project header). Required when scope is 'folders' or 'organizations' with user ADC."
  type        = string
  default     = ""
}

variable "service_name" {
  description = "Security Command Center built-in service ID (e.g. 'event-threat-detection', 'security-health-analytics', 'vm-threat-detection', 'container-threat-detection')."
  type        = string
  default     = "event-threat-detection"

  validation {
    condition     = can(regex("^[a-zA-Z0-9_-]{2,64}$", var.service_name))
    error_message = "service_name must contain only alphanumeric characters, hyphens, or underscores."
  }
}

variable "intended_enablement_state" {
  description = "Desired enablement state for the SCC service: 'ENABLED', 'DISABLED', or 'INHERITED'."
  type        = string
  default     = "ENABLED"

  validation {
    condition     = contains(["ENABLED", "DISABLED", "INHERITED"], var.intended_enablement_state)
    error_message = "intended_enablement_state must be 'ENABLED', 'DISABLED', or 'INHERITED'."
  }
}

variable "modules" {
  description = "Map of built-in detector module names (e.g. 'GKE_NODEPORT_SERVICE_CREATED') to their desired intendedEnablementState ('ENABLED' or 'DISABLED')."
  type        = map(string)
  default     = {}

  validation {
    condition = alltrue([
      for k, v in var.modules :
      can(regex("^[A-Z0-9_]{2,128}$", k)) && contains(["ENABLED", "DISABLED", "INHERITED"], v)
    ])
    error_message = "All module keys must be uppercase module identifiers (^[A-Z0-9_]+$) and values must be 'ENABLED', 'DISABLED', or 'INHERITED'."
  }
}

variable "enable_required_apis" {
  description = "Whether to automatically enable securitycenter.googleapis.com and securitycentermanagement.googleapis.com when scope is 'projects'."
  type        = bool
  default     = true
}

variable "execution_mode" {
  description = "Backend mechanism used to patch the SecurityCenterService resource: 'rest_api' (direct HTTPS PATCH to securitycentermanagement.googleapis.com/v1) or 'gcloud_cli' (wraps gcloud scc manage services update --quiet)."
  type        = string
  default     = "rest_api"

  validation {
    condition     = contains(["rest_api", "gcloud_cli"], var.execution_mode)
    error_message = "execution_mode must be either 'rest_api' or 'gcloud_cli'."
  }
}

variable "enforce_premium_tier_check" {
  description = "When true (for project/organization scope), emits a Terraform check warning if the target resource's SCC billingTier is not PREMIUM or ENTERPRISE."
  type        = bool
  default     = false
}
