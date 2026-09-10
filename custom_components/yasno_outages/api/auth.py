"""
Authenticated login (Azure AD B2C phone/OTP) API for Yasno outages.

Reproduces the login flow used by the official YASNO mobile app: an
embedded WebView loading `login.yasno.ua` (Azure AD B2C), phone number +
SMS/Viber one-time code, no email/password.

Yasno's B2C login endpoint sits behind an Imperva WAF that performs
TLS/JA3 fingerprint-based bot detection: requests made with a plain HTTP
client (e.g. `aiohttp`, `requests`) are rejected with a generic 400 "Bad
Request" regardless of headers, cookies, or source IP, while requests made
with a real browser's TLS fingerprint succeed. This module therefore uses
`curl_cffi` (which impersonates a real Safari/iOS TLS fingerprint) for the
login flow specifically, instead of `aiohttp` used elsewhere in this
integration. This module is otherwise Home Assistant agnostic.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import re
import secrets
import uuid
from typing import TYPE_CHECKING, Literal
from urllib.parse import parse_qs, urlencode, urlparse

from curl_cffi.requests import AsyncSession

from .const import (
    AUTH_AUTHORITY,
    AUTH_CLIENT_ID,
    AUTH_IMPERSONATE,
    AUTH_MESSAGE_TYPE_SMS,
    AUTH_MESSAGE_TYPE_VIBER,
    AUTH_REDIRECT_URI,
    AUTH_SCOPE,
    AUTH_USER_AGENT,
    AUTH_VERIFICATION_CONTROL_ID,
)
from .models import AuthTokens

if TYPE_CHECKING:
    from collections.abc import Mapping

LOGGER = logging.getLogger(__name__)

_MESSAGE_TYPES = (AUTH_MESSAGE_TYPE_SMS, AUTH_MESSAGE_TYPE_VIBER)
_HTTP_OK = 200
_HTTP_BAD_REQUEST = 400
_TIMEOUT = 30


class YasnoAuthError(Exception):
    """Raised when the authenticated login flow fails."""


class YasnoAuthBlockedError(YasnoAuthError):
    """Raised when the B2C endpoint responds via an Imperva WAF block/challenge."""


def _make_pkce() -> tuple[str, str]:
    """Generate a PKCE code_verifier / code_challenge pair (S256)."""
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(40)).rstrip(b"=").decode()
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def _extract_settings(html: str) -> dict:
    """Pull the embedded `var SETTINGS = {...};` JSON blob out of the B2C page."""
    match = re.search(r"var SETTINGS = (\{.*?\});", html, re.DOTALL)
    if not match:
        msg = "Could not find SETTINGS blob in authorize page HTML"
        raise YasnoAuthError(msg)
    return json.loads(match.group(1))


def _is_imperva_block(headers: Mapping[str, str]) -> bool:
    """Detect an Imperva WAF block/challenge page (vs. a real B2C error)."""
    return "imperva" in headers.get("X-CDN", "").lower() or "x-iinfo" in {
        key.lower() for key in headers
    }


class YasnoAuthApi:
    """
    Handles the Azure AD B2C phone number + OTP login flow.

    The login is multi-step and stateful (a CSRF token and transaction id
    tied to session cookies), so a single `YasnoAuthApi` instance owns one
    `curl_cffi.requests.AsyncSession` for the duration of a login attempt.
    Call `close()` once done (successful or not).
    """

    def __init__(self) -> None:
        """Initialize the YasnoAuthApi."""
        self._session: AsyncSession | None = None
        self._code_verifier: str | None = None
        self._trans_id: str | None = None
        self._csrf_token: str | None = None
        self._action_base: str | None = None
        self._api: str | None = None
        self._policy: str | None = None
        self._phone: str | None = None
        self._message_type: str | None = None
        self._referer: str | None = None
        # Mimics the app's per-install device id; the real app always sends a
        # non-empty UUID here (an empty deviceId/flowType="Login" combination
        # was observed to be rejected by the upstream WAF, see skill-yasno.md).
        self._device_id: str = str(uuid.uuid4()).upper()

    def _action_url(self, sub: str | None = None) -> str:
        """Build a B2C SelfAsserted action URL for the current transaction."""
        path = f"/{self._api}" + (f"/{sub}" if sub else "")
        query = urlencode({"tx": self._trans_id, "p": self._policy})
        return f"{self._action_base}{path}?{query}"

    async def _post_self_asserted(self, url: str, data: dict) -> dict:
        """POST form data to a B2C SelfAsserted action and return its JSON body."""
        headers = {
            "X-CSRF-TOKEN": self._csrf_token,
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Origin": "https://login.yasno.ua",
            "User-Agent": AUTH_USER_AGENT,
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
        }
        if self._referer:
            headers["Referer"] = self._referer
        response = await self._session.post(
            url,
            data=urlencode(data),
            headers=headers,
            timeout=_TIMEOUT,
        )
        if response.status_code >= _HTTP_BAD_REQUEST:
            LOGGER.debug(
                "SelfAsserted request to %s failed: status=%s "
                "response_headers=%s body=%s",
                url,
                response.status_code,
                dict(response.headers),
                response.text,
            )
            if _is_imperva_block(response.headers):
                msg = (
                    f"Request blocked by WAF (status={response.status_code}); "
                    "likely a rate-limit/IP block, not an invalid phone number"
                )
                raise YasnoAuthBlockedError(msg)
        response.raise_for_status()
        return json.loads(response.text)

    async def start_login(
        self,
        phone_number: str,
        message_type: Literal["sms", "viber"] = AUTH_MESSAGE_TYPE_SMS,
    ) -> None:
        """Start a login attempt and trigger an SMS/Viber code to be sent."""
        if message_type not in _MESSAGE_TYPES:
            msg = f"Unsupported message_type: {message_type!r}"
            raise ValueError(msg)

        self._session = AsyncSession(impersonate=AUTH_IMPERSONATE)
        self._code_verifier, challenge = _make_pkce()

        params = {
            "client_id": AUTH_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": AUTH_REDIRECT_URI,
            "scope": AUTH_SCOPE,
            "state": secrets.token_urlsafe(16),
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "prompt": "login",
        }
        response = await self._session.get(
            f"{AUTH_AUTHORITY}/oauth2/v2.0/authorize",
            params=params,
            timeout=_TIMEOUT,
            headers={"User-Agent": AUTH_USER_AGENT},
        )
        response.raise_for_status()
        html = response.text
        self._referer = str(response.url)

        settings = _extract_settings(html)
        hosts = settings.get("hosts", {})
        self._trans_id = settings.get("transId")
        self._csrf_token = settings.get("csrf")
        self._api = settings.get("api", "SelfAsserted")
        self._policy = hosts.get("policy")
        tenant_path = hosts.get("tenant")
        if not (self._trans_id and self._csrf_token and tenant_path and self._policy):
            msg = f"Missing transId/csrf/hosts in authorize page SETTINGS: {settings}"
            raise YasnoAuthError(msg)
        self._action_base = f"https://login.yasno.ua{tenant_path}"

        self._phone = phone_number
        self._message_type = message_type

        body = await self._post_self_asserted(
            self._action_url(
                f"DisplayControlAction/vbeta/{AUTH_VERIFICATION_CONTROL_ID}/SendCode",
            ),
            {
                "flowType": "Register",
                "phoneNumber": phone_number,
                "executeValidation": "",
                "deviceId": self._device_id,
                "messageType": message_type,
            },
        )
        if int(body.get("status", 0)) != _HTTP_OK:
            msg = f"SendCode failed: {body}"
            raise YasnoAuthError(msg)

    async def verify_code(self, code: str) -> None:
        """Verify the OTP code the user received via SMS/Viber."""
        if not self._session:
            msg = "start_login() must be called before verify_code()"
            raise YasnoAuthError(msg)

        data = {
            "flowType": "Register",
            "phoneNumber": self._phone,
            "executeValidation": "",
            "deviceId": self._device_id,
            "messageType": self._message_type,
            "verificationCode": code,
        }
        body = await self._post_self_asserted(
            self._action_url(
                f"DisplayControlAction/vbeta/{AUTH_VERIFICATION_CONTROL_ID}/VerifyCode",
            ),
            data,
        )
        if int(body.get("status", 0)) != _HTTP_OK:
            msg = f"VerifyCode failed: {body}"
            raise YasnoAuthError(msg)

        body = await self._post_self_asserted(
            self._action_url(),
            {"request_type": "RESPONSE", **data},
        )
        if int(body.get("status", 0)) != _HTTP_OK:
            msg = f"Final sign-in step failed: {body}"
            raise YasnoAuthError(msg)

    async def complete_login(self) -> AuthTokens:
        """Finish the login flow and exchange the authorization code for tokens."""
        if not self._session:
            msg = "start_login() must be called before complete_login()"
            raise YasnoAuthError(msg)

        next_url = f"{self._action_base}/api/CombinedSigninAndSignup/confirmed"
        next_params: dict | None = {
            "csrf_token": self._csrf_token,
            "tx": self._trans_id,
            "p": self._policy,
        }

        code = None
        max_redirects = 5
        for _ in range(max_redirects):
            response = await self._session.get(
                next_url,
                params=next_params,
                allow_redirects=False,
                timeout=_TIMEOUT,
                headers={"User-Agent": AUTH_USER_AGENT},
            )
            location = response.headers.get("Location")
            next_params = None
            if not location:
                break
            qs = parse_qs(urlparse(location).query)
            if "code" in qs:
                code = qs["code"][0]
                break
            if not location.startswith(("http://", "https://")):
                # e.g. msauth://... - the final app redirect, not followable.
                break
            next_url = location

        if not code:
            msg = "Did not receive an authorization code from the confirmed endpoint"
            raise YasnoAuthError(msg)

        tokens = await self._exchange_token(
            {
                "client_id": AUTH_CLIENT_ID,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": AUTH_REDIRECT_URI,
                "code_verifier": self._code_verifier,
                "scope": AUTH_SCOPE,
            },
            session=self._session,
        )
        return self._parse_tokens(tokens)

    async def refresh(self, refresh_token: str) -> AuthTokens:
        """Exchange a refresh token for a new set of tokens."""
        async with AsyncSession(impersonate=AUTH_IMPERSONATE) as session:
            tokens = await self._exchange_token(
                {
                    "client_id": AUTH_CLIENT_ID,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "scope": AUTH_SCOPE,
                },
                session=session,
            )
        return self._parse_tokens(tokens)

    @staticmethod
    async def _exchange_token(
        data: dict,
        session: AsyncSession,
    ) -> dict:
        """POST to the token endpoint and return the parsed JSON response."""
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": AUTH_USER_AGENT,
        }
        response = await session.post(
            f"{AUTH_AUTHORITY}/oauth2/v2.0/token",
            data=urlencode(data),
            headers=headers,
            timeout=_TIMEOUT,
        )
        if response.status_code >= _HTTP_BAD_REQUEST and _is_imperva_block(
            response.headers,
        ):
            msg = f"Token request blocked by WAF (status={response.status_code})"
            raise YasnoAuthBlockedError(msg)
        response.raise_for_status()
        return json.loads(response.text)

    @staticmethod
    def _parse_tokens(tokens: dict) -> AuthTokens:
        """Parse a token endpoint response into an AuthTokens object."""
        try:
            return AuthTokens(
                access_token=tokens["access_token"],
                refresh_token=tokens["refresh_token"],
                id_token=tokens.get("id_token", ""),
                expires_in=int(tokens["expires_in"]),
            )
        except KeyError as err:
            msg = f"Token response missing expected field: {sorted(tokens.keys())}"
            raise YasnoAuthError(msg) from err

    async def close(self) -> None:
        """Close the underlying HTTP session used for the login flow."""
        if self._session:
            await self._session.close()
            self._session = None
