variable "parent" {
  description = "Resource hierarchy parent in the form 'projects/<PROJECT_ID>', 'folders/<FOLDER_ID>', or 'organizations/<ORG_ID>'."
  type        = string

  validation {
    condition     = can(regex("^(projects|folders|organizations)/[a-zA-Z0-9][a-zA-Z0-9._-]{0,62}$", var.parent))
    error_message = "parent must match 'projects/<ID>', 'folders/<ID>', or 'organizations/<ID>'."
  }
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
    condition     = contains(["ENABLED", "DISABLED", "INHERITED"], upper(var.intended_enablement_state))
    error_message = "intended_enablement_state must be 'ENABLED', 'DISABLED', or 'INHERITED'."
  }
}

variable "modules" {
  description = "Map of built-in ETD detector module names (e.g. 'PERSISTENCE_IAM_ANOMALOUS_GRANT') to their desired enablement state. Accepts either a string ('ENABLED'/'DISABLED') or an object({ enablement_state = string })."
  type        = any
  default     = {}
}

variable "execution_mode" {
  description = "Backend mechanism used to patch the SecurityCenterService resource: 'REST_API' (direct HTTPS PATCH to securitycentermanagement.googleapis.com/v1) or 'GCLOUD_CLI' (wraps gcloud scc manage services update --quiet)."
  type        = string
  default     = "REST_API"

  validation {
    condition     = contains(["REST_API", "GCLOUD_CLI"], upper(var.execution_mode))
    error_message = "execution_mode must be 'REST_API' or 'GCLOUD_CLI'."
  }
}

variable "validate_only" {
  description = "When true (in REST_API mode), appends '&validateOnly=true' to dry-run validate the PATCH payload with the API without persisting changes."
  type        = bool
  default     = false
}

variable "quota_project_id" {
  description = "Optional GCP Project ID used for API quota/billing attribution (X-Goog-User-Project header). Useful when parent is 'folders/*' or 'organizations/*' with user ADC."
  type        = string
  default     = ""
}

variable "enable_required_apis" {
  description = "Whether to automatically enable securitycenter.googleapis.com and securitycentermanagement.googleapis.com when parent is 'projects/*'."
  type        = bool
  default     = true
}

variable "enforce_effective_enablement_check" {
  description = "When true, emits a Terraform check warning if intended_enablement_state is ENABLED on a project but effectiveEnablementState remains DISABLED (which indicates SCC Premium is not yet active on the project)."
  type        = bool
  default     = false
}
