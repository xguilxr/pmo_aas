"""Endpoints self-service para el usuario autenticado (`/users/me/...`).

US-007: preferencia de tema (dark/light/system).
US-009: perfil personal (full_name) + preferencias.
"""
from typing import Literal

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.api.deps import CurrentUser, get_current_user
from app.core import cookies
from app.core.errors import mensaje, validation_error
from app.db.session import get_db
from app.models.auth import RefreshToken
from app.services.audit import write_audit
from app.services.datos_personales import anonimiza, exporta

router = APIRouter(prefix="/users", tags=["users-me"])


ALLOWED_THEMES = ("dark", "light", "system")


class PreferencesPatch(BaseModel):
    theme: Literal["dark", "light", "system"] | None = None
    locale: str | None = None


class PreferencesOut(BaseModel):
    theme: Literal["dark", "light", "system"] = "system"
    locale: str | None = None


def _read_prefs(raw: dict | None) -> PreferencesOut:
    raw = raw or {}
    theme = raw.get("theme") if raw.get("theme") in ALLOWED_THEMES else "system"
    return PreferencesOut(theme=theme, locale=raw.get("locale"))


class ProfilePatch(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=200)


class ProfileOut(BaseModel):
    id: str
    username: str
    email: str
    full_name: str
    avatar_url: str | None


def _profile_out(u) -> ProfileOut:
    return ProfileOut(
        id=str(u.id),
        username=u.username,
        email=u.email,
        full_name=u.full_name,
        avatar_url=u.avatar_url,
    )


@router.get("/me", response_model=ProfileOut)
async def get_my_profile(cu: CurrentUser = Depends(get_current_user)):
    return _profile_out(cu.user)


@router.patch("/me", response_model=ProfileOut)
async def update_my_profile(
    body: ProfilePatch,
    cu: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    changes: dict[str, str] = {}
    if body.full_name is not None and body.full_name != cu.user.full_name:
        cu.user.full_name = body.full_name
        changes["full_name"] = body.full_name
    if changes:
        await write_audit(
            db,
            action="user.profile.update",
            module="auth",
            user_id=cu.id,
            tenant_id=cu.user.tenant_id,
            entity_type="user",
            entity_id=str(cu.id),
            details=changes,
        )
    await db.commit()
    return _profile_out(cu.user)


@router.get("/me/preferences", response_model=PreferencesOut)
async def get_my_preferences(cu: CurrentUser = Depends(get_current_user)):
    return _read_prefs(cu.user.preferences)


@router.patch("/me/preferences", response_model=PreferencesOut)
async def update_my_preferences(
    body: PreferencesPatch,
    cu: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    prefs = dict(cu.user.preferences or {})
    changes: dict[str, str] = {}
    if body.theme is not None:
        prefs["theme"] = body.theme
        changes["theme"] = body.theme
    if body.locale is not None:
        prefs["locale"] = body.locale
        cu.user.locale = body.locale
        changes["locale"] = body.locale
    cu.user.preferences = prefs
    flag_modified(cu.user, "preferences")
    if changes:
        await write_audit(
            db,
            action="user.preferences.update",
            module="auth",
            user_id=cu.id,
            tenant_id=cu.user.tenant_id,
            entity_type="user",
            entity_id=str(cu.id),
            details=changes,
        )
    await db.commit()
    return _read_prefs(cu.user.preferences)


# ---------------------------------------------------------------------------
# MCS SEG-01 · ASVS 8.3.2 — «users have a method to remove or export their data»
# ---------------------------------------------------------------------------


@router.get("/me/datos-personales")
async def exportar_mis_datos(
    cu: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    """Descarga en JSON de todo lo que la plataforma guarda sobre quien pide.

    Va **antes** que la supresión y no por casualidad: una vez anonimizado no
    hay forma de recuperar la copia, así que quien quiere irse necesita poder
    llevarse sus datos primero.

    Se registra en la auditoría porque una exportación de datos personales es
    una lectura masiva de datos personales — si alguien se hace con una sesión,
    esto es lo primero que haría, y tiene que dejar rastro.
    """
    contenido = await exporta(db, user=cu.user)
    await write_audit(
        db, action="personal_data_exported", module="account", user_id=cu.id,
        tenant_id=cu.user.tenant_id,
        details={"registros": len(contenido.get("actividad", []))},
    )
    await db.commit()

    return JSONResponse(
        content=contenido,
        headers={
            "Content-Disposition": (
                f'attachment; filename="mis-datos-{cu.user.username}.json"'
            )
        },
    )


class SupresionRequest(BaseModel):
    """La confirmación que hay que re-teclear.

    Mismo patrón que el borrado permanente de entidades (`core/hard_delete.py`):
    una acción irreversible no puede depender de un solo clic. Aquí es la propia
    dirección de correo, que es lo que la persona sabe sin buscarlo.
    """

    confirmacion: str = Field(min_length=1)


@router.post("/me/datos-personales/suprimir")
async def suprimir_mis_datos(
    body: SupresionRequest,
    cu: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Anonimiza los datos personales de quien lo pide (ASVS 8.3.2, ADR-034).

    **No borra filas.** Sustituye los identificadores por un seudónimo estable y
    no reversible, y deja la cuenta inactiva. El porqué —`audit_log` de solo
    anexado, y el historial del proyecto que es dato del inquilino y no de la
    persona— está en `services/datos_personales.py`.

    Es irreversible, así que exige re-teclear el correo. Y cierra la sesión: una
    cuenta anonimizada y con sesión viva sería una cuenta sin dueño desde la que
    todavía se puede operar.
    """
    correo = cu.user.email
    if body.confirmacion.strip().lower() != (correo or "").lower():
        raise validation_error(
            mensaje(
                que="La confirmación no coincide.",
                porque=(
                    "Esto no se puede deshacer: tus datos se sustituyen por un "
                    "marcador anónimo y no hay forma de recuperarlos."
                ),
                accion=f"Escribe exactamente tu correo: {correo}",
            ),
            fields={"esperado": "el correo de la cuenta"},
        )

    tocadas = await anonimiza(db, user=cu.user)
    # El registro se escribe con el usuario ya anonimizado: queda el hecho, no
    # quién era. Es lo mismo que hace la anonimización con el resto.
    await write_audit(
        db, action="personal_data_erased", module="account", user_id=cu.id,
        tenant_id=cu.user.tenant_id, details={"filas": tocadas},
    )
    await db.execute(
        update(RefreshToken).where(RefreshToken.user_id == cu.id).values(revoked=True)
    )
    await db.commit()

    resp = JSONResponse(content={"anonimizado": True, "filas": tocadas})
    cookies.borrar(resp, cookies.ACCESO)
    cookies.borrar(resp, cookies.REFRESCO)
    return resp
