from fastapi import Header, HTTPException, status

from app.config import get_settings


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

    tenant_id = get_settings().api_keys.get(x_api_key)
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
