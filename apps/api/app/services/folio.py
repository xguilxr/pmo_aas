from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project_request import FolioSequence


async def next_folio(db: AsyncSession, *, tenant_id: UUID, prefix: str, year: int | None = None) -> str:
    year = year or datetime.now(UTC).year
    seq = (
        await db.execute(
            select(FolioSequence).where(
                FolioSequence.tenant_id == str(tenant_id),
                FolioSequence.prefix == prefix,
                FolioSequence.year == year,
            ).with_for_update() if db.bind.dialect.name == "postgresql" else
            select(FolioSequence).where(
                FolioSequence.tenant_id == str(tenant_id),
                FolioSequence.prefix == prefix,
                FolioSequence.year == year,
            )
        )
    ).scalar_one_or_none()
    if seq is None:
        seq = FolioSequence(tenant_id=str(tenant_id), prefix=prefix, year=year, last_number=0)
        db.add(seq)
        await db.flush()
    seq.last_number += 1
    return f"{prefix}-{year}-{seq.last_number:03d}"
