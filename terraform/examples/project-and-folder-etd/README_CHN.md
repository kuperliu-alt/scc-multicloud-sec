# 示例：基于 Terraform 的文件夹与多项目车队级 ETD 自动化配置

本示例展示仅具备 **文件夹（Folder）或项目（Project）级权限**（无组织级 Organization IAM 所有权）的团队，如何基于 **100% Public GA 公开 API** 通过 Terraform 自动化完成前置 API 启用、文件夹级 ETD 策略继承、单项目内置检测器覆盖，以及实时 `effectiveEnablementState` / 层级资格状态审计。

---

## 🏗️ 本示例包含的资源编排

1. **`module.folder_etd_policy`（可选）**：当传入 `var.folder_id` 时，在 `folders/<FOLDER_ID>/locations/global/securityCenterServices/event-threat-detection` 上一次性完成配置，使所有状态为 `INHERITED` 的子项目自动继承 ETD 检测器策略。
2. **`module.project_etd_service`**：为 `var.project_ids` 中的每个项目自动启用 `securitycenter.googleapis.com` 与 `securitycentermanagement.googleapis.com`，配置 `projects/<PROJECT_ID>/locations/global/securityCenterServices/event-threat-detection`，并实时回读每个项目的 `effectiveEnablementState` 与 `tier_eligibility`。若某个项目尚未在控制台完成 `PREMIUM` 层级激活，Outputs 会自动生成该项目的一键激活直达链接。

---

## 🚀 运行方式

```bash
terraform init

terraform apply \
  -var="folder_id=<FOLDER_ID>" \
  -var='project_ids=["<PROJECT_ID_1>", "<PROJECT_ID_2>"]' \
  -var="project_enablement_state=INHERITED"
```
