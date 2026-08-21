# Universal Workspace & Project Starter Template

A clean, modular, and production-ready workspace starter template designed for modern software development and Multi-Agent AI pair-programming across any technology stack.

---

## 🌟 Key Features

1. **Multi-Agent Coordination Framework (`.agents/AGENTS.md`)**:
   - Standardized 4-Role Division: **Architect** (Design), **Developer** (Implementation), **QA** (Testing & Verification), and **DevOps** (Git & Release).
   - Clear responsibility boundaries and structured agent dispatching workflows.

2. **Mandatory Governance Invariants**:
   - **1-to-1 Bilingual Documentation**: Default English (`*.md`) and Chinese (`*_CHN.md`) synchronized in lockstep.
   - **Scratch & Temporary Script Isolation**: All temporary verification code, debug probes, and scratch scripts are strictly isolated in `tmp/`.
   - **Quality & Test Verification**: Ensures self-testing, linting, and build verification.
   - **Conventional Commits**: Enforces standardized commit formats and clean Git hygiene.

3. **Universal Environment & Config Isolation**:
   - `.envrc` and `.env.example` provide per-workspace environment loading with `direnv` support.
   - Prevents leaking secrets or environment variables into global shells.

4. **Comprehensive Multi-Language `.gitignore`**:
   - Covers AI coding assistant artifacts (`.gemini/`, `.cursor/`, `.jetski/`, etc.), IDEs, credentials, and build caches for Python, Node/TS, Go, Java, Rust, and C/C++.

---

## 📂 Directory Layout

```text
jetski-workspace-template/
├── .agents/               # Multi-Agent coordination rules & role definitions
│   └── AGENTS.md          # 4-Role collaboration workflow and mandatory invariants
├── .vscode/               # Standardized IDE editor settings
│   └── settings.json
├── scripts/               # Project automation and bootstrap scripts
│   └── init_project.sh    # One-click project workspace bootstrap script
├── tmp/                   # Temporary scripts, probes, and scratch sandbox
│   └── .gitkeep
├── .env.example           # Example project environment variable configuration
├── .envrc                 # Universal direnv environment loader
├── .gitignore             # Multi-layer security, AI-artifact, and multi-language ignore rules
├── README.md              # Project documentation (English)
└── README_CHN.md          # Project documentation (Chinese, 1:1 synchronized)
```

---

## 🚀 Quick Start Guide

### Step 1: Copy Template to New Project
```bash
cp -r /path/to/jetski-workspace-template /path/to/my-new-project
cd /path/to/my-new-project
```

### Step 2: Initialize Workspace
```bash
chmod +x scripts/*.sh
./scripts/init_project.sh
```

### Step 3: Configure Environment
Edit `.env` as required for your project dependencies and runtime environment:
```bash
nano .env  # or open in your editor
```
