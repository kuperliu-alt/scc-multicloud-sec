# 通用项目工作区与初始模版 (Universal Workspace Starter Template)

一个轻量、模块化、生产就绪的工作区初始脚手架模版，专为跨技术栈的现代软件工程开发以及多智能体（Multi-Agent）AI 结对编程设计。

---

## 🌟 核心特性

1. **多智能体协作框架 (`.agents/AGENTS.md`)**：
   - 标准化四角色分工：**Architect**（系统架构设计）、**Developer**（软件代码开发）、**QA**（质量保证与测试）、**DevOps**（运维与版本控制）。
   - 明确职责边界与结构化调度协作时序流程。

2. **硬性工程治理约束**：
   - **1:1 双语文档同步**：默认英文文档（`*.md`）与中文文档（`*_CHN.md`）保持原子性双向同步。
   - **临时脚本统一隔离**：所有一次性验证脚本、排查探针及中间产物严格隔离在 `tmp/` 目录下。
   - **质量与自测验证**：强制要求单元测试覆盖、语法检查与构建校验。
   - **规范化提交（Conventional Commits）**：统一 Git 提交规范与清晰的版本历史。

3. **通用环境与配置隔离**：
   - 通过 `.envrc` 与 `.env.example` 实现工作区级别的环境隔离与 `direnv` 自动加载。
   - 防止敏感凭据与环境变量泄露至全局 Shell 环境。

4. **多语言级 `.gitignore` 安全防护**：
   - 覆盖 AI 编程助手临时文件（`.gemini/`, `.cursor/`, `.jetski/` 等）、IDE 配置、敏感凭据，以及 Python、Node/TS、Go、Java、Rust、C/C++ 的多语言编译构建缓存。

---

## 📂 目录结构

```text
jetski-workspace-template/
├── .agents/               # Multi-Agent 协作规则与角色定义
│   └── AGENTS.md          # 四角色协作流程与硬性治理规范
├── .vscode/               # 统一的 IDE 编辑器配置
│   └── settings.json
├── scripts/               # 项目自动化与初始化脚本
│   └── init_project.sh    # 一键工作区初始化脚本
├── tmp/                   # 临时脚本、调试探针沙盒
│   └── .gitkeep
├── .env.example           # 项目环境变量配置示例
├── .envrc                 # 通用 direnv 环境加载器
├── .gitignore             # 多层安全、AI 临时产物与多语言忽略规则
├── README.md              # 项目根文档 (英文)
└── README_CHN.md          # 项目根文档 (中文 1:1 双向同步)
```

---

## 🚀 快速启动指南

### 第一步：复制模版至新项目
```bash
cp -r /path/to/jetski-workspace-template /path/to/my-new-project
cd /path/to/my-new-project
```

### 第二步：初始化工作区
```bash
chmod +x scripts/*.sh
./scripts/init_project.sh
```

### 第三步：配置环境变量
根据项目依赖和运行时需求编辑 `.env`：
```bash
nano .env  # 或在编辑器中直接打开
```
