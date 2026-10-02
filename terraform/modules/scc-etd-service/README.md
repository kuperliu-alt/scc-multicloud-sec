# Terraform Module: SCC Event Threat Detection (ETD) Built-in Service & Modules

Because the `hashicorp/google` Terraform provider (verified through `v8.5.0`) only includes resources for ETD **custom** modules (`google_scc_management_organization_event_threat_detection_custom_module` / `google_scc_event_threat_detection_custom_module`) and does not yet implement a native resource for the built-in `SecurityCenterService` (`securityCenterServices/event-threat-detection`), this module bridges the gap using the **Public GA Security Center Management API v1**.

---

## ✨ Features

1. **Multi-Scope Support (`organizations/*`, `folders/*`, `projects/*`)**:
   - Configure `event-threat-detection` at the **Organization**, **Folder**, or **Project** level using a single `parent` variable (e.g. `folders/<FOLDER_ID>` or `projects/<PROJECT_ID>`).
2. **Built-in Service State & Per-Detector Module Overrides**:
   - Set `intended_enablement_state` (`ENABLED`, `DISABLED`, or `INHERITED`).
   - Override individual built-in ETD detector modules (e.g. `PERSISTENCE_IAM_ANOMALOUS_GRANT`, `CRYPTOMINING_POOL_DOMAIN`, `EXFILTRATION_BIGQUERY_ANOMALOUS_DATA_EGRESS`) while preserving the other ~170 built-in detectors via `updateMask=intendedEnablementState,modules`.
3. **Dual Execution Modes (`REST_API` vs `GCLOUD_CLI`)**:
   - **`REST_API` (Default, Recommended)**: Calls `PATCH https://securitycentermanagement.googleapis.com/v1/{parent}/locations/global/securityCenterServices/event-threat-detection` directly via `curl` with `--fail-with-body` and optional `?validateOnly=true`.
   - **`GCLOUD_CLI`**: Invokes `gcloud scc manage services update event-threat-detection --quiet` (the `--quiet` flag is critical in non-interactive Terraform runs because `gcloud` prompts `Do you want to continue (Y/n)?` by default).
4. **Live Drift Detection & State Readback (`data.http`)**:
   - Reads the live `securityCenterServices/event-threat-detection` resource and `billingMetadata` (for `projects/*` parents) from the Security Center Management API and exposes `effective_enablement_state`, `billing_tier`, and `enabled_module_count` as Terraform outputs.

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
| `intended_enablement_state` | Desired enablement state (`ENABLED`, `DISABLED`, `INHERITED`). | `string` | `"ENABLED"` | no |
| `modules` | Map of built-in ETD module names to desired `enablement_state` and optional `configuration`. | `map(object)` | `{}` | no |
| `execution_mode` | Execution backend (`REST_API` or `GCLOUD_CLI`). | `string` | `"REST_API"` | no |
| `validate_only` | When `true` (in `REST_API` mode), appends `&validateOnly=true` to dry-run the update. | `bool` | `false` | no |
| `reset_to_inherited_on_destroy` | When `true`, resets `intendedEnablementState` to `INHERITED` on `terraform destroy`. | `bool` | `true` | no |

---

## 📤 Outputs

| Name | Description |
| :--- | :--- |
| `service_resource_name` | Full resource name of the ETD `SecurityCenterService`. |
| `intended_enablement_state` | Live `intendedEnablementState` returned by the API. |
| `effective_enablement_state` | Live `effectiveEnablementState` returned by the API (`ENABLED` or `DISABLED`). |
| `billing_tier` | Live SCC `billingTier` (`PREMIUM` or `STANDARD`) when `parent` is `projects/*`, or `N/A`. |
| `enabled_module_count` | Count of built-in ETD detector modules currently enabled. |
| `update_time` | Last update timestamp from the Security Center Management API. |
