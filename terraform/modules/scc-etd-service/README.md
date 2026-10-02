# Terraform Module: SCC Event Threat Detection (ETD) Built-in Service & Modules

Because the `hashicorp/google` Terraform provider (verified through `v8.5.0`) only includes resources for ETD **custom** modules (`google_scc_management_organization_event_threat_detection_custom_module` / `google_scc_event_threat_detection_custom_module`) and does not yet implement a native resource for the built-in `SecurityCenterService` (`securityCenterServices/event-threat-detection`), this module bridges the gap using the **100% Public GA Security Center Management API v1**.

---

## ✨ Features

1. **Multi-Scope Support (`organizations/*`, `folders/*`, `projects/*`)**:
   - Configure `event-threat-detection` at the **Organization**, **Folder**, or **Project** level using a single `parent` variable (e.g. `folders/<FOLDER_ID>` or `projects/<PROJECT_ID>`).
2. **Built-in Service State & Per-Detector Module Overrides**:
   - Set `intended_enablement_state` (`ENABLED`, `DISABLED`, or `INHERITED`).
   - Override individual built-in ETD detector modules (e.g. `PERSISTENCE_IAM_ANOMALOUS_GRANT`, `CRYPTOMINING_POOL_DOMAIN`, `EXFILTRATION_BIGQUERY_ANOMALOUS_DATA_EGRESS`) while preserving the other ~170 built-in detectors via `updateMask=intendedEnablementState,modules`.
3. **Dual Execution Modes (`REST_API` vs `GCLOUD_CLI`)**:
   - **`REST_API` (Default, Recommended)**: Calls `PATCH https://securitycentermanagement.googleapis.com/v1/{parent}/locations/global/securityCenterServices/event-threat-detection` directly and supports `?validateOnly=true`.
   - **`GCLOUD_CLI`**: Invokes `gcloud scc manage services update event-threat-detection --quiet` (the `--quiet` flag is critical in non-interactive Terraform runs because `gcloud` prompts `Do you want to continue (Y/n)?` by default).
4. **Live Drift Detection & Tier Eligibility Verification (`data.http`)**:
   - Reads the live `securityCenterServices/event-threat-detection` resource from the official Public GA Security Center Management API v1 and exposes `effective_enablement_state`, `tier_eligibility`, and `enabled_module_count` as Terraform outputs.

---

## 🚀 Usage

### Folder-Level ETD Enablement (Cascades to Child Projects)
```hcl
module "folder_etd_service" {
  source = "../../modules/scc-etd-service"

  parent                    = "folders/<FOLDER_ID>"
  intended_enablement_state = "ENABLED"
  execution_mode            = "REST_API"

  modules = {
    PERSISTENCE_IAM_ANOMALOUS_GRANT = {
      enablement_state = "ENABLED"
    }
    MALWARE_BAD_DOMAIN = {
      enablement_state = "ENABLED"
    }
  }
}
```

### Project-Level ETD Enablement
```hcl
module "project_etd_service" {
  source = "../../modules/scc-etd-service"

  parent                    = "projects/<PROJECT_ID>"
  intended_enablement_state = "ENABLED"
  execution_mode            = "REST_API"

  modules = {
    PERSISTENCE_IAM_ANOMALOUS_GRANT = {
      enablement_state = "ENABLED"
    }
  }
}
```

---

## 📋 Inputs

| Name | Description | Type | Default | Required |
| :--- | :--- | :--- | :--- | :---: |
| `parent` | Resource hierarchy parent in the form `projects/<PROJECT_ID>`, `folders/<FOLDER_ID>`, or `organizations/<ORG_ID>`. | `string` | n/a | yes |
| `service_name` | SCC built-in service ID (`event-threat-detection`, `security-health-analytics`, `vm-threat-detection`, `container-threat-detection`). | `string` | `"event-threat-detection"` | no |
| `intended_enablement_state` | Desired enablement state (`ENABLED`, `DISABLED`, `INHERITED`). | `string` | `"ENABLED"` | no |
| `modules` | Map of built-in ETD module names to desired `enablement_state`. | `any` | `{}` | no |
| `execution_mode` | Execution backend (`REST_API` or `GCLOUD_CLI`). | `string` | `"REST_API"` | no |
| `validate_only` | When `true`, dry-runs the update via `validateOnly=true` / `--validate-only`. | `bool` | `false` | no |
| `quota_project_id` | Optional GCP Project ID for `X-Goog-User-Project` header. | `string` | `""` | no |
| `enable_required_apis` | Automatically enable `securitycenter.googleapis.com` and `securitycentermanagement.googleapis.com` when `parent` is `projects/*`. | `bool` | `true` | no |
| `enforce_effective_enablement_check` | Emit a Terraform `check` warning if `effectiveEnablementState` is not `ENABLED`. | `bool` | `false` | no |

---

## 📤 Outputs

| Name | Description |
| :--- | :--- |
| `service_resource_name` | Full resource name of the ETD `SecurityCenterService`. |
| `intended_enablement_state` | Live `intendedEnablementState` returned by the API. |
| `effective_enablement_state` | Live `effectiveEnablementState` returned by the API (`ENABLED` or `DISABLED`). |
| `tier_eligibility` | Inferred SCC tier eligibility (`PREMIUM_OR_ENTERPRISE`, `STANDARD_OR_UNONBOARDED`, or `FOLDER_POLICY_SCOPE`). |
| `enabled_module_count` | Count of built-in ETD detector modules currently enabled. |
| `update_time` | Last update timestamp from the Security Center Management API. |
| `configured_modules_state` | Live state of the specific built-in modules managed by this Terraform module. |
| `console_onboarding_url` | Direct Cloud Console SCC onboarding URL if `effectiveEnablementState` is not yet `ENABLED`. |
