# SCC Multi-Cloud Security & ETD Fleet Automation (`scc-multicloud-sec`)

A modular, production-ready toolkit for automating **Google Cloud Security Command Center (SCC)** and **Event Threat Detection (ETD)** at project, folder, and organization fleet scale using **100% Public GA APIs**.

---

## 🌟 Key Capabilities

1. **SCC & ETD Fleet Manager CLI (`scripts/scc_etd_fleet_manager.py`)**:
   - **Fleet Tier Eligibility & ETD Audit (`audit`)**: Discovers all active projects in a Folder (or explicit project list) and queries the official Public GA `securityCenterServices/event-threat-detection` endpoint (`securitycentermanagement.googleapis.com/v1`) to verify `effectiveEnablementState` (`ENABLED` vs `DISABLED`), tier eligibility (`PREMIUM_OR_ENTERPRISE` vs `STANDARD_OR_UNONBOARDED`), and enabled detector counts (152+ built-in modules).
   - **Automated Pre-Flight Preparation (`prepare`)**: Batch-enables prerequisite SCC APIs (`securitycentermanagement.googleapis.com`, `securitycenter.googleapis.com`, `cloudresourcemanager.googleapis.com`) across target projects or folders.
   - **Built-in ETD Service & Module Configuration (`configure-etd`)**: Configures `intendedEnablementState` (`ENABLED`, `DISABLED`, `INHERITED`) and individual built-in detector module overrides across `organizations/*`, `folders/*`, or `projects/*` with `--validate-only` dry-run support.

2. **Terraform Module for Built-in ETD Service & Modules (`terraform/modules/scc-etd-service`)**:
   - Bridges the gap in `hashicorp/google` (`<= v8.5.0`, which only supports ETD *custom* modules) by wrapping the **100% Public GA Security Center Management API v1** (`securityCenterServices/event-threat-detection`) with live `data "http"` state readback and drift detection.
   - Supports both direct `REST_API` (`PATCH` with `updateMask=intendedEnablementState,modules`) and non-interactive `GCLOUD_CLI` (`gcloud scc manage services update event-threat-detection --quiet`) execution modes.

3. **Verified Technical Architecture & Q&A Guide (`docs/SCC_ETD_OPEN_QUESTIONS.md`)**:
   - Comprehensive root-cause analysis and live verification logs for Project-level SCC Premium tier activation, Terraform ETD built-in module automation, and Folder/Project-scoped fleet patterns without Org-level IAM ownership.

---

## 📂 Directory Layout

```text
scc-multicloud-sec/
├── docs/                                      # Technical verification reports & architecture guides
│   ├── SCC_ETD_OPEN_QUESTIONS.md              # Verified SCC & ETD Q1-Q3 root-cause & solutions (English)
│   └── SCC_ETD_OPEN_QUESTIONS_CHN.md          # Verified SCC & ETD Q1-Q3 root-cause & solutions (Chinese)
├── scripts/                                   # SCC/ETD fleet automation CLI tools
│   └── scc_etd_fleet_manager.py               # Fleet-scale SCC tier audit, pre-flight & ETD manager CLI
├── terraform/                                 # Reusable Terraform modules & fleet examples
│   ├── examples/
│   │   └── project-and-folder-etd/            # Folder policy inheritance + project fleet ETD example
│   │       ├── main.tf
│   │       ├── README.md
│   │       └── README_CHN.md
│   └── modules/
│       └── scc-etd-service/                   # Terraform module for built-in ETD service & modules
│           ├── main.tf
│           ├── outputs.tf
│           ├── README.md
│           ├── README_CHN.md
│           ├── variables.tf
│           └── versions.tf
├── tests/                                     # Automated unit test suites
│   └── test_scc_etd_fleet_manager.py          # Unit tests for payload generation, audit & CLI logic
├── README.md                                  # Project documentation (English)
└── README_CHN.md                              # Project documentation (Chinese, 1:1 synchronized)
```

---

## 🚀 Quick Start Guide

### 1. Audit SCC Tier Eligibility & ETD Effective Status Across a Folder or Project Fleet
```bash
# Audit specific projects
python3 scripts/scc_etd_fleet_manager.py audit --projects <PROJECT_ID_1>,<PROJECT_ID_2>

# Automatically discover and audit all active projects inside a GCP Folder
python3 scripts/scc_etd_fleet_manager.py audit --folder <FOLDER_ID> --expand-folder-projects
```

### 2. Prepare Projects for SCC Onboarding (Batch-Enable Prerequisite APIs)
```bash
python3 scripts/scc_etd_fleet_manager.py prepare --folder <FOLDER_ID>
```

### 3. Configure Built-in ETD Service & Detector Modules (Folder or Project Scope)
```bash
# Enable ETD once at the Folder scope (cascades automatically to child projects with INHERITED state)
python3 scripts/scc_etd_fleet_manager.py configure-etd \
  --scope folders/<FOLDER_ID> \
  --state ENABLED \
  --enable-modules PERSISTENCE_IAM_ANOMALOUS_GRANT,MALWARE_BAD_DOMAIN,CRYPTOMINING_POOL_DOMAIN

# Dry-run validation against a single project (--validate-only)
python3 scripts/scc_etd_fleet_manager.py configure-etd \
  --scope projects/<PROJECT_ID> \
  --state ENABLED \
  --enable-modules PERSISTENCE_IAM_ANOMALOUS_GRANT \
  --validate-only
```

### 4. Run Automated Unit Tests
```bash
python3 -m unittest discover -s tests -v
```
