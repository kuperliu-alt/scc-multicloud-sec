# SCC 多云安全与事件威胁检测 (ETD) 车队级自动化工具包 (`scc-multicloud-sec`)

一个基于 **100% Public GA 公开 API** 构建的模块化、生产就绪 **Google Cloud Security Command Center (SCC)** 与 **Event Threat Detection (ETD)** 跨项目、文件夹及组织级规模化自动化工具包。

---

## 🌟 核心能力

1. **SCC 与 ETD 车队级管理 CLI (`scripts/scc_etd_fleet_manager.py`)**：
   - **车队级层级资格与 ETD 状态巡检 (`audit`)**：自动发现指定文件夹（Folder）下的所有活跃项目（或指定项目列表），调用官方 Public GA 的 `securityCenterServices/event-threat-detection` 接口（`securitycentermanagement.googleapis.com/v1`），实时核查 `effectiveEnablementState`（`ENABLED` vs `DISABLED`）、层级资格状态（`PREMIUM_OR_ENTERPRISE` vs `STANDARD_OR_UNONBOARDED`）及已启用的内置检测器数量（152+ 内置检测模块）。
   - **前置 API 批量自动化启用 (`prepare`)**：批量为目标项目或文件夹下所有活跃项目启用 SCC 前置 API（`securitycentermanagement.googleapis.com`、`securitycenter.googleapis.com`、`cloudresourcemanager.googleapis.com`）。
   - **内置 ETD 服务与检测器模块配置 (`configure-etd`)**：支持在 `organizations/*`、`folders/*` 或 `projects/*` 任意层级设置 `intendedEnablementState`（`ENABLED`、`DISABLED`、`INHERITED`）及单个内置检测器模块覆盖策略，并原生支持 `--validate-only` 无损预检。

2. **内置 ETD 服务与模块 Terraform 模块 (`terraform/modules/scc-etd-service`)**：
   - 填补 `hashicorp/google`（截至 `<= v8.5.0` 仅支持 ETD *自定义*模块）的功能空白，通过封装 **100% Public GA 的 Security Center Management API v1**（`securityCenterServices/event-threat-detection`）并结合 `data "http"` 实现实时状态回读与配置漂移检测。
   - 同时支持直接调用 `REST_API`（带 `updateMask=intendedEnablementState,modules` 的 `PATCH` 请求）与非交互式 `GCLOUD_CLI`（`gcloud scc manage services update event-threat-detection --quiet`）两种执行引擎。

3. **实测技术验证报告与架构指南 (`docs/SCC_ETD_OPEN_QUESTIONS_CHN.md`)**：
   - 详尽记录项目级 SCC Premium 层级激活的架构原因与公开状态巡检方案、Terraform 内置 ETD 模块自动化方案，以及无 Organization 级权限下基于 Folder/Project 的三种规模化落地范式。

---

## 📂 目录结构

```text
scc-multicloud-sec/
├── docs/                                      # 实测技术验证报告与架构方案指南
│   ├── SCC_ETD_OPEN_QUESTIONS.md              # SCC 与 ETD Q1-Q3 根因分析与解决方案 (英文)
│   └── SCC_ETD_OPEN_QUESTIONS_CHN.md          # SCC 与 ETD Q1-Q3 根因分析与解决方案 (中文)
├── scripts/                                   # SCC/ETD 车队级自动化 CLI 工具
│   └── scc_etd_fleet_manager.py               # 车队级 SCC 层级巡检、预配置与 ETD 管理 CLI
├── terraform/                                 # 可复用 Terraform 模块与多项目示例
│   ├── examples/
│   │   └── project-and-folder-etd/            # 文件夹级策略继承 + 项目群 ETD 编排示例
│   │       ├── main.tf
│   │       ├── README.md
│   │       └── README_CHN.md
│   └── modules/
│       └── scc-etd-service/                   # 内置 ETD 服务与检测器模块 Terraform 模块
│           ├── main.tf
│           ├── outputs.tf
│           ├── README.md
│           ├── README_CHN.md
│           ├── variables.tf
│           └── versions.tf
├── tests/                                     # 自动化单元测试套件
│   └── test_scc_etd_fleet_manager.py          # 针对请求构建、状态巡检与 CLI 逻辑的单元测试
├── README.md                                  # 项目根文档 (英文)
└── README_CHN.md                              # 项目根文档 (中文 1:1 双向同步)
```

---

## 🚀 快速启动指南

### 1. 巡检文件夹（Folder）或项目群的 SCC 层级资格与 ETD 生效状态
```bash
# 巡检指定项目列表
python3 scripts/scc_etd_fleet_manager.py audit --projects <PROJECT_ID_1>,<PROJECT_ID_2>

# 自动发现并巡检指定 GCP 文件夹下的所有活跃项目
python3 scripts/scc_etd_fleet_manager.py audit --folder <FOLDER_ID> --expand-folder-projects
```

### 2. 项目群 SCC 激活前置准备（批量启用前置 API）
```bash
python3 scripts/scc_etd_fleet_manager.py prepare --folder <FOLDER_ID>
```

### 3. 配置内置 ETD 服务与检测器模块（支持 Folder 或 Project 作用域）
```bash
# 在文件夹（Folder）层级一次性启用 ETD（自动级联生效至所有状态为 INHERITED 的子项目）
python3 scripts/scc_etd_fleet_manager.py configure-etd \
  --scope folders/<FOLDER_ID> \
  --state ENABLED \
  --enable-modules PERSISTENCE_IAM_ANOMALOUS_GRANT,MALWARE_BAD_DOMAIN,CRYPTOMINING_POOL_DOMAIN

# 针对单个项目执行无损 Dry-Run 预检校验 (--validate-only)
python3 scripts/scc_etd_fleet_manager.py configure-etd \
  --scope projects/<PROJECT_ID> \
  --state ENABLED \
  --enable-modules PERSISTENCE_IAM_ANOMALOUS_GRANT \
  --validate-only
```

### 4. 运行自动化单元测试
```bash
python3 -m unittest discover -s tests -v
```
