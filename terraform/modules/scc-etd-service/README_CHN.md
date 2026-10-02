# Terraform 模块：SCC 事件威胁检测 (ETD) 内置服务与模块管理

由于 `hashicorp/google` Terraform Provider（已核查至 `v8.5.0`）目前仅提供 ETD **自定义模块**资源（`google_scc_management_organization_event_threat_detection_custom_module` / `google_scc_event_threat_detection_custom_module`），尚未提供用于管理内置 `SecurityCenterService`（`securityCenterServices/event-threat-detection`）的原生资源，本模块基于 **Public GA 的 Security Center Management API v1** 填补了这一空白。

---

## ✨ 核心特性

1. **多层级作用域支持（`organizations/*`, `folders/*`, `projects/*`）**：
   - 通过单一 `parent` 变量（例如 `folders/<FOLDER_ID>` 或 `projects/<PROJECT_ID>`），即可在 **组织（Organization）**、**文件夹（Folder）** 或 **项目（Project）** 层级配置 `event-threat-detection`。
2. **内置服务启用状态与单检测器模块精准覆盖**：
   - 支持设置 `intended_enablement_state`（`ENABLED`、`DISABLED` 或 `INHERITED`）。
   - 支持通过 `updateMask=intendedEnablementState,modules` 针对指定内置检测器模块（如 `PERSISTENCE_IAM_ANOMALOUS_GRANT`、`CRYPTOMINING_POOL_DOMAIN`、`EXFILTRATION_BIGQUERY_ANOMALOUS_DATA_EGRESS`）进行状态覆盖，同时无损保留其余约 170 个内置检测器的默认状态。
3. **双执行引擎模式（`REST_API` vs `GCLOUD_CLI`）**：
   - **`REST_API`（默认，推荐）**：通过 `curl --fail-with-body` 直接调用 `PATCH https://securitycentermanagement.googleapis.com/v1/{parent}/locations/global/securityCenterServices/event-threat-detection`，并支持 `?validateOnly=true` 预检。
   - **`GCLOUD_CLI`**：调用 `gcloud scc manage services update event-threat-detection --quiet`（在非交互式 Terraform 运行中必须附加 `--quiet` 参数，否则 `gcloud` 默认会弹出 `Do you want to continue (Y/n)?` 导致流水线挂起）。
4. **实时状态回读与漂移检测（`data.http`）**：
   - 自动从 Security Center Management API 读取 `securityCenterServices/event-threat-detection` 实时状态及项目级 `billingMetadata`，并将 `effective_enablement_state`、`billing_tier` 和 `enabled_module_count` 作为 Terraform Outputs 输出。

---

## 🚀 使用示例

### 文件夹级（Folder-Level）ETD 启用（自动级联继承至子项目）
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

### 项目级（Project-Level）ETD 启用
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

## 📋 输入变量 (Inputs)

| 变量名 | 说明 | 类型 | 默认值 | 必填 |
| :--- | :--- | :--- | :--- | :---: |
| `parent` | 资源层级父路径，格式为 `projects/<PROJECT_ID>`、`folders/<FOLDER_ID>` 或 `organizations/<ORG_ID>`。 | `string` | n/a | 是 |
| `intended_enablement_state` | 目标启用状态（`ENABLED`、`DISABLED`、`INHERITED`）。 | `string` | `"ENABLED"` | 否 |
| `modules` | 内置 ETD 模块名称到目标 `enablement_state` 及可选 `configuration` 的映射表。 | `map(object)` | `{}` | 否 |
| `execution_mode` | 执行后端（`REST_API` 或 `GCLOUD_CLI`）。 | `string` | `"REST_API"` | 否 |
| `validate_only` | 当为 `true` 时（仅限 `REST_API` 模式），附加 `&validateOnly=true` 进行 Dry-Run 校验。 | `bool` | `false` | 否 |
| `reset_to_inherited_on_destroy` | 当为 `true` 时，在 `terraform destroy` 时将 `intendedEnablementState` 重置为 `INHERITED`。 | `bool` | `true` | 否 |

---

## 📤 输出变量 (Outputs)

| 输出名 | 说明 |
| :--- | :--- |
| `service_resource_name` | ETD `SecurityCenterService` 的完整资源名称。 |
| `intended_enablement_state` | API 返回的实时 `intendedEnablementState`。 |
| `effective_enablement_state` | API 返回的实时 `effectiveEnablementState`（`ENABLED` 或 `DISABLED`）。 |
| `billing_tier` | 当 `parent` 为 `projects/*` 时返回的实时 SCC `billingTier`（`PREMIUM` 或 `STANDARD`），否则为 `N/A`。 |
| `enabled_module_count` | 当前处于启用状态的内置 ETD 检测器模块数量。 |
| `update_time` | Security Center Management API 返回的最后更新时间戳。 |
