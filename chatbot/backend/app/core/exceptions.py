from __future__ import annotations


class AuthConfigError(Exception):
    """GCP authentication could not be resolved.

    Raised by GeminiProvider._resolve_credentials() when all three ADC
    priority paths (impersonation, key file, ambient) fail.
    """
