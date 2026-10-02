# Example: Folder & Project-Fleet ETD Enablement in Terraform

This example demonstrates how teams with **Folder or Project-level access** (without Organization-level IAM ownership) can automate prerequisite API enablement, Folder-level ETD policy inheritance, per-project ETD detector overrides, and live `billingTier` / `effectiveEnablementState` auditing.

---

## 🏗️ What This Example Configures

1. **`google_project_service.scc_apis`**: Enables `securitycentermanagement.googleapis.com`, `securitycenter.googleapis.com`, and `cloudresourcemanager.googleapis.com` across every project in `var.project_ids`.
2. **`module.folder_etd_policy` (Optional)**: When `var.folder_id` is provided, configures `folders/<FOLDER_ID>/locations/global/securityCenterServices/event-threat-detection` once so all child projects with `INHERITED` state automatically receive the ETD detector configuration.
3. **`module.project_etd_service`**: Configures `projects/<PROJECT_ID>/locations/global/securityCenterServices/event-threat-detection` and reads back each project's live `billingTier` (`PREMIUM` vs `STANDARD`) and `effectiveEnablementState`. If any project has not yet completed the Console tier flip to `PREMIUM`, the output emits its direct 1-click onboarding URL.

---

## 🚀 Usage

```bash
terraform init

terraform apply \
  -var="folder_id=<FOLDER_ID>" \
  -var='project_ids=["<PROJECT_ID_1>", "<PROJECT_ID_2>"]' \
  -var="project_enablement_state=INHERITED"
```
