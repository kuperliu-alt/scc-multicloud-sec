locals {
  parent = "${var.scope}/${var.target_id}"
  effective_quota_project = (
    var.quota_project_id != ""
    ? var.quota_project_id
    : (var.scope == "projects" ? var.target_id : "")
  )
  service_resource_name = "${local.parent}/locations/global/securityCenterServices/${var.service_name}"
  scm_api_base          = "https://securitycentermanagement.googleapis.com/v1"
  service_endpoint      = "${local.scm_api_base}/${local.service_resource_name}"

  has_modules = length(var.modules) > 0
  update_mask = join(",", compact([
    "intendedEnablementState",
    local.has_modules ? "modules" : "",
  ]))

  modules_payload = {
    for mod_name, mod_state in var.modules :
    mod_name => {
      intendedEnablementState = mod_state
    }
  }

  patch_body = jsonencode(merge(
    {
      name                    = local.service_resource_name
      intendedEnablementState = var.intended_enablement_state
    },
    local.has_modules ? { modules = local.modules_payload } : {}
  ))

  gcloud_scope_flag = (
    var.scope == "projects" ? "--project=${var.target_id}" :
    var.scope == "folders" ? "--folder=${var.target_id}" :
    "--organization=${var.target_id}"
  )
}

resource "google_project_service" "scc_apis" {
  for_each = var.scope == "projects" && var.enable_required_apis ? toset([
    "securitycenter.googleapis.com",
    "securitycentermanagement.googleapis.com",
  ]) : toset([])

  project            = var.target_id
  service            = each.value
  disable_on_destroy = false
}

data "google_client_config" "current" {}

data "http" "billing_metadata" {
  count = var.scope != "folders" ? 1 : 0

  url = "${local.scm_api_base}/${local.parent}/locations/global/billingMetadata"

  request_headers = merge(
    {
      Authorization = "Bearer ${data.google_client_config.current.access_token}"
      Accept        = "application/json"
    },
    local.effective_quota_project != "" ? {
      "X-Goog-User-Project" = local.effective_quota_project
    } : {}
  )

  depends_on = [google_project_service.scc_apis]
}

resource "local_file" "gcloud_module_config" {
  count = var.execution_mode == "gcloud_cli" && local.has_modules ? 1 : 0

  filename        = "${path.module}/.terraform-scc-modules-${var.scope}-${var.target_id}.json"
  content         = jsonencode(local.modules_payload)
  file_permission = "0600"
}

resource "terraform_data" "scc_service_config" {
  triggers_replace = [
    local.service_resource_name,
    var.intended_enablement_state,
    jsonencode(local.modules_payload),
    var.execution_mode,
  ]

  input = {
    service_resource_name     = local.service_resource_name
    intended_enablement_state = var.intended_enablement_state
    modules                   = local.modules_payload
    execution_mode            = var.execution_mode
  }

  provisioner "local-exec" {
    command = var.execution_mode == "rest_api" ? (
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
      CLOUDSDK_METRICS_ENVIRONMENT=datacloud.jetski \
      gcloud scc manage services update "${var.service_name}" \
        "${local.gcloud_scope_flag}" \
        --enablement-state="${lower(var.intended_enablement_state)}" \
        ${local.has_modules ? "--module-config-file=${local_file.gcloud_module_config[0].filename}" : ""} \
        --quiet
      EOT
    )

    environment = {
      SCM_PATCH_URL     = "${local.service_endpoint}?updateMask=${local.update_mask}"
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

check "scc_premium_tier_verification" {
  assert {
    condition = (
      !var.enforce_premium_tier_check ||
      var.scope == "folders" ||
      contains(
        ["PREMIUM", "ENTERPRISE"],
        try(jsondecode(data.http.billing_metadata[0].response_body).billingTier, "UNKNOWN")
      )
    )
    error_message = "Target ${local.parent} SCC billingTier is not PREMIUM or ENTERPRISE. Project-level SCC Premium tier activation requires a one-time Console action at https://console.cloud.google.com/security/command-center/onboarding?project=${var.target_id} (PANTHEON-restricted RPC)."
  }
}
