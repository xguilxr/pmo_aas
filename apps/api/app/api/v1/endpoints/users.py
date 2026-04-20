"""Endpoints self-service para el usuario autenticado (`/users/me/...`).

US-NEW-007: preferencia de tema (dark/light/system).
US-NEW-009: perfil personal (full_name) + preferencias.
"""
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.api.deps import CurrentUser, get_current_user
from app.db.session import get_db
from app.services.audit import write_audit

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
