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
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    ResetPasswordRequest,
    SwitchTenantRequest,
    UserOut,
)
from app.services.audit import write_audit
from app.services.notifications import (
    PASSWORD_CHANGED,
    PASSWORD_RESET_REQUESTED,
    enqueue_notification,
)
from app.services.password_reset import (
    TOKEN_TTL_MIN,
    consume_reset_token,
    issue_reset_token,
)
from app.services.rate_limit import check_and_increment, reset as rate_limit_reset

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
    # US-063: confirmación al user ("si no fuiste tú, avisa al admin").
    if cu.user.tenant_id is not None:
        await enqueue_notification(
            db,
            tenant_id=cu.user.tenant_id,
            user_id=cu.id,
            type=PASSWORD_CHANGED,
            title="Tu contraseña fue cambiada",
            body=(
                "Acabas de cambiar tu contraseña. Si no fuiste tú, "
                "avisa inmediatamente al administrador del tenant."
            ),
            entity_type="user",
            entity_id=str(cu.id),
            link="/account",
            send_email=True,
        )
    await db.commit()
    from fastapi.responses import Response

    return Response(status_code=204)


@router.get("/me", response_model=UserOut)
async def me(cu: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await _build_user_out(db, cu.user)


@router.get("/me/permissions")
async def my_permissions(cu: CurrentUser = Depends(get_current_user)):
    """US-060 — expone el role_type + lista plana de permisos del user
    actual para que el frontend pueda gate-ar botones/links."""
    from app.core.permissions import flat_permissions

    return {
        "role_type": cu.role_type or "user",
        "is_superadmin": cu.is_superadmin,
        "permissions": flat_permissions(cu.role_type or "user"),
    }


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


# ============================================================================
# US-063 — Forgot / reset password por email
# ============================================================================

# Rate-limit: 5 intentos por IP por hora en forgot; 10 en reset (para
# tolerar el tab de reset abierto + browser autofill). Las keys viven en
# Redis con EXPIRE de `window_sec`; si Redis está caído el check abre
# fail-open (ver rate_limit.py).
_FORGOT_MAX_PER_HOUR_IP = 5
_RESET_MAX_PER_HOUR_IP = 10
_WINDOW_SEC = 3600


def _client_ip(req: Request) -> str:
    # Railway + la mayoría de PaaS ponen la IP del cliente en
    # `X-Forwarded-For`; fallback al socket.
    fwd = req.headers.get("x-forwarded-for") or ""
    if fwd:
        return fwd.split(",")[0].strip()
    if req.client and req.client.host:
        return req.client.host
    return "unknown"


@router.post("/forgot-password", status_code=204)
async def forgot_password(
    body: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Emite un link de reset al email **si existe un usuario activo**.

    Responde siempre 204 para no revelar qué emails están registrados.
    Si el rate-limit se excede, respondemos 204 también — el atacante no
    distingue entre 'email no existe' y 'fue bloqueado'. El usuario
    legítimo recibirá el email cuando la ventana se reinicie."""
    from fastapi.responses import Response

    ip = _client_ip(request)
    ok_ip = check_and_increment(
        f"rl:forgot:ip:{ip}",
        max_attempts=_FORGOT_MAX_PER_HOUR_IP,
        window_sec=_WINDOW_SEC,
    )
    if not ok_ip:
        # Loggeamos pero respondemos 204 para no filtrar.
        import logging

        logging.getLogger("pmoaas.auth").warning(
            "forgot_password rate_limit ip=%s", ip,
        )
        return Response(status_code=204)

    email_lc = str(body.email).lower()
    user = (
        await db.execute(
            select(User).where(User.email == email_lc, User.is_active.is_(True))
        )
    ).scalar_one_or_none()
    if user is None:
        # No revelamos.
        return Response(status_code=204)

    plain_token = await issue_reset_token(db, user_id=user.id, ip_address=ip)
    reset_link = f"{settings.APP_BASE_URL.rstrip('/')}/reset?token={plain_token}"

    # Notificación in-app + email (PASSWORD_RESET_REQUESTED está en
    # EMAIL_BY_DEFAULT, así que la task Celery la manda vía Resend).
    if user.tenant_id is not None:
        await enqueue_notification(
            db,
            tenant_id=user.tenant_id,
            user_id=user.id,
            type=PASSWORD_RESET_REQUESTED,
            title="Solicitud de restablecer contraseña",
            body=(
                f"Recibimos una solicitud para restablecer tu contraseña. "
                f"Este link expira en {TOKEN_TTL_MIN} minutos. Si no "
                "fuiste tú, ignora este mensaje."
            ),
            entity_type="user",
            entity_id=str(user.id),
            link=reset_link,
            send_email=True,
        )
    await write_audit(
        db,
        action="password_reset_requested",
        module="auth",
        user_id=user.id,
        tenant_id=user.tenant_id,
        ip_address=ip,
    )
    await db.commit()
    return Response(status_code=204)


@router.post("/reset-password", status_code=204)
async def reset_password(
    body: ResetPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Consume el token y fija la nueva contraseña.

    Requiere que la nueva cumpla la política (≥ 12 chars + U + digit +
    symbol). Al éxito: invalida todos los refresh tokens del user,
    limpia `must_change_password` si estaba, manda email confirmando
    y audit log."""
    from fastapi.responses import Response

    ip = _client_ip(request)
    ok_ip = check_and_increment(
        f"rl:reset:ip:{ip}",
        max_attempts=_RESET_MAX_PER_HOUR_IP,
        window_sec=_WINDOW_SEC,
    )
    if not ok_ip:
        raise business_rule(
            "Demasiados intentos. Intenta de nuevo en una hora.",
            code="RATE_LIMITED",
        )

    policy_ok, policy_err = validate_password_policy(body.new_password)
    if not policy_ok:
        raise validation_error(
            "Contraseña no cumple política", {"code": policy_err}
        )

    token_row = await consume_reset_token(db, plain=body.token)
    if token_row is None:
        # Mensaje genérico: el atacante no debe saber si el token existió.
        raise business_rule(
            "Token inválido o expirado", code="TOKEN_INVALID",
        )

    user = (
        await db.execute(
            select(User).where(
                User.id == str(token_row.user_id), User.is_active.is_(True)
            )
        )
    ).scalar_one_or_none()
    if user is None:
        raise business_rule("Usuario inactivo", code="USER_INACTIVE")

    user.password_hash = hash_password(body.new_password)
    user.must_change_password = False
    # Invalida TODOS los refresh tokens activos del user.
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id)
        .values(revoked=True)
    )

    if user.tenant_id is not None:
        await enqueue_notification(
            db,
            tenant_id=user.tenant_id,
            user_id=user.id,
            type=PASSWORD_CHANGED,
            title="Tu contraseña fue restablecida",
            body=(
                "Acabas de restablecer tu contraseña. Si no fuiste tú, "
                "avisa inmediatamente al administrador del tenant."
            ),
            entity_type="user",
            entity_id=str(user.id),
            link="/login",
            send_email=True,
        )

    await write_audit(
        db,
        action="password_reset_confirmed",
        module="auth",
        user_id=user.id,
        tenant_id=user.tenant_id,
        ip_address=ip,
        details={"token_id": str(token_row.id)},
    )
    await db.commit()

    # Éxito: permitimos al user reintentar login sin trabarse con la ventana.
    rate_limit_reset(f"rl:reset:ip:{ip}")
    return Response(status_code=204)
