"""Reverse proxy for all backend services."""
from __future__ import annotations

from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Request, Response

from ..config.settings import get_settings
from ..middlewares.authMiddleware import optional_auth, require_auth

router = APIRouter()

# Headers that httpx / ASGI will set automatically — don't copy from downstream response.
_HOP_BY_HOP = {
    "content-encoding",
    "content-length",
    "transfer-encoding",
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "upgrade",
}


def _upstream_for_prefix(prefix: str) -> Optional[str]:
    s = get_settings()
    mapping = {
        "auth": s.AUTH_SERVICE_URL,
        "users": s.USER_SERVICE_URL,
        "movies": s.MOVIE_SERVICE_URL,
        "showtimes": s.MOVIE_SERVICE_URL,
        "seats": s.MOVIE_SERVICE_URL,
        "vouchers": s.VOUCHER_SERVICE_URL,
        "bookings": s.BOOKING_SERVICE_URL,
        "payments": s.PAYMENT_SERVICE_URL,
    }
    return mapping.get(prefix)


def _requires_auth(prefix: str, method: str, path_tail: str) -> bool:
    if prefix == "auth":
        return False
    if prefix in ("movies", "showtimes"):
        return False
    if prefix == "vouchers" and method == "GET":
        return False
    if prefix == "payments":
        # Public: mock pay HTML page and VNPay return redirect
        if path_tail.startswith("mock/") or path_tail == "vnpay-return":
            return False
    return True


async def _forward(
    request: Request, upstream_base: str, path_tail: str, claims: Optional[dict]
) -> Response:
    s = get_settings()
    url = f"{upstream_base.rstrip('/')}/{path_tail.lstrip('/')}"
    if request.url.query:
        url = f"{url}?{request.url.query}"

    fwd_headers: dict[str, str] = {}
    for k, v in request.headers.items():
        lk = k.lower()
        if lk in {"host", "content-length"}:
            continue
        fwd_headers[k] = v
    if claims:
        fwd_headers["x-user-id"] = str(claims.get("user_id") or claims.get("sub"))
        fwd_headers["x-user-email"] = str(claims.get("email") or "")
        fwd_headers["x-user-role"] = str(claims.get("role") or "")

    body = await request.body()

    async with httpx.AsyncClient(timeout=s.HTTP_TIMEOUT_SECONDS, follow_redirects=False) as client:
        try:
            r = await client.request(
                method=request.method,
                url=url,
                headers=fwd_headers,
                content=body,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"upstream error: {exc}") from exc

    resp_headers = {k: v for k, v in r.headers.items() if k.lower() not in _HOP_BY_HOP}
    return Response(content=r.content, status_code=r.status_code, headers=resp_headers, media_type=r.headers.get("content-type"))


@router.api_route(
    "/{prefix}/{path_tail:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def proxy(prefix: str, path_tail: str, request: Request) -> Response:
    upstream = _upstream_for_prefix(prefix)
    if upstream is None:
        raise HTTPException(status_code=404, detail="unknown route")

    claims: Optional[dict] = None
    if _requires_auth(prefix, request.method, path_tail):
        claims = require_auth(request)
    else:
        claims = optional_auth(request)

    # Forward preserving full path including prefix
    full_tail = f"{prefix}/{path_tail}" if path_tail else prefix
    return await _forward(request, upstream, full_tail, claims)


@router.api_route("/{prefix}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_root(prefix: str, request: Request) -> Response:
    """Handles e.g. GET /movies (no trailing path segment)."""
    upstream = _upstream_for_prefix(prefix)
    if upstream is None:
        raise HTTPException(status_code=404, detail="unknown route")

    claims: Optional[dict] = None
    if _requires_auth(prefix, request.method, ""):
        claims = require_auth(request)
    else:
        claims = optional_auth(request)

    return await _forward(request, upstream, prefix, claims)
