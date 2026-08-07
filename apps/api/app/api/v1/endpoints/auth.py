import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user
from app.core import cookies
from app.core.config import settings
from app.core.contrasenas_filtradas import esta_filtrada
from app.core.errors import (
    business_rule,
    forbidden,
    mensaje,
    rate_limited,
    unauthorized,
    validation_error,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    mensaje_de_politica,
    necesita_rehash,
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
    PASSWORD_RESET_REQUESTED,
    avisa_cambio_de_credencial,
    enqueue_notification,
)
from app.services.password_reset import (
    TOKEN_TTL_MIN,
    consume_reset_token,
    issue_reset_token,
)
from app.services.rate_limit import check_and_increment, excede
from app.services.rate_limit import reset as rate_limit_reset

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
    # AM-09 · límite por IP. El bloqueo por cuenta que ya había detiene a quien
    # adivina la contraseña de **una** cuenta; no hace nada contra el rociado,
    # que prueba una contraseña contra mil cuentas y no toca el umbral de
    # ninguna. El limitador existía y se aplicaba en recuperación y reseteo:
    # esto es aplicar lo que ya estaba escrito.
    #
    # Se usa `_client_ip` y no `request.client.host` a propósito: detrás del
    # proxy de Railway el socket es siempre el mismo, así que contar por él
    # bloquearía a todo el mundo con el primer atacante.
    clave_limite = f"rl:login:ip:{_client_ip(request)}"
    if excede(clave_limite, max_attempts=_LOGIN_MAX_FAILS_PER_HOUR_IP):
        raise rate_limited()

    def registrar_fallo() -> None:
        """Suma uno al contador de la IP. El corte se hace arriba, en la puerta."""
        check_and_increment(
            clave_limite,
            max_attempts=_LOGIN_MAX_FAILS_PER_HOUR_IP,
            window_sec=_WINDOW_SEC,
        )

    ident = body.identifier.strip().lower()
    stmt = select(User).where(or_(User.username == ident, User.email == ident))
    user = (await db.execute(stmt)).scalar_one_or_none()
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    if user is None:
        registrar_fallo()
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
        registrar_fallo()
        restan = max(1, int((locked_until - now).total_seconds()))
        await write_audit(
            db, action="login_failed", module="auth", user_id=user.id, tenant_id=user.tenant_id,
            details={"reason": "backoff", "wait_seconds": restan},
            ip_address=ip, user_agent=ua,
        )
        # Se conserva `ACCOUNT_LOCKED` como `code` —el frontend lo trata— pero
        # ya no significa «bloqueada»: significa «espera unos segundos». El
        # texto lo dice, con el número, para que la espera no parezca infinita.
        raise forbidden(
            code="ACCOUNT_LOCKED",
            detail=(
                mensaje(
                    que=f"Por seguridad, tras varios intentos fallidos hay que esperar "
                        f"antes del siguiente. Vuelve a intentarlo en {restan} segundos; "
                        f"si no recuerdas tu contraseña, usa «¿Olvidaste tu contraseña?».",
                    porque="La espera es lo que impide probar contraseñas una tras otra.",
                    accion="Espera el tiempo indicado, o usa «¿Olvidaste tu contraseña?».",
                )
            ),
        )

    if not verify_password(body.password, user.password_hash):
        registrar_fallo()
        user.failed_login_attempts += 1
        espera = espera_tras_fallos(user.failed_login_attempts)
        if espera:
            # `locked_until` se conserva como columna, pero pasa a significar
            # «no antes de» en vez de «bloqueada hasta» (AM-10).
            user.locked_until = now + timedelta(seconds=espera)
            await write_audit(
                db, action="login_backoff", module="auth", user_id=user.id,
                tenant_id=user.tenant_id,
                details={"attempts": user.failed_login_attempts, "wait_seconds": espera},
                ip_address=ip, user_agent=ua,
            )
        await write_audit(
            db, action="login_failed", module="auth", user_id=user.id, tenant_id=user.tenant_id,
            details={"reason": "bad_password", "attempts": user.failed_login_attempts},
            ip_address=ip, user_agent=ua,
        )
        await db.commit()
        raise unauthorized()

    if not user.is_active:
        registrar_fallo()
        await write_audit(
            db, action="login_failed", module="auth", user_id=user.id, tenant_id=user.tenant_id,
            details={"reason": "inactive"}, ip_address=ip, user_agent=ua,
        )
        raise forbidden(code="USER_INACTIVE", detail=mensaje(
            que="Usuario inactivo",
            porque="La cuenta está desactivada y no puede iniciar sesión.",
            accion="Pide su reactivación a quien administre tu organización.",
        ))

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login = now

    # MCS SEG-01 / ASVS 2.1.3 — el único momento en que la contraseña en claro
    # existe y se ha demostrado correcta. Si su hash sigue en el esquema viejo
    # —bcrypt a secas, que trunca a 72 bytes— se reescribe al nuevo aquí. Una
    # migración de esquema que no se cablea en el inicio de sesión no migra
    # nunca: nadie va a pedirle la contraseña otra vez a nadie para esto.
    if necesita_rehash(user.password_hash):
        user.password_hash = hash_password(body.password)

    # MCS SEG-01 / ASVS 2.1.7 — el control nombra tres momentos: alta, **inicio
    # de sesión** y cambio. Los otros dos los cubre `validate_password_policy`,
    # que rechaza. Aquí no se puede rechazar: la contraseña es correcta, y dejar
    # a alguien fuera de su cuenta porque su contraseña apareció en una
    # filtración es convertir el aviso en una denegación de servicio.
    #
    # Lo que se hace es forzar el cambio en la siguiente pantalla. Es el mismo
    # mecanismo del alta por administrador, así que la web ya lo sabe llevar.
    if not user.must_change_password and esta_filtrada(body.password):
        user.must_change_password = True
        await write_audit(
            db, action="password_breached_detected", module="auth", user_id=user.id,
            tenant_id=user.tenant_id, details={"forced_change": True},
            ip_address=ip, user_agent=ua,
        )

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
    # ASVS 3.4.4 — nombre, `Path` y `Secure` los decide `core/cookies.py`: el
    # prefijo `__Host-` solo vale si van los tres juntos, y repartir esa regla
    # por los endpoints es cómo se acaba emitiendo una cookie que el navegador
    # tira sin decir nada.
    cookies.fijar(resp, cookies.REFRESCO, refresh, max_age=settings.REFRESH_TOKEN_TTL_SEC)
    return resp


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    cu: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    refresh = cookies.leer(request, cookies.REFRESCO)
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
    cookies.borrar(r, cookies.REFRESCO)
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
        raise business_rule(mensaje(
            que="La nueva contraseña debe ser diferente",
            porque="Repetir la anterior no cambia nada si alguien ya la conocía.",
            accion="Elige una contraseña que no hayas usado antes.",
        ))
    ok, err = validate_password_policy(body.new_password)
    if not ok:
        raise validation_error(mensaje_de_politica(err), {"code": err})
    cu.user.password_hash = hash_password(body.new_password)
    cu.user.must_change_password = False
    # invalidar todos los refresh tokens del usuario
    await db.execute(update(RefreshToken).where(RefreshToken.user_id == cu.id).values(revoked=True))
    await write_audit(db, action="password_change", module="auth", user_id=cu.id, tenant_id=cu.user.tenant_id)
    # ASVS 2.2.3 / 2.5.5. Antes esto llevaba el guardia `if tenant_id is not
    # None`, así que un superadministrador —la cuenta con más permisos de la
    # plataforma— era la única que cambiaba su contraseña sin recibir aviso.
    await avisa_cambio_de_credencial(db, usuario=cu.user, motivo="password")
    await db.commit()
    from fastapi.responses import Response

    return Response(status_code=204)


@router.get("/me", response_model=UserOut)
async def me(cu: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await _build_user_out(db, cu.user)


@router.get("/me/permissions")
async def my_permissions(cu: CurrentUser = Depends(get_current_user)):
    """US-060 + US-076 — expone el role_type + capabilities del user
    actual para que el frontend pueda gate-ar botones/links.

    `capabilities` es el vocabulario nuevo (5 strings para admin, 0
    para user). `permissions` es el shim legacy `module:action` para
    el hook `useMyPermissions` pre-DEC-024; se borra en US-080/081 al
    migrar el hook al vocabulario de capabilities.
    """
    from app.core.permissions import (
        capabilities_for,
        flat_permissions,
        legacy_permissions_shim,
    )

    role_type = cu.role_type or "user"
    # Aplicar overrides de tenant para reportar el set efectivo.
    effective_caps = set(capabilities_for(role_type))
    for cap, granted in cu.capability_overrides.get(role_type, {}).items():
        if granted:
            effective_caps.add(cap)
        else:
            effective_caps.discard(cap)
    return {
        "role_type": role_type,
        "is_superadmin": cu.is_superadmin,
        "capabilities": sorted(effective_caps) if not cu.is_superadmin else sorted(flat_permissions("admin")),
        "permissions": legacy_permissions_shim(
            "admin" if cu.is_superadmin else role_type
        ),
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

#: AM-09 — **fallos** de inicio de sesión por IP y por hora.
#:
#: Se cuentan solo los fallos, no los intentos. Con `check_and_increment` en la
#: puerta contaríamos también los aciertos, y una oficina detrás de un NAT
#: —decenas de personas compartiendo IP, acertando la contraseña— se quedaría
#: fuera sin haber hecho nada raro.
#:
#: 30 sale de mirar los dos lados: el bloqueo por cuenta ya corta a los 5
#: fallos del mismo usuario, así que llegar aquí exige fallar contra **muchas**
#: cuentas distintas, que es la firma del rociado. Y deja margen a una oficina
#: grande con dedos torpes un lunes. Si un cliente real lo toca, este número es
#: lo que hay que subir — no el que hay que quitar.
_LOGIN_MAX_FAILS_PER_HOUR_IP = 30


def espera_tras_fallos(fallos: int) -> int:
    """Segundos que hay que esperar tras `fallos` intentos fallidos (AM-10).

    Cero hasta el umbral; a partir de ahí el doble cada vez, con tope. **No es
    un bloqueo**: la cuenta nunca queda fuera, solo se responde más despacio.

    Ese matiz es la amenaza entera. Con bloqueo duro, quien conociera un nombre
    de usuario dejaba esa cuenta inutilizable un cuarto de hora —y con una lista
    de usuarios, al inquilino entero—. Con retardo creciente, el peor caso para
    quien sufre el ataque es esperar `LOGIN_BACKOFF_MAX_SECONDS`, y quien tecleó
    mal su contraseña espera segundos.

    Contra la adivinación protege igual o mejor: con el tope por defecto son
    doce intentos por hora y por cuenta, y el rociado lo corta AM-09 por IP.
    """
    exceso = fallos - settings.MAX_FAILED_LOGIN_ATTEMPTS
    if exceso < 0:
        return 0
    return min(
        settings.LOGIN_BACKOFF_BASE_SECONDS * (2**exceso),
        settings.LOGIN_BACKOFF_MAX_SECONDS,
    )


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
        # Antes era un 422 con este mismo `code`, que le dice al cliente que su
        # cuerpo está mal cuando lo que pasa es que fue demasiado rápido. Con
        # `RATE_LIMITED` ya en el catálogo (AM-09), los dos sitios que lo emiten
        # devuelven el código que les corresponde.
        raise rate_limited()

    policy_ok, policy_err = validate_password_policy(body.new_password)
    if not policy_ok:
        raise validation_error(mensaje_de_politica(policy_err), {"code": policy_err})

    token_row = await consume_reset_token(db, plain=body.token)
    if token_row is None:
        # Mensaje genérico: el atacante no debe saber si el token existió.
        raise business_rule(
            mensaje(
                que="Token inválido o expirado",
                porque="Los enlaces de recuperación caducan para que uno filtrado no sirva para siempre.",
                accion="Pide un enlace nuevo desde «¿Olvidaste tu contraseña?».",
            ), code="TOKEN_INVALID",
        )

    user = (
        await db.execute(
            select(User).where(
                User.id == str(token_row.user_id), User.is_active.is_(True)
            )
        )
    ).scalar_one_or_none()
    if user is None:
        raise business_rule(mensaje(
            que="Usuario inactivo",
            porque="La cuenta está desactivada y no puede iniciar sesión.",
            accion="Pide su reactivación a quien administre tu organización.",
        ), code="USER_INACTIVE")

    user.password_hash = hash_password(body.new_password)
    user.must_change_password = False
    # Invalida TODOS los refresh tokens activos del user.
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id)
        .values(revoked=True)
    )

    await avisa_cambio_de_credencial(db, usuario=user, motivo="password_reset")

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
