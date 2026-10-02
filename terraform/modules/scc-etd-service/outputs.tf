locals {
  parsed_service_state = try(jsondecode(data.http.scc_service_state.response_body), {})
  effective_state      = try(local.parsed_service_state.effectiveEnablementState, "UNKNOWN")
  enabled_module_count = length([
    for k, v in try(local.parsed_service_state.modules, {}) : k
    if try(v.effectiveEnablementState, try(v.intendedEnablementState, "")) == "ENABLED"
  ])
}

output "service_resource_name" {
  description = "Canonical resource name of the configured SecurityCenterService."
  value       = try(local.parsed_service_state.name, local.service_resource_name)
}

output "intended_enablement_state" {
  description = "Live intendedEnablementState read back from the Security Center Management API."
  value       = try(local.parsed_service_state.intendedEnablementState, local.normalized_state)
}

output "effective_enablement_state" {
  description = "Live effectiveEnablementState read back from the Security Center Management API."
  value       = local.effective_state
}

output "tier_eligibility" {
  description = "Inferred SCC tier eligibility from the official Public GA SecurityCenterService effectiveEnablementState."
  value = (
    local.scope == "folders" ? "FOLDER_POLICY_SCOPE" :
    local.effective_state == "ENABLED" ? "PREMIUM_OR_ENTERPRISE" :
    "STANDARD_OR_UNONBOARDED"
  )
}

output "enabled_module_count" {
  description = "Count of built-in detector modules currently in ENABLED effective state."
  value       = local.enabled_module_count
}

output "update_time" {
  description = "Last update timestamp of the SecurityCenterService resource."
  value       = try(local.parsed_service_state.updateTime, null)
}

output "configured_modules_state" {
  description = "Live state of the specific built-in modules managed by this Terraform module."
  value = {
    for k in keys(local.modules_payload) :
    k => try(local.parsed_service_state.modules[k], null)
  }
}

output "console_onboarding_url" {
  description = "Direct Cloud Console SCC onboarding URL (emitted when scope is 'projects' and effectiveEnablementState is not yet ENABLED)."
  value = (
    local.scope == "projects" && local.effective_state != "ENABLED"
    ? "https://console.cloud.google.com/security/command-center/onboarding?project=${local.target_id}"
    : null
  )
}
