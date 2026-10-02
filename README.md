# SCC Multi-Cloud Security & ETD Fleet Automation (`scc-multicloud-sec`)

A modular, production-ready toolkit and workspace for automating **Google Cloud Security Command Center (SCC)** and **Event Threat Detection (ETD)** at project, folder, and organization fleet scale, with built-in Google Cloud session isolation and Multi-Agent governance.

---

## 🌟 Key Capabilities

1. **SCC & ETD Fleet Manager CLI (`scripts/scc_etd_fleet_manager.py`)**:
   - **Fleet Tier & ETD Audit (`audit`)**: Discovers all active projects in a Folder (or explicit project list) and queries the public `billingMetadata`, `securityCenterSettings`, and `securityCenterServices/event-threat-detection` APIs to inspect `billingTier` (`PREMIUM` vs `STANDARD`), onboarding timestamps, service accounts, and enabled detector counts (152+ built-in modules).
   - **Automated Pre-Flight Preparation (`prepare`)**: Batch-enables prerequisite SCC APIs (`securitycentermanagement.googleapis.com`, `securitycenter.googleapis.com`, `cloudresourcemanager.googleapis.com`), pre-creates project service identities (`service-<PROJECT_NUMBER>@security-center-api.iam.gserviceaccount.com`), and generates targeted 1-click Console onboarding deep-links (`https://console.cloud.google.com/security/command-center/onboarding?project=<PROJECT_ID>`) only for un-flipped projects.
   - **Built-in ETD Service & Module Configuration (`configure-etd`)**: Configures `intendedEnablementState` (`ENABLED`, `DISABLED`, `INHERITED`) and individual built-in detector module overrides across `organizations/*`, `folders/*`, or `projects/*` with `--validate-only` dry-run support.

2. **Terraform Module for Built-in ETD Service & Modules (`terraform/modules/scc-etd-service`)**:
   - Bridges the gap in `hashicorp/google` (`<= v8.5.0`, which only supports ETD *custom* modules) by wrapping the **Public GA Security Center Management API v1** (`securityCenterServices/event-threat-detection`) with live `data "http"` state readback and drift detection.
   - Supports both direct `REST_API` (`PATCH` with `updateMask=intendedEnablementState,modules`) and non-interactive `GCLOUD_CLI` (`gcloud scc manage services update event-threat-detection --quiet`) execution modes.

3. **Verified Technical Architecture & Q&A Guide (`docs/SCC_ETD_OPEN_QUESTIONS.md`)**:
   - Comprehensive root-cause analysis and live verification logs for Project-level SCC Premium tier activation (`PANTHEON` API visibility vs public inspection endpoints), Terraform ETD built-in module automation, and Folder/Project-scoped fleet patterns without Org-level IAM ownership.

4. **Google Cloud Session-Level Isolation & Multi-Agent Governance**:
   - Isolates `gcloud` configuration and authentication state inside `.gcloud/` (`CLOUDSDK_CONFIG`).
   - Enforces 1:1 bilingual documentation (`*.md` and `*_CHN.md`), `tmp/` scratch script isolation, automated unit testing, and zero hardcoded secrets per `.agents/AGENTS.md`.

---

## 📂 Directory Layout

```text
scc-multicloud-sec/
├── .agents/                                   # Multi-Agent coordination rules & role definitions
│   └── AGENTS.md                              # 4-Role collaboration workflow and mandatory invariants
├── .vscode/                                   # Standardized IDE editor settings & terminal env isolation
│   └── settings.json
├── docs/                                      # Technical verification reports & architecture guides
│   ├── SCC_ETD_OPEN_QUESTIONS.md              # Verified SCC & ETD Q1-Q3 root-cause & solutions (English)
│   └── SCC_ETD_OPEN_QUESTIONS_CHN.md          # Verified SCC & ETD Q1-Q3 root-cause & solutions (Chinese)
├── scripts/                                   # Project automation & SCC/ETD fleet CLI tools
│   ├── init_project.sh                        # One-click project workspace bootstrap script
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
├── tmp/                                       # Temporary scripts, probes, and scratch sandbox (gitignored)
│   └── .gitkeep
├── .env.example                               # Example project environment variable configuration
├── .envrc                                     # Universal direnv environment loader & gcloud isolator
├── .gitignore                                 # Multi-layer security, AI-artifact, and multi-language ignore rules
├── README.md                                  # Project documentation (English)
└── README_CHN.md                              # Project documentation (Chinese, 1:1 synchronized)
```

---

## 🚀 Quick Start Guide

### 1. Audit SCC Tier & ETD Effective Status Across a Folder or Project Fleet
```bash
# Audit specific projects
python3 scripts/scc_etd_fleet_manager.py audit --projects <PROJECT_ID_1>,<PROJECT_ID_2>

# Automatically discover and audit all active projects inside a GCP Folder
python3 scripts/scc_etd_fleet_manager.py audit --folder <FOLDER_ID>
```

### 2. Prepare Projects for SCC Onboarding (Enable APIs, Provision Service Identity, Emit Onboarding Links)
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
