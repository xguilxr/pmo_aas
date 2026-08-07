---
tipo: epica
responsable: propietario
estado: vigente
revisado: 2026-05-08
revisar_cada: 90d
---

# EP019 — Cambios / Approval workflow

| Campo | Valor |
|---|---|
| **ID** | EP019 |
| **Prioridad** | Alta — Sprint 22 |
| **Dependencias** | EP006 (RAID/Cambios), EP011 (notifications), EP017 (Áreas/Actores) |
| **Módulo** | `raid.changes`, `approvals`, `notifications.email`, `public.approval-landing` |
| **Estado** | # PENDING |
| **Versión objetivo** | v1.21 |

## Objetivo de negocio

Convertir los **Cambios** (ChangeRequests dentro del módulo RAID) en un flujo de aprobación formal con responsables externos. Hoy se registran como ítems planos; queremos:

1. Registrar uno o más **responsables de aprobación** por cambio (usualmente externos a la plataforma — sponsors, business owners, comité).
2. **Notificar por email** con la información del cambio + links firmados de "Aprobar" / "Rechazar".
3. Registrar la **acción del aprobador** sin requerir login en la plataforma (landing pública con token JWT firmado).
4. Si el cambio se **rechaza**, retriggerear el flujo (PM ajusta y reenvía).

## Decisiones arquitectónicas asociadas

- **DEC-Approval-token** — JWT firmado con expiry (default 30 días) + scope `change_id + approver_id + action`. Token de un solo uso (consumido al actuar).
- **DEC-Approval-landing** — Landing pública servida desde el dominio principal de la plataforma en una ruta `/approve/[token]` (no requiere subdominio separado en MVP).
- **DEC-Approval-rejected-retrigger** — Al rechazar, el cambio vuelve a status `draft`; el PM edita y al reenviar se invalidan los tokens previos y se generan nuevos.

## US iniciales

- **US-112** — Cambios: registrar responsables de aprobación (FK multi a actors + UI de gestión en el ticket).
- **US-113** — Cambios: workflow email — token firmado, landing pública, registrar acción, rechazo retriggera.

## Migraciones Alembic previstas

- `change_approvers` (change_id, actor_id, role, status, decided_at, decision_note).
- `approval_tokens` (token_hash, change_id, actor_id, action, expires_at, consumed_at).

## Out of scope EP019

- Aprobación jerárquica multi-nivel (es flat: todos los aprobadores reciben el email simultáneo).
- Delegación de aprobaciones.
- Quórum dinámico (puede agregarse post-MVP si los grupos lo piden).
- Aprobación de Charter / Riesgos / etc — el patrón se reusa, pero esos casos abren epics separados.
