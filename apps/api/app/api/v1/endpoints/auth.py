import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user
from app.core.config import settings
from app.core.errors import business_rule, forbidden, unauthorized, validation_error
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    validate_password_policy,
    verify_password,
)
from app.db.session import get_db
from app.models.auth import RefreshToken
from app.models.role import Role, UserRole
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    SwitchTenantRequest,
    UserOut,
)
from app.services.audit import write_audit

router = APIRouter(prefix="/auth", tags=["auth"])


async def _build_user_out(db: AsyncSession, user: User) -> UserOut:
    role_names = (
        await db.execute(
            select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user.id)
        )
    ).scalars().all()
    return UserOut.model_validate(
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_superadmin": user.is_superadmin,
            "must_change_password": user.must_change_password,
            "roles": list(role_names),
        }
    )


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    ident = body.identifier.strip().lower()
    stmt = select(User).where(or_(User.username == ident, User.email == ident))
    user = (await db.execute(stmt)).scalar_one_or_none()
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    if user is None:
        await write_audit(
            db, action="login_failed", module="auth",
            details={"identifier": ident, "reason": "not_found"}, ip_address=ip, user_agent=ua,
        )
        raise unauthorized()

    now = datetime.now(UTC)
    locked_until = user.locked_until
    if locked_until is not None and locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=UTC)
    if locked_until and locked_until > now:
        await write_audit(
            db, action="login_failed", module="auth", user_id=user.id, tenant_id=user.tenant_id,
            details={"reason": "locked"}, ip_address=ip, user_agent=ua,
        )
        raise forbidden(code="ACCOUNT_LOCKED", detail="Cuenta bloqueada, intenta más tarde")

    if not verify_password(body.password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
            user.locked_until = now + timedelta(minutes=settings.ACCOUNT_LOCK_MINUTES)
            await write_audit(
                db, action="account_locked", module="auth", user_id=user.id, tenant_id=user.tenant_id,
                details={"attempts": user.failed_login_attempts}, ip_address=ip, user_agent=ua,
            )
        await write_audit(
            db, action="login_failed", module="auth", user_id=user.id, tenant_id=user.tenant_id,
            details={"reason": "bad_password", "attempts": user.failed_login_attempts},
            ip_address=ip, user_agent=ua,
        )
        await db.commit()
        raise unauthorized()

    if not user.is_active:
        await write_audit(
            db, action="login_failed", module="auth", user_id=user.id, tenant_id=user.tenant_id,
            details={"reason": "inactive"}, ip_address=ip, user_agent=ua,
        )
        raise forbidden(code="USER_INACTIVE", detail="Usuario inactivo")

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login = now

    role_names = (
        await db.execute(
            select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user.id)
        )
    ).scalars().all()

    tenant_ids: list = []
    if user.tenant_id:
        tenant_ids.append(user.tenant_id)
    active_tenant = user.tenant_id

    access = create_access_token(
        subject=user.id,
        tenant_ids=[str(t) for t in tenant_ids],
        active_tenant_id=str(active_tenant) if active_tenant else None,
        is_superadmin=user.is_superadmin,
        roles=list(role_names),
    )
    jti = uuid4().hex
    refresh = create_refresh_token(subject=user.id, jti=jti)
    db.add(
        RefreshToken(
            user_id=user.id,
            jti=jti,
            expires_at=now + timedelta(seconds=settings.REFRESH_TOKEN_TTL_SEC),
        )
    )
    await write_audit(
        db, action="login_success", module="auth", user_id=user.id, tenant_id=user.tenant_id,
        ip_address=ip, user_agent=ua,
    )
    await db.commit()

    user_out = await _build_user_out(db, user)
    response = LoginResponse(
        access_token=access,
        user=user_out,
        tenants=tenant_ids,
        active_tenant_id=active_tenant,
    )
    # refresh token via HttpOnly cookie set by response headers
    from fastapi.responses import JSONResponse

    resp = JSONResponse(content=response.model_dump(mode="json"))
    resp.set_cookie(
        "refresh_token", refresh, httponly=True, secure=settings.PYTHON_ENV == "production",
        samesite="strict", max_age=settings.REFRESH_TOKEN_TTL_SEC, path="/api/v1/auth",
    )
    return resp


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    cu: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    refresh = request.cookies.get("refresh_token")
    if refresh:
        from app.core.security import decode_refresh_token

        try:
            payload = decode_refresh_token(refresh)
            jti = payload.get("jti")
            if jti:
                await db.execute(
                    update(RefreshToken).where(RefreshToken.jti == jti).values(revoked=True)
                )
        except ValueError:
            pass
    await write_audit(db, action="logout", module="auth", user_id=cu.id, tenant_id=cu.user.tenant_id)
    await db.commit()
    from fastapi.responses import Response

    r = Response(status_code=204)
    r.delete_cookie("refresh_token", path="/api/v1/auth")
    return r


@router.post("/change-password", status_code=204)
async def change_password(
    body: ChangePasswordRequest,
    cu: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(body.current_password, cu.user.password_hash):
        raise unauthorized()
    if body.current_password == body.new_password:
        raise business_rule("La nueva contraseña debe ser diferente")
    ok, err = validate_password_policy(body.new_password)
    if not ok:
        raise validation_error("Contraseña no cumple política", {"code": err})
    cu.user.password_hash = hash_password(body.new_password)
    cu.user.must_change_password = False
    # invalidar todos los refresh tokens del usuario
    await db.execute(update(RefreshToken).where(RefreshToken.user_id == cu.id).values(revoked=True))
    await write_audit(db, action="password_change", module="auth", user_id=cu.id, tenant_id=cu.user.tenant_id)
    await db.commit()
    from fastapi.responses import Response

    return Response(status_code=204)


@router.get("/me", response_model=UserOut)
async def me(cu: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await _build_user_out(db, cu.user)


@router.post("/switch-tenant", response_model=LoginResponse)
async def switch_tenant(
    body: SwitchTenantRequest,
    cu: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not cu.is_superadmin and body.tenant_id not in cu.tenant_ids:
        raise forbidden()
    access = create_access_token(
        subject=cu.id,
        tenant_ids=[str(t) for t in cu.tenant_ids],
        active_tenant_id=str(body.tenant_id),
        is_superadmin=cu.is_superadmin,
        roles=cu.roles,
    )
    user_out = await _build_user_out(db, cu.user)
    return LoginResponse(
        access_token=access, user=user_out, tenants=cu.tenant_ids, active_tenant_id=body.tenant_id
    )


def _random_password(length: int = 16) -> str:
    import string

    alphabet = string.ascii_letters + string.digits + "!@#$%&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))
