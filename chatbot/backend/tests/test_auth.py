"""Phase 1 — GCP ADC auth unit tests for GeminiProvider._resolve_credentials()."""
from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import AuthConfigError


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_provider_uninitialized():
    """Return a GeminiProvider instance with __init__ bypassed."""
    from app.services.llm.providers.gemini_provider import GeminiProvider

    provider = object.__new__(GeminiProvider)
    return provider


# ── tests ─────────────────────────────────────────────────────────────────────


def test_impersonation_path_selected_when_env_set(monkeypatch):
    """Priority 1: GCP_IMPERSONATE_SA triggers impersonated_credentials.Credentials."""
    monkeypatch.setattr(
        "app.services.llm.providers.gemini_provider.settings",
        MagicMock(
            GCP_IMPERSONATE_SA="shared-sa@proj.iam.gserviceaccount.com",
            GOOGLE_APPLICATION_CREDENTIALS="",
        ),
    )

    fake_source = MagicMock()
    fake_impersonated = MagicMock()

    with (
        patch("google.auth.default", return_value=(fake_source, "proj")) as mock_default,
        patch(
            "google.auth.impersonated_credentials.Credentials",
            return_value=fake_impersonated,
        ) as mock_imp,
    ):
        provider = _make_provider_uninitialized()
        creds = provider._resolve_credentials()

    mock_default.assert_called_once()
    mock_imp.assert_called_once_with(
        source_credentials=fake_source,
        target_principal="shared-sa@proj.iam.gserviceaccount.com",
        target_scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    assert creds is fake_impersonated


def test_keyfile_path_selected_when_credentials_env_set(monkeypatch):
    """Priority 2: GOOGLE_APPLICATION_CREDENTIALS triggers from_service_account_file."""
    monkeypatch.setattr(
        "app.services.llm.providers.gemini_provider.settings",
        MagicMock(
            GCP_IMPERSONATE_SA="",
            GOOGLE_APPLICATION_CREDENTIALS="/tmp/sa.json",
        ),
    )

    fake_creds = MagicMock()

    with patch(
        "google.oauth2.service_account.Credentials.from_service_account_file",
        return_value=fake_creds,
    ) as mock_from_file:
        provider = _make_provider_uninitialized()
        creds = provider._resolve_credentials()

    mock_from_file.assert_called_once_with(
        "/tmp/sa.json",
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    assert creds is fake_creds


def test_ambient_adc_fallback_logs_warning(monkeypatch, capsys):
    """Priority 3: ambient ADC is used and a WARNING is emitted via structlog."""
    monkeypatch.setattr(
        "app.services.llm.providers.gemini_provider.settings",
        MagicMock(
            GCP_IMPERSONATE_SA="",
            GOOGLE_APPLICATION_CREDENTIALS="",
        ),
    )

    fake_creds = MagicMock()

    with patch("google.auth.default", return_value=(fake_creds, "proj")):
        provider = _make_provider_uninitialized()
        creds = provider._resolve_credentials()

    assert creds is fake_creds
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert "Shared SA not explicitly targeted" in output


def test_auth_config_error_raised_when_all_paths_fail(monkeypatch):
    """All three auth paths fail → AuthConfigError with remediation message."""
    import google.auth.exceptions

    monkeypatch.setattr(
        "app.services.llm.providers.gemini_provider.settings",
        MagicMock(
            GCP_IMPERSONATE_SA="",
            GOOGLE_APPLICATION_CREDENTIALS="",
        ),
    )

    with patch(
        "google.auth.default",
        side_effect=google.auth.exceptions.DefaultCredentialsError("no creds"),
    ):
        provider = _make_provider_uninitialized()
        with pytest.raises(AuthConfigError) as exc_info:
            provider._resolve_credentials()

    msg = str(exc_info.value)
    assert "gcloud auth application-default login" in msg
    assert "GCP_IMPERSONATE_SA" in msg
    assert "GOOGLE_APPLICATION_CREDENTIALS" in msg


def test_credentials_never_logged(monkeypatch, caplog):
    """Credential values (tokens, file paths beyond INFO) must not appear in logs."""
    monkeypatch.setattr(
        "app.services.llm.providers.gemini_provider.settings",
        MagicMock(
            GCP_IMPERSONATE_SA="shared-sa@proj.iam.gserviceaccount.com",
            GOOGLE_APPLICATION_CREDENTIALS="",
        ),
    )

    fake_source = MagicMock()
    fake_source.token = "SECRET_TOKEN_12345"
    fake_impersonated = MagicMock()
    fake_impersonated.token = "IMPERSONATED_TOKEN_67890"

    with (
        patch("google.auth.default", return_value=(fake_source, "proj")),
        patch(
            "google.auth.impersonated_credentials.Credentials",
            return_value=fake_impersonated,
        ),
    ):
        provider = _make_provider_uninitialized()
        with caplog.at_level(logging.DEBUG):
            provider._resolve_credentials()

    full_log = " ".join(caplog.messages)
    assert "SECRET_TOKEN_12345" not in full_log
    assert "IMPERSONATED_TOKEN_67890" not in full_log
    # The SA email in the INFO log is acceptable (it's not a secret)
    # but no token or key material should appear
