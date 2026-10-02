#!/usr/bin/env python3
"""Security Command Center (SCC) & Event Threat Detection (ETD) Fleet Manager.

Provides programmatic inspection, pre-activation preparation, and fleet-scale
Event Threat Detection (ETD) service/module configuration across GCP Projects,
Folders, and Organizations using the public Security Center Management API (v1)
and Security Center Settings API (v1beta2).

Key Capabilities:
1. `audit`:
   - Reads project/org SCC billing tier (`STANDARD`, `PREMIUM`, `ENTERPRISE`)
     via `GET /v1/{parent}/locations/global/billingMetadata`.
   - Reads project/org SCC onboarding status and service agent principal via
     `GET /v1beta2/{parent}/securityCenterSettings`.
   - Reads ETD built-in service and detector module enablement states via
     `GET /v1/{parent}/locations/global/securityCenterServices/event-threat-detection`.
   - Generates direct Cloud Console onboarding URLs for any project that still
     requires the Console-only (`PANTHEON` visibility) tier activation click.
2. `prepare`:
   - Enables required APIs (`securitycenter.googleapis.com` and
     `securitycentermanagement.googleapis.com`) across one or more projects or
     all active projects under a Folder.
3. `configure-etd`:
   - Programmatically updates `intendedEnablementState` (`ENABLED`, `DISABLED`,
     `INHERITED`) and built-in ETD detector modules (`modules` map) at the
     Project, Folder, or Organization level via REST `PATCH` (`v1`), with
     optional `validateOnly=true` dry-run verification.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import dataclasses
import json
import os
import re
import shutil
import subprocess
import sys
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

SCM_API_BASE = "https://securitycentermanagement.googleapis.com/v1"
SCC_SETTINGS_API_BASE = "https://securitycenter.googleapis.com/v1beta2"

VALID_RESOURCE_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,62}$")
VALID_MODULE_NAME_RE = re.compile(r"^[A-Z0-9_]{2,128}$")
VALID_SERVICE_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]{2,64}$")
VALID_ENABLEMENT_STATES = frozenset({"ENABLED", "DISABLED", "INHERITED"})
VALID_SCOPES = frozenset({"projects", "folders", "organizations"})


def validate_resource_id(resource_id: str, label: str = "resource_id") -> str:
  """Validates a GCP project ID, folder ID, or organization ID."""
  cleaned = resource_id.strip()
  if not VALID_RESOURCE_ID_RE.match(cleaned):
    raise ValueError(
        f"Invalid {label}: {resource_id!r}. Must match"
        f" {VALID_RESOURCE_ID_RE.pattern}"
    )
  return cleaned


def validate_parent(scope: str, resource_id: str) -> str:
  """Constructs and validates a canonical parent path (`projects/<id>`, etc.)."""
  if scope not in VALID_SCOPES:
    raise ValueError(
        f"Invalid scope {scope!r}. Must be one of {sorted(VALID_SCOPES)}"
    )
  valid_id = validate_resource_id(resource_id, label=scope[:-1])
  return f"{scope}/{valid_id}"


def validate_module_name(module_name: str) -> str:
  """Validates an ETD built-in module identifier."""
  cleaned = module_name.strip().upper()
  if not VALID_MODULE_NAME_RE.match(cleaned):
    raise ValueError(
        f"Invalid ETD module name: {module_name!r}. Expected uppercase"
        " identifier (e.g. GKE_NODEPORT_SERVICE_CREATED)."
    )
  return cleaned


def get_gcloud_binary() -> str:
  """Resolves the path to the `gcloud` CLI binary safely."""
  gcloud_path = shutil.which("gcloud")
  if not gcloud_path:
    raise RuntimeError("`gcloud` CLI binary not found in PATH.")
  return gcloud_path


def get_access_token() -> str:
  """Retrieves an OAuth2 access token from the environment or `gcloud`."""
  env_token = os.environ.get("GCP_ACCESS_TOKEN", "").strip()
  if env_token:
    return env_token
  gcloud_bin = get_gcloud_binary()
  env = os.environ.copy()
  env.setdefault("CLOUDSDK_METRICS_ENVIRONMENT", "datacloud.jetski")
  proc = subprocess.run(
      [gcloud_bin, "auth", "print-access-token"],
      capture_output=True,
      text=True,
      check=False,
      env=env,
  )
  if proc.returncode != 0 or not proc.stdout.strip():
    raise RuntimeError(
        "Failed to obtain access token via `gcloud auth print-access-token`:"
        f" {proc.stderr.strip()}"
    )
  return proc.stdout.strip()


def list_projects_in_folder(folder_id: str) -> list[str]:
  """Lists all ACTIVE project IDs directly under the specified GCP Folder."""
  valid_folder = validate_resource_id(folder_id, label="folder_id")
  gcloud_bin = get_gcloud_binary()
  env = os.environ.copy()
  env.setdefault("CLOUDSDK_METRICS_ENVIRONMENT", "datacloud.jetski")
  filter_expr = (
      f"parent.id={valid_folder} AND parent.type=folder AND"
      " lifecycleState=ACTIVE"
  )
  proc = subprocess.run(
      [
          gcloud_bin,
          "projects",
          "list",
          f"--filter={filter_expr}",
          "--format=value(projectId)",
      ],
      capture_output=True,
      text=True,
      check=False,
      env=env,
  )
  if proc.returncode != 0:
    raise RuntimeError(
        f"Failed to list projects in folder {valid_folder}:"
        f" {proc.stderr.strip()}"
    )
  projects = [
      validate_resource_id(line, "project_id")
      for line in proc.stdout.splitlines()
      if line.strip()
  ]
  return sorted(projects)


def api_request(
    method: str,
    url: str,
    token: str,
    quota_project: str | None = None,
    payload: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
  """Executes an HTTPS JSON request against a Google Cloud API endpoint."""
  if not url.startswith("https://"):
    raise ValueError(f"Only https:// URLs are permitted, got: {url!r}")
  headers = {
      "Authorization": f"Bearer {token}",
      "Accept": "application/json",
  }
  if quota_project:
    headers["X-Goog-User-Project"] = validate_resource_id(
        quota_project, label="quota_project"
    )
  body_bytes = None
  if payload is not None:
    headers["Content-Type"] = "application/json; charset=utf-8"
    body_bytes = json.dumps(payload).encode("utf-8")

  req = urllib.request.Request(
      url=url, data=body_bytes, headers=headers, method=method
  )
  try:
    with urllib.request.urlopen(req, timeout=30) as resp:
      raw = resp.read().decode("utf-8")
      return resp.status, json.loads(raw) if raw else {}
  except urllib.error.HTTPError as err:
    raw = err.read().decode("utf-8", errors="replace")
    try:
      parsed = json.loads(raw)
    except json.JSONDecodeError:
      parsed = {"error": {"code": err.code, "message": raw}}
    return err.code, parsed


@dataclasses.dataclass
class ResourceAuditResult:
  """Structured SCC & ETD audit result for a single resource."""

  parent: str
  billing_tier: str
  onboarded: bool
  onboarding_time: str | None
  service_account: str | None
  etd_intended_state: str
  etd_effective_state: str
  etd_enabled_modules_count: int
  etd_disabled_modules_count: int
  console_onboarding_url: str | None
  notes: list[str] = dataclasses.field(default_factory=list)

  def to_dict(self) -> dict[str, Any]:
    return dataclasses.asdict(self)


def audit_resource(
    scope: str,
    resource_id: str,
    token: str,
    quota_project: str | None = None,
) -> ResourceAuditResult:
  """Audits SCC billing tier, onboarding status, and ETD service configuration."""
  parent = validate_parent(scope, resource_id)
  effective_quota_project = quota_project or (
      resource_id if scope == "projects" else None
  )
  notes: list[str] = []

  # 1. Query BillingMetadata (supported on projects and organizations)
  billing_tier = "N/A (FOLDER_INHERITED)"
  if scope in ("projects", "organizations"):
    bm_url = f"{SCM_API_BASE}/{parent}/locations/global/billingMetadata"
    bm_status, bm_data = api_request(
        "GET", bm_url, token, quota_project=effective_quota_project
    )
    if bm_status == 200:
      billing_tier = bm_data.get("billingTier", "UNKNOWN")
    else:
      err_msg = bm_data.get("error", {}).get("message", f"HTTP {bm_status}")
      billing_tier = f"ERROR ({bm_status})"
      notes.append(f"billingMetadata: {err_msg}")

  # 2. Query v1beta2 SecurityCenterSettings
  onboarded = False
  onboarding_time = None
  service_account = None
  scs_url = f"{SCC_SETTINGS_API_BASE}/{parent}/securityCenterSettings"
  scs_status, scs_data = api_request(
      "GET", scs_url, token, quota_project=effective_quota_project
  )
  if scs_status == 200:
    onboarding_time = scs_data.get("onboardingTime")
    service_account = scs_data.get("orgServiceAccount")
    onboarded = bool(onboarding_time or service_account)

  # 3. Query v1 SecurityCenterServices for event-threat-detection
  etd_url = (
      f"{SCM_API_BASE}/{parent}/locations/global/"
      "securityCenterServices/event-threat-detection"
  )
  etd_status, etd_data = api_request(
      "GET", etd_url, token, quota_project=effective_quota_project
  )
  etd_intended = "UNKNOWN"
  etd_effective = "UNKNOWN"
  enabled_count = 0
  disabled_count = 0
  if etd_status == 200:
    etd_intended = etd_data.get("intendedEnablementState", "UNSPECIFIED")
    etd_effective = etd_data.get("effectiveEnablementState", "UNSPECIFIED")
    modules = etd_data.get("modules", {})
    for mod_cfg in modules.values():
      eff = mod_cfg.get(
          "effectiveEnablementState", mod_cfg.get("intendedEnablementState")
      )
      if eff == "ENABLED":
        enabled_count += 1
      elif eff == "DISABLED":
        disabled_count += 1
  else:
    err_msg = etd_data.get("error", {}).get("message", f"HTTP {etd_status}")
    notes.append(f"event-threat-detection: {err_msg}")

  console_url = None
  if scope == "projects" and billing_tier not in ("PREMIUM", "ENTERPRISE"):
    console_url = (
        "https://console.cloud.google.com/security/command-center/"
        f"onboarding?project={resource_id}"
    )
    notes.append(
        "Project tier is not PREMIUM; activate via Console deep-link"
        " (PANTHEON-restricted RPC)."
    )

  return ResourceAuditResult(
      parent=parent,
      billing_tier=billing_tier,
      onboarded=onboarded,
      onboarding_time=onboarding_time,
      service_account=service_account,
      etd_intended_state=etd_intended,
      etd_effective_state=etd_effective,
      etd_enabled_modules_count=enabled_count,
      etd_disabled_modules_count=disabled_count,
      console_onboarding_url=console_url,
      notes=notes,
  )


def build_etd_patch_request(
    parent: str,
    service_name: str = "event-threat-detection",
    enablement_state: str | None = "ENABLED",
    enable_modules: list[str] | None = None,
    disable_modules: list[str] | None = None,
    raw_modules: dict[str, Any] | None = None,
    validate_only: bool = False,
) -> tuple[str, dict[str, Any]]:
  """Builds the REST PATCH URL and body for `SecurityCenterServices.Patch`."""
  if not VALID_SERVICE_NAME_RE.match(service_name):
    raise ValueError(f"Invalid service name: {service_name!r}")

  resource_name = (
      f"{parent}/locations/global/securityCenterServices/{service_name}"
  )
  body: dict[str, Any] = {"name": resource_name}
  update_mask_paths: list[str] = []

  if enablement_state is not None:
    upper_state = enablement_state.strip().upper()
    if upper_state not in VALID_ENABLEMENT_STATES:
      raise ValueError(
          f"Invalid enablement_state {enablement_state!r}. Must be one of"
          f" {sorted(VALID_ENABLEMENT_STATES)}"
      )
    body["intendedEnablementState"] = upper_state
    update_mask_paths.append("intendedEnablementState")

  modules_payload: dict[str, dict[str, str]] = {}
  if raw_modules:
    for mod_name, mod_cfg in raw_modules.items():
      valid_mod = validate_module_name(mod_name)
      if isinstance(mod_cfg, dict):
        mod_state = (
            mod_cfg.get("intendedEnablementState")
            or mod_cfg.get("enablementState")
            or "ENABLED"
        )
      else:
        mod_state = str(mod_cfg)
      mod_state_upper = mod_state.strip().upper()
      if mod_state_upper not in VALID_ENABLEMENT_STATES:
        raise ValueError(
            f"Invalid module state {mod_state!r} for {valid_mod}."
        )
      modules_payload[valid_mod] = {"intendedEnablementState": mod_state_upper}

  for mod in enable_modules or []:
    valid_mod = validate_module_name(mod)
    modules_payload[valid_mod] = {"intendedEnablementState": "ENABLED"}

  for mod in disable_modules or []:
    valid_mod = validate_module_name(mod)
    modules_payload[valid_mod] = {"intendedEnablementState": "DISABLED"}

  if modules_payload:
    body["modules"] = modules_payload
    update_mask_paths.append("modules")

  if not update_mask_paths:
    raise ValueError(
        "At least one of enablement_state or module configurations must be"
        " specified."
    )

  query_params: dict[str, str] = {"updateMask": ",".join(update_mask_paths)}
  if validate_only:
    query_params["validateOnly"] = "true"

  encoded_query = urllib.parse.urlencode(query_params)
  url = f"{SCM_API_BASE}/{resource_name}?{encoded_query}"
  return url, body


def configure_etd_service(
    scope: str,
    resource_id: str,
    token: str,
    service_name: str = "event-threat-detection",
    enablement_state: str | None = "ENABLED",
    enable_modules: list[str] | None = None,
    disable_modules: list[str] | None = None,
    raw_modules: dict[str, Any] | None = None,
    validate_only: bool = False,
    quota_project: str | None = None,
) -> dict[str, Any]:
  """Applies an ETD service/module configuration via Security Center Management API."""
  parent = validate_parent(scope, resource_id)
  effective_quota_project = quota_project or (
      resource_id if scope == "projects" else None
  )
  url, body = build_etd_patch_request(
      parent=parent,
      service_name=service_name,
      enablement_state=enablement_state,
      enable_modules=enable_modules,
      disable_modules=disable_modules,
      raw_modules=raw_modules,
      validate_only=validate_only,
  )
  status_code, resp_data = api_request(
      "PATCH",
      url,
      token=token,
      quota_project=effective_quota_project,
      payload=body,
  )
  if status_code != 200:
    raise RuntimeError(
        f"Failed to update {parent} ({status_code}):"
        f" {json.dumps(resp_data)}"
    )
  return {
      "parent": parent,
      "validateOnly": validate_only,
      "name": resp_data.get("name"),
      "intendedEnablementState": resp_data.get("intendedEnablementState"),
      "effectiveEnablementState": resp_data.get("effectiveEnablementState"),
      "updateTime": resp_data.get("updateTime"),
      "updatedModules": {
          k: resp_data.get("modules", {}).get(k)
          for k in body.get("modules", {})
      },
  }


def prepare_project_apis(project_id: str, dry_run: bool = False) -> dict[str, Any]:
  """Enables SCC and Security Center Management APIs on a target GCP project."""
  valid_project = validate_resource_id(project_id, "project_id")
  apis = [
      "securitycenter.googleapis.com",
      "securitycentermanagement.googleapis.com",
  ]
  cmd = [
      get_gcloud_binary(),
      "services",
      "enable",
      *apis,
      f"--project={valid_project}",
      "--quiet",
  ]
  if dry_run:
    return {"project_id": valid_project, "dry_run": True, "command": cmd}

  env = os.environ.copy()
  env.setdefault("CLOUDSDK_METRICS_ENVIRONMENT", "datacloud.jetski")
  proc = subprocess.run(
      cmd, capture_output=True, text=True, check=False, env=env
  )
  if proc.returncode != 0:
    raise RuntimeError(
        f"Failed to enable SCC APIs on {valid_project}: {proc.stderr.strip()}"
    )
  return {"project_id": valid_project, "enabled_apis": apis, "status": "OK"}


def format_audit_table(results: list[ResourceAuditResult]) -> str:
  """Renders a human-readable table of ResourceAuditResult items."""
  header = (
      f"{'RESOURCE':<36} {'BILLING_TIER':<14} {'ONBOARDED':<10} "
      f"{'ETD_INTENDED':<14} {'ETD_EFFECTIVE':<14} {'MODULES(EN/DIS)':<16}"
  )
  sep = "-" * len(header)
  lines = [header, sep]
  for r in results:
    mod_summary = f"{r.etd_enabled_modules_count}/{r.etd_disabled_modules_count}"
    lines.append(
        f"{r.parent:<36} {r.billing_tier:<14} {str(r.onboarded):<10} "
        f"{r.etd_intended_state:<14} {r.etd_effective_state:<14} {mod_summary:<16}"
    )
    if r.console_onboarding_url:
      lines.append(f"  -> Activate Premium in Console: {r.console_onboarding_url}")
    for note in r.notes:
      lines.append(f"  -> Note: {note}")
  return "\n".join(lines)


def resolve_targets(args: argparse.Namespace) -> list[tuple[str, str]]:
  """Resolves CLI scope arguments into a list of (scope, resource_id) tuples."""
  targets: list[tuple[str, str]] = []
  if getattr(args, "organization", None):
    targets.append(
        ("organizations", validate_resource_id(args.organization, "org_id"))
    )
  if getattr(args, "folder", None):
    valid_folder = validate_resource_id(args.folder, "folder_id")
    if getattr(args, "include_folder", True):
      targets.append(("folders", valid_folder))
    if getattr(args, "expand_folder_projects", False):
      for pid in list_projects_in_folder(valid_folder):
        targets.append(("projects", pid))
  if getattr(args, "project", None):
    targets.append(("projects", validate_resource_id(args.project, "project_id")))
  if getattr(args, "projects", None):
    for raw_pid in args.projects.split(","):
      if raw_pid.strip():
        targets.append(("projects", validate_resource_id(raw_pid, "project_id")))
  if not targets:
    raise ValueError(
        "Specify at least one target via --project, --projects, --folder, or"
        " --organization."
    )
  return targets


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
  """Parses command-line arguments."""
  parser = argparse.ArgumentParser(
      description=(
          "SCC & Event Threat Detection (ETD) Fleet Manager for Project,"
          " Folder, and Organization scopes."
      )
  )
  subparsers = parser.add_subparsers(dest="command", required=True)

  # 1. `audit` subcommand
  audit_p = subparsers.add_parser(
      "audit",
      help="Audit SCC billing tier, onboarding status, and ETD service state.",
  )
  audit_p.add_argument("--project", help="Single GCP Project ID or Number.")
  audit_p.add_argument(
      "--projects", help="Comma-separated list of GCP Project IDs."
  )
  audit_p.add_argument("--folder", help="GCP Folder ID.")
  audit_p.add_argument(
      "--expand-folder-projects",
      action="store_true",
      help="Also audit all ACTIVE child projects inside --folder.",
  )
  audit_p.add_argument("--organization", help="GCP Organization ID.")
  audit_p.add_argument(
      "--quota-project",
      help="Optional quota/billing project ID for X-Goog-User-Project header.",
  )
  audit_p.add_argument(
      "--json", action="store_true", help="Output audit report as JSON."
  )

  # 2. `prepare` subcommand
  prep_p = subparsers.add_parser(
      "prepare",
      help="Enable required SCC & Management APIs across target project(s).",
  )
  prep_p.add_argument("--project", help="Single GCP Project ID.")
  prep_p.add_argument(
      "--projects", help="Comma-separated list of GCP Project IDs."
  )
  prep_p.add_argument(
      "--folder", help="Discover and prepare all ACTIVE projects in Folder ID."
  )
  prep_p.add_argument(
      "--dry-run", action="store_true", help="Print gcloud commands only."
  )

  # 3. `configure-etd` subcommand
  cfg_p = subparsers.add_parser(
      "configure-etd",
      help=(
          "Enable/disable built-in ETD service and detector modules at"
          " Project, Folder, or Organization scope."
      ),
  )
  cfg_p.add_argument("--project", help="Target GCP Project ID or Number.")
  cfg_p.add_argument(
      "--projects", help="Comma-separated list of GCP Project IDs."
  )
  cfg_p.add_argument("--folder", help="Target GCP Folder ID.")
  cfg_p.add_argument(
      "--expand-folder-projects",
      action="store_true",
      help="Apply configuration to all ACTIVE child projects under --folder.",
  )
  cfg_p.add_argument("--organization", help="Target GCP Organization ID.")
  cfg_p.add_argument(
      "--service",
      default="event-threat-detection",
      help="SCC Service ID (default: event-threat-detection).",
  )
  cfg_p.add_argument(
      "--enablement-state",
      choices=["ENABLED", "DISABLED", "INHERITED"],
      default="ENABLED",
      help="Intended service enablement state (default: ENABLED).",
  )
  cfg_p.add_argument(
      "--enable-modules",
      help=(
          "Comma-separated list of built-in ETD module names to set to ENABLED"
          " (e.g. GKE_NODEPORT_SERVICE_CREATED,MALWARE_BAD_DOMAIN)."
      ),
  )
  cfg_p.add_argument(
      "--disable-modules",
      help=(
          "Comma-separated list of built-in ETD module names to set to"
          " DISABLED."
      ),
  )
  cfg_p.add_argument(
      "--module-config-file",
      help="Path to a JSON file containing a map of module settings.",
  )
  cfg_p.add_argument(
      "--validate-only",
      action="store_true",
      help="Validate the PATCH request with the API without persisting changes.",
  )
  cfg_p.add_argument(
      "--quota-project",
      help="Optional quota/billing project ID for X-Goog-User-Project header.",
  )

  return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
  args = parse_args(argv)

  if args.command == "prepare":
    args.include_folder = False
    args.expand_folder_projects = bool(args.folder)
    targets = resolve_targets(args)
    results = []
    for scope, rid in targets:
      if scope != "projects":
        continue
      results.append(prepare_project_apis(rid, dry_run=args.dry_run))
    print(json.dumps(results, indent=2))
    return 0

  token = get_access_token()

  if args.command == "audit":
    args.include_folder = True
    targets = resolve_targets(args)
    audit_results: list[ResourceAuditResult] = []
    with ThreadPoolExecutor(max_workers=min(8, len(targets))) as pool:
      fut_map = {
          pool.submit(
              audit_resource, scope, rid, token, args.quota_project
          ): (scope, rid)
          for scope, rid in targets
      }
      for fut in as_completed(fut_map):
        audit_results.append(fut.result())
    audit_results.sort(key=lambda r: r.parent)
    if args.json:
      print(json.dumps([r.to_dict() for r in audit_results], indent=2))
    else:
      print(format_audit_table(audit_results))
    return 0

  if args.command == "configure-etd":
    args.include_folder = not args.expand_folder_projects
    targets = resolve_targets(args)
    raw_modules = None
    if args.module_config_file:
      with open(args.module_config_file, "r", encoding="utf-8") as fh:
        loaded = json.load(fh)
        raw_modules = loaded.get("modules", loaded)
    en_mods = (
        [m.strip() for m in args.enable_modules.split(",") if m.strip()]
        if args.enable_modules
        else None
    )
    dis_mods = (
        [m.strip() for m in args.disable_modules.split(",") if m.strip()]
        if args.disable_modules
        else None
    )
    outputs = []
    for scope, rid in targets:
      res = configure_etd_service(
          scope=scope,
          resource_id=rid,
          token=token,
          service_name=args.service,
          enablement_state=args.enablement_state,
          enable_modules=en_mods,
          disable_modules=dis_mods,
          raw_modules=raw_modules,
          validate_only=args.validate_only,
          quota_project=args.quota_project,
      )
      outputs.append(res)
    print(json.dumps(outputs, indent=2))
    return 0

  return 1


if __name__ == "__main__":
  sys.exit(main())
