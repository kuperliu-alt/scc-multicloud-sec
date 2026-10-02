#!/usr/bin/env python3
"""Unit tests for scripts/scc_etd_fleet_manager.py."""

from __future__ import annotations

import os
import sys
import unittest
from unittest import mock

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
)

import scc_etd_fleet_manager as fm


class TestSccEtdFleetManager(unittest.TestCase):
  """Tests input validation, request building, and audit logic."""

  def test_validate_resource_id_valid(self) -> None:
    self.assertEqual(fm.validate_resource_id("my-project-123"), "my-project-123")
    self.assertEqual(fm.validate_resource_id("9876543210"), "9876543210")

  def test_validate_resource_id_rejects_injection(self) -> None:
    for bad_id in ["", "../etc/passwd", "proj;rm -rf /", "proj/../../x", "-bad"]:
      with self.assertRaises(ValueError):
        fm.validate_resource_id(bad_id)

  def test_validate_parent_scopes(self) -> None:
    self.assertEqual(
        fm.validate_parent("projects", "demo-proj"), "projects/demo-proj"
    )
    self.assertEqual(fm.validate_parent("folders", "123456"), "folders/123456")
    self.assertEqual(
        fm.validate_parent("organizations", "654321"), "organizations/654321"
    )
    with self.assertRaises(ValueError):
      fm.validate_parent("invalid_scope", "123")

  def test_parse_scope_path(self) -> None:
    self.assertEqual(
        fm.parse_scope_path("projects/my-proj"), ("projects", "my-proj")
    )
    self.assertEqual(
        fm.parse_scope_path("folders/12345"), ("folders", "12345")
    )
    with self.assertRaises(ValueError):
      fm.parse_scope_path("invalid-path")

  def test_validate_module_name(self) -> None:
    self.assertEqual(
        fm.validate_module_name("gke_nodeport_service_created"),
        "GKE_NODEPORT_SERVICE_CREATED",
    )
    with self.assertRaises(ValueError):
      fm.validate_module_name("bad-module-name!")

  def test_build_etd_patch_request_with_modules_and_validate_only(self) -> None:
    url, body = fm.build_etd_patch_request(
        parent="projects/example-project",
        service_name="event-threat-detection",
        enablement_state="ENABLED",
        enable_modules=["GKE_NODEPORT_SERVICE_CREATED"],
        disable_modules=["IAM_ANOMALOUS_BEHAVIOR_USER_AGENT"],
        validate_only=True,
    )
    self.assertIn(
        "https://securitycentermanagement.googleapis.com/v1/"
        "projects/example-project/locations/global/"
        "securityCenterServices/event-threat-detection?",
        url,
    )
    self.assertIn("updateMask=intendedEnablementState%2Cmodules", url)
    self.assertIn("validateOnly=true", url)
    self.assertEqual(body["intendedEnablementState"], "ENABLED")
    self.assertEqual(
        body["modules"]["GKE_NODEPORT_SERVICE_CREATED"],
        {"intendedEnablementState": "ENABLED"},
    )
    self.assertEqual(
        body["modules"]["IAM_ANOMALOUS_BEHAVIOR_USER_AGENT"],
        {"intendedEnablementState": "DISABLED"},
    )

  def test_build_etd_patch_request_folder_inheritance(self) -> None:
    url, body = fm.build_etd_patch_request(
        parent="folders/1122334455",
        service_name="event-threat-detection",
        enablement_state="ENABLED",
        enable_modules=None,
        disable_modules=None,
        validate_only=False,
    )
    self.assertEqual(
        url,
        "https://securitycentermanagement.googleapis.com/v1/"
        "folders/1122334455/locations/global/"
        "securityCenterServices/event-threat-detection?"
        "updateMask=intendedEnablementState",
    )
    self.assertEqual(
        body,
        {
            "name": (
                "folders/1122334455/locations/global/"
                "securityCenterServices/event-threat-detection"
            ),
            "intendedEnablementState": "ENABLED",
        },
    )

  @mock.patch.object(fm, "api_request")
  def test_audit_resource_standard_generates_console_url(
      self, mock_api: mock.MagicMock
  ) -> None:
    mock_api.side_effect = [
        (
            200,
            {
                "name": (
                    "projects/sample-std/locations/global/"
                    "securityCenterServices/event-threat-detection"
                ),
                "intendedEnablementState": "INHERITED",
                "effectiveEnablementState": "DISABLED",
                "modules": {
                    "GKE_NODEPORT_SERVICE_CREATED": {
                        "effectiveEnablementState": "DISABLED"
                    }
                },
            },
        ),
    ]
    res = fm.audit_resource("projects", "sample-std", token="fake-token")
    self.assertEqual(res.tier_eligibility, "STANDARD_OR_UNONBOARDED")
    self.assertEqual(res.etd_effective_state, "DISABLED")
    self.assertEqual(
        res.console_onboarding_url,
        "https://console.cloud.google.com/security/command-center/"
        "onboarding?project=sample-std",
    )

  @mock.patch.object(fm, "api_request")
  def test_audit_resource_premium_no_console_url_needed(
      self, mock_api: mock.MagicMock
  ) -> None:
    mock_api.side_effect = [
        (
            200,
            {
                "name": (
                    "projects/sample-prem/locations/global/"
                    "securityCenterServices/event-threat-detection"
                ),
                "intendedEnablementState": "INHERITED",
                "effectiveEnablementState": "ENABLED",
                "modules": {
                    "GKE_NODEPORT_SERVICE_CREATED": {
                        "effectiveEnablementState": "ENABLED"
                    },
                    "WORKSPACE_STRONG_AUTHENTICATION_DISABLED": {
                        "effectiveEnablementState": "DISABLED"
                    },
                },
            },
        ),
    ]
    res = fm.audit_resource("projects", "sample-prem", token="fake-token")
    self.assertEqual(res.tier_eligibility, "PREMIUM_OR_ENTERPRISE")
    self.assertIsNone(res.console_onboarding_url)
    self.assertEqual(res.etd_enabled_modules_count, 1)
    self.assertEqual(res.etd_disabled_modules_count, 1)


if __name__ == "__main__":
  unittest.main()
