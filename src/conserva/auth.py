"""Cryptographically verified Bearer token authentication and server-side RBAC/tenant resolution for CONSERVA.

Replaces untrusted caller-supplied headers with:
- HMAC-SHA256 signed tokens bound to a stable subject (`sub`) and expiration (`exp`).
- Server-side principal registry resolving role and allowed tenant memberships (never trusting client claims).
- Default-deny enforcement for anonymous, expired, tampered, unknown, or cross-tenant requests.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass

from conserva.models import Role


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    subject: str
    display_name: str
    role: Role
    allowed_orgs: frozenset[str]
    active: bool = True

    def can_access_org(self, org_id: str) -> bool:
        return self.role == Role.ADMIN or org_id in self.allowed_orgs

    def can_write(self) -> bool:
        return self.role in {Role.ADMIN, Role.AUDITOR, Role.RISK_OWNER}


class AuthError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class ConservaAuthService:
    """Issues and verifies HMAC-SHA256 signed session tokens resolved strictly against server-side principals."""

    def __init__(self, secret_key: str | None = None, principals: dict[str, AuthenticatedPrincipal] | None = None) -> None:
        raw_secret = secret_key or os.getenv("CONSERVA_TOKEN_SECRET") or secrets.token_hex(32)
        self._secret = raw_secret.encode("utf-8")
        self._principals: dict[str, AuthenticatedPrincipal] = dict(principals or self._default_principals())

    @staticmethod
    def _default_principals() -> dict[str, AuthenticatedPrincipal]:
        return {
            "sub-admin-01": AuthenticatedPrincipal(
                subject="sub-admin-01",
                display_name="Platform GRC Administrator",
                role=Role.ADMIN,
                allowed_orgs=frozenset({"maison-valmont", "atlaspath-lab", "fondation-alqarawiyyin", "observatoire-meridien"}),
            ),
            "sub-valmont-auditor": AuthenticatedPrincipal(
                subject="sub-valmont-auditor",
                display_name="Valmont Internal Auditor",
                role=Role.AUDITOR,
                allowed_orgs=frozenset({"maison-valmont"}),
            ),
            "sub-valmont-viewer": AuthenticatedPrincipal(
                subject="sub-valmont-viewer",
                display_name="Valmont Read-Only Viewer",
                role=Role.VIEWER,
                allowed_orgs=frozenset({"maison-valmont"}),
            ),
            "sub-atlaspath-risk": AuthenticatedPrincipal(
                subject="sub-atlaspath-risk",
                display_name="AtlasPath Risk Owner",
                role=Role.RISK_OWNER,
                allowed_orgs=frozenset({"atlaspath-lab"}),
            ),
        }

    def register_principal(self, principal: AuthenticatedPrincipal) -> None:
        self._principals[principal.subject] = principal

    @staticmethod
    def _b64u_encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    @staticmethod
    def _b64u_decode(seg: str) -> bytes:
        pad = "=" * (-len(seg) % 4)
        return base64.urlsafe_b64decode(seg + pad)

    def issue_token(self, subject: str, ttl_seconds: int = 1800) -> str:
        if subject not in self._principals:
            raise KeyError(f"Unknown principal subject: {subject}")
        now = int(time.time())
        header = self._b64u_encode(json.dumps({"alg": "HS256", "typ": "CONSERVA-SESSION"}).encode("utf-8"))
        payload = self._b64u_encode(
            json.dumps({"sub": subject, "iat": now, "exp": now + ttl_seconds, "jti": secrets.token_hex(8)}).encode("utf-8")
        )
        signing_input = f"{header}.{payload}".encode("ascii")
        sig = self._b64u_encode(hmac.new(self._secret, signing_input, hashlib.sha256).digest())
        return f"{header}.{payload}.{sig}"

    def verify_bearer_header(self, authorization: str | None) -> AuthenticatedPrincipal:
        if not authorization or not authorization.startswith("Bearer "):
            raise AuthError(401, "Missing or malformed Bearer authentication token.")
        token = authorization.split(" ", 1)[1].strip()
        parts = token.split(".")
        if len(parts) != 3:
            raise AuthError(401, "Malformed session token.")
        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected_sig = self._b64u_encode(hmac.new(self._secret, signing_input, hashlib.sha256).digest())
        if not hmac.compare_digest(sig_b64, expected_sig):
            raise AuthError(401, "Invalid session token signature.")
        try:
            claims = json.loads(self._b64u_decode(payload_b64))
        except Exception as exc:
            raise AuthError(401, f"Unreadable session token payload: {exc}") from exc

        exp = claims.get("exp")
        sub = claims.get("sub")
        if not isinstance(exp, int) or time.time() > exp:
            raise AuthError(401, "Session token expired.")
        if not isinstance(sub, str) or sub not in self._principals:
            raise AuthError(401, "Authenticated subject not found in server principal registry.")

        principal = self._principals[sub]
        if not principal.active:
            raise AuthError(403, "Principal account is deactivated.")
        return principal
