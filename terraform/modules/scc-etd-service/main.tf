locals {
  parent_parts = split("/", var.parent)
  scope        = local.parent_parts[0]
  target_id    = local.parent_parts[1]

  effective_quota_project = (
    var.quota_project_id != ""
    ? var.quota_project_id
    : (local.scope == "projects" ? local.target_id : "")
  )

  normalized_state = upper(var.intended_enablement_state)
  normalized_mode  = upper(var.execution_mode)

  service_resource_name = "${var.parent}/locations/global/securityCenterServices/${var.service_name}"
  scm_api_base          = "https://securitycentermanagement.googleapis.com/v1"
  service_endpoint      = "${local.scm_api_base}/${local.service_resource_name}"

  has_modules = length(var.modules) > 0
  update_mask = join(",", compact([
    "intendedEnablementState",
    local.has_modules ? "modules" : "",
  ]))

  modules_payload = {
    for mod_name, mod_val in var.modules :
    upper(mod_name) => {
      intendedEnablementState = upper(
        try(mod_val.intendedEnablementState, try(mod_val.enablement_state, tostring(mod_val)))
      )
    }
  }

  patch_body = jsonencode(merge(
    {
      name                    = local.service_resource_name
      intendedEnablementState = local.normalized_state
    },
    local.has_modules ? { modules = local.modules_payload } : {}
  ))

  validate_query = var.validate_only ? "&validateOnly=true" : ""
  patch_url      = "${local.service_endpoint}?updateMask=${local.update_mask}${local.validate_query}"

  gcloud_scope_flag = (
    local.scope == "projects" ? "--project=${local.target_id}" :
    local.scope == "folders" ? "--folder=${local.target_id}" :
    "--organization=${local.target_id}"
  )
}

resource "google_project_service" "scc_apis" {
  for_each = local.scope == "projects" && var.enable_required_apis ? toset([
    "securitycenter.googleapis.com",
    "securitycentermanagement.googleapis.com",
  ]) : toset([])

  project            = local.target_id
  service            = each.value
  disable_on_destroy = false
}

data "google_client_config" "current" {}

resource "local_file" "gcloud_module_config" {
  count = local.normalized_mode == "GCLOUD_CLI" && local.has_modules ? 1 : 0

  filename        = "${path.module}/.terraform-scc-modules-${local.scope}-${local.target_id}.json"
  content         = jsonencode(local.modules_payload)
  file_permission = "0600"
}

resource "terraform_data" "scc_service_config" {
  triggers_replace = [
    local.service_resource_name,
    local.normalized_state,
    jsonencode(local.modules_payload),
    local.normalized_mode,
    tostring(var.validate_only),
  ]

  input = {
    service_resource_name     = local.service_resource_name
    intended_enablement_state = local.normalized_state
    modules                   = local.modules_payload
    execution_mode            = local.normalized_mode
  }

  provisioner "local-exec" {
    command = local.normalized_mode == "REST_API" ? (
      <<-EOT
      python3 -c '
import json, os, sys, urllib.request, urllib.error

url = os.environ["SCM_PATCH_URL"]
payload = os.environ["SCM_PATCH_BODY"].encode("utf-8")
quota_proj = os.environ.get("SCM_QUOTA_PROJECT", "")
token = os.environ["SCM_ACCESS_TOKEN"]

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json; charset=utf-8",
    "Accept": "application/json",
}
if quota_proj:
    headers["X-Goog-User-Project"] = quota_proj

req = urllib.request.Request(url, data=payload, headers=headers, method="PATCH")
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        print(f"Updated {data.get(\"name\")}: intended={data.get(\"intendedEnablementState\")}, effective={data.get(\"effectiveEnablementState\")}")
except urllib.error.HTTPError as err:
    sys.stderr.write(f"HTTP {err.code}: {err.read().decode(\"utf-8\", errors=\"replace\")}\n")
    sys.exit(1)
'
      EOT
      ) : (
      <<-EOT
      CLOUDSDK_CORE_DISABLE_PROMPTS=1 \
      gcloud scc manage services update "${var.service_name}" \
        "${local.gcloud_scope_flag}" \
        --enablement-state="${lower(local.normalized_state)}" \
        ${local.has_modules ? "--module-config-file=${local_file.gcloud_module_config[0].filename}" : ""} \
        ${var.validate_only ? "--validate-only" : ""} \
        --quiet
      EOT
    )

    environment = {
      SCM_PATCH_URL     = local.patch_url
      SCM_PATCH_BODY    = local.patch_body
      SCM_QUOTA_PROJECT = local.effective_quota_project
      SCM_ACCESS_TOKEN  = data.google_client_config.current.access_token
    }
  }

  depends_on = [
    google_project_service.scc_apis,
    local_file.gcloud_module_config,
  ]
}

data "http" "scc_service_state" {
  url = local.service_endpoint

  request_headers = merge(
    {
      Authorization = "Bearer ${data.google_client_config.current.access_token}"
      Accept        = "application/json"
    },
    local.effective_quota_project != "" ? {
      "X-Goog-User-Project" = local.effective_quota_project
    } : {}
  )

  depends_on = [terraform_data.scc_service_config]
}

check "scc_effective_enablement_verification" {
  assert {
    condition = (
      !var.enforce_effective_enablement_check ||
      local.scope == "folders" ||
      local.normalized_state == "DISABLED" ||
      try(jsondecode(data.http.scc_service_state.response_body).effectiveEnablementState, "UNKNOWN") == "ENABLED"
    )
    error_message = "Target ${var.parent} ${var.service_name} effectiveEnablementState is not ENABLED. Per the Security Center Management API v1 specification, effectiveEnablementState remains DISABLED until SCC Premium/Enterprise tier is active on the project (https://console.cloud.google.com/security/command-center/onboarding?project=${local.target_id})."
  }
}
