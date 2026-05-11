import secrets

from fastapi import Header, HTTPException, status

from app.config import get_settings


def _tenant_for_api_key(x_api_key: str) -> str | None:
    """Resolve tenant using sorted iteration + compare_digest (same-length keys only)."""
    settings = get_settings()
    for stored_key, tenant_id in sorted(settings.api_keys.items(), key=lambda kv: kv[0]):
        if len(stored_key) != len(x_api_key):
            continue
        if secrets.compare_digest(stored_key, x_api_key):
            return tenant_id
    return None


def get_tenant_id_from_api_key(x_api_key: str | None = Header(default=None)) -> str:
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "unauthenticated",
                "message": "Missing API key.",
                "details": {},
                "correlation_id": None,
            },
        )

    tenant_id = _tenant_for_api_key(x_api_key)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "unauthorized_tenant",
                "message": "API key is invalid for tenant access.",
                "details": {},
                "correlation_id": None,
            },
        )
    return tenant_id
