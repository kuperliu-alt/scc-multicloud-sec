locals {
  parsed_billing_metadata = (
    var.scope != "folders" && length(data.http.billing_metadata) > 0
    ? try(jsondecode(data.http.billing_metadata[0].response_body), {})
    : {}
  )
  parsed_service_state = try(jsondecode(data.http.scc_service_state.response_body), {})
}

output "service_resource_name" {
  description = "Canonical resource name of the configured SecurityCenterService."
  value       = try(local.parsed_service_state.name, local.service_resource_name)
}

output "billing_tier" {
  description = "Current SCC billing tier reported by GetBillingMetadata (STANDARD, PREMIUM, ENTERPRISE, or FOLDER_INHERITED)."
  value       = var.scope == "folders" ? "FOLDER_INHERITED" : try(local.parsed_billing_metadata.billingTier, "UNKNOWN")
}

output "intended_enablement_state" {
  description = "Live intendedEnablementState read back from the Security Center Management API."
  value       = try(local.parsed_service_state.intendedEnablementState, var.intended_enablement_state)
}

output "effective_enablement_state" {
  description = "Live effectiveEnablementState read back from the Security Center Management API."
  value       = try(local.parsed_service_state.effectiveEnablementState, "UNKNOWN")
}

output "update_time" {
  description = "Last update timestamp of the SecurityCenterService resource."
  value       = try(local.parsed_service_state.updateTime, null)
}

output "configured_modules_state" {
  description = "Live state of the specific built-in modules managed by this Terraform module."
  value = {
    for k in keys(var.modules) :
    k => try(local.parsed_service_state.modules[k], null)
  }
}

output "console_onboarding_url" {
  description = "Direct Cloud Console SCC onboarding URL (applicable when scope is 'projects')."
  value = (
    var.scope == "projects"
    ? "https://console.cloud.google.com/security/command-center/onboarding?project=${var.target_id}"
    : null
  )
}
