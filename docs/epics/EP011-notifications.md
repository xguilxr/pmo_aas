---
tipo: epica
responsable: propietario
estado: vigente
revisado: 2026-05-08
revisar_cada: 90d
---

# EP011 — Sistema de Notificaciones

| Campo | Valor |
|---|---|
| **ID** | EP011 |
| **Prioridad** | POST-MVP |
| **Dependencias** | EP001, EP003, EP005, EP006 |
| **Módulo** | `notifications` |
| **Estado** | Entregada — como trabajo operativo (notifications.py, notification-bell.tsx); ver índice |
| **Versión objetivo** | v1.1 |

## Objetivo de negocio

Mantener a los usuarios informados sobre eventos relevantes sin que tengan que revisar activamente cada módulo. Notificaciones in-app (bell icon en topbar) + email via Resend.

## Tipos de notificación

| Tipo | Trigger | Destinatario |
|---|---|---|
| `request_approved` | Solicitud aprobada | Solicitante |
| `request_rejected` | Solicitud rechazada | Solicitante |
| `request_needs_info` | Solicitud devuelta | Solicitante |
| `pm_assigned` | PM asignado a proyecto | PM nuevo |
| `pm_removed` | PM removido | PM anterior |
| `phase_changed` | Proyecto cambia de fase | Team del proyecto |
| `aid_overdue` | AID vencida | Owner del AID |
| `risk_high` | Riesgo con severidad ≥ 13 creado | PM del proyecto |
| `change_pending` | Cambio en revisión | PMO Manager |
| `minute_generated` | Minuta IA lista para revisar | PM |
| `report_sent` | Reporte enviado | PM (confirmación) |

---

## # PENDING — US-027 — Tabla notifications + in-app notification center

**Como** usuario autenticado
**Quiero** ver mis notificaciones en un panel dentro del topbar
**Para** enterarme de eventos importantes sin revisar cada módulo.

**Criterios de aceptación:**
- [ ] Bell icon en topbar con badge de count de no leídas.
- [ ] Click en bell abre dropdown con últimas 20 notificaciones.
- [ ] Cada notificación: ícono de tipo, título, tiempo relativo, link.
- [ ] Click en notificación → navega al objeto relacionado + marca como leída.
- [ ] "Marcar todas como leídas" en el dropdown.
- [ ] Ver todas → `/notifications` con lista completa paginada y filtros.
- [ ] Badge desaparece cuando count = 0.
- [ ] Tabla `notifications` según DB-CHANGES.md.
- [ ] Endpoint `GET /api/v1/notifications?is_read=&page=&limit=`.
- [ ] Endpoint `POST /api/v1/notifications/{id}/read`.
- [ ] Endpoint `POST /api/v1/notifications/read-all`.
- [ ] Endpoint `GET /api/v1/notifications/unread-count` — caché 30s.

**Test Cases:**
- `TC-NEW-020` (integration) — Aprobar solicitud → crea notificación para solicitante.
- `TC-NEW-021` (E2E) — Badge muestra count correcto, desaparece al marcar todas.
- `TC-NEW-022` (integration) — Cross-tenant: user A no ve notificaciones de tenant B.

---

## # PENDING — US-028 — Email notifications via Resend

**Como** usuario
**Quiero** recibir emails para eventos críticos
**Para** no perder notificaciones importantes aunque no esté en la app.

**Criterios de aceptación:**
- [ ] Emails para: `request_approved/rejected`, `pm_assigned`, `aid_overdue` (resumen diario).
- [ ] Template HTML responsive con branding del tenant (logo + color).
- [ ] Unsubscribe link en cada email (preferencias por tipo).
- [ ] `users.notification_preferences JSONB` — qué tipos recibe por email.
- [ ] No enviar email si ya fue leído in-app en últimas 2h (evitar spam).
- [ ] Resend webhook para tracking de apertura (post-MVP).

**Test Cases:**
- `TC-NEW-023` (integration) — Email enviado con template correcto (mailcatcher).
- `TC-NEW-024` (integration) — User con tipo deshabilitado no recibe email.

---

## Definition of Done

- [ ] Bell icon en topbar funcional con badge.
- [ ] Dropdown de notificaciones con navegación.
- [ ] Al menos 5 tipos de notificación implementados.
- [ ] Email para tipos críticos funcionando con Resend.
- [ ] Preferencias de notificación por usuario.
