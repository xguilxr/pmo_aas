# Visión general del producto

**ID:** `DOC-OVERVIEW`
**Estado:** Aprobado
**Última revisión:** 2026-04-18

---

## 1. Misión

Ofrecer a oficinas de gestión de proyectos (PMO) una plataforma SaaS **multi-tenant, rápida y limpia** que centralice el ciclo de vida de proyectos: desde la solicitud inicial hasta el cierre, con trazabilidad total, IA para automatizar minutas y reportes, e integración con Microsoft Project.

## 2. Problemas que resolvemos

| Problema | Dolor actual | Cómo lo resolvemos |
|---|---|---|
| Dispersión de información | Excel + correos + SharePoint | Sistema único con jerarquía PMO→Org→Programa→Proyecto |
| Reportes manuales que consumen 4-6 h/semana | PM redacta en Word cada viernes | IA local genera reporte en <60 s, PM solo revisa |
| Minutas sin estructura | Notas libres sin acuerdos trazables | IA extrae acuerdos, participantes, próximos pasos desde transcripción |
| Visibilidad baja del portafolio | Dirección no ve estado real | Dashboard con KPIs, semáforo de salud, Plan vs Real |
| Aislamiento entre clientes | Instancias separadas caras | Multi-tenant con RLS en Postgres, 1 despliegue para N tenants |
| Dependencia de MS Project standalone | PM importa/exporta manual | Importación .mpp/.xml y Gantt nativo en la app |

## 3. Personas / Roles

| Rol | Acceso | Principales tareas |
|---|---|---|
| **Super Admin** | Platform-wide | Provisionar tenants, ver logs globales, asumir rol admin en cualquier tenant |
| **Administrador** (del tenant) | Su tenant | CRUD de usuarios, roles, organizaciones, proyectos del tenant |
| **PMO Manager** | Su tenant | Aprobar solicitudes, ver portafolio completo, priorizar |
| **Project Manager** | Proyectos asignados | Ejecutar proyecto, gestionar riesgos/incidencias/cambios, reportar |
| **Viewer / Stakeholder** | Proyectos asignados (read) | Ver avance, descargar reportes, consultar minutas |
| **Solicitante** (opcional) | Sólo form de solicitud | Crear solicitud de proyecto |

## 4. Alcance MVP vs Futuro

### MVP (v1.0, primer release en Railway)

- ✅ Auth + gestión de usuarios y roles (EP001)
- ✅ Jerarquía organizacional (EP002)
- ✅ Solicitud y aprobación de proyectos (EP003)
- ✅ Dashboard con KPIs + Plan vs Real (EP004)
- ✅ CRUD de proyectos (EP005)
- ✅ 6 módulos transversales (EP006)
- ✅ Panel de administración (EP007)
- ✅ IA: minutas desde transcripción + reportes (EP008) — modo Ollama local
- ✅ MS Project: importación .xml/.xlsx + Gantt read-only (EP009)
- ✅ Super Admin platform-wide

### Post-MVP (v1.1+)

- 🔜 Drag & drop en Gantt
- 🔜 Importación nativa .mpp (requiere MPXJ + Java runtime en Railway)
- 🔜 Preview de PDFs/imágenes inline
- 🔜 Mobile app (React Native / Expo)
- 🔜 Webhooks outbound para integraciones externas
- 🔜 SSO (SAML / OIDC)
- 🔜 Real-time colaborativo (Yjs) en minutas y documentos

## 5. Requerimientos no funcionales

| Categoría | Objetivo | Cómo medimos |
|---|---|---|
| Performance | p95 < 300 ms en listados, TTFB < 150 ms | Sentry Performance, Railway Metrics |
| Disponibilidad | 99.5% mensual | UptimeRobot hitting `/health` |
| Seguridad | OWASP Top 10, aislamiento estricto multi-tenant | Pen-test trimestral, TC-MT-* E2E en cada PR |
| Accesibilidad | WCAG 2.1 AA | `axe-core` en Playwright CI |
| Internacionalización | ES/EN desde día 1 | 100% claves en `i18n/` |
| Observabilidad | MTTD < 5 min para errores críticos | Alertas Sentry + Slack |
| Escalabilidad | 500 tenants, 50 proyectos/tenant, 100 usuarios concurrentes | Load test k6 antes de release |

## 6. Principios de diseño

1. **Limpio antes que potente.** Una feature bien pulida > cinco a medias.
2. **Velocidad percibida.** Skeletons, optimistic UI, RSC streaming. Nada de spinners en blanco.
3. **Estética Apple.** Tipografía clara, jerarquía visual fuerte, materiales (vibrancy/blur), movimiento suave.
4. **Multi-tenant by default.** Ningún endpoint olvida el `tenant_id`. Tests `TC-MT-*` bloquean merges.
5. **IA asistida, humano decide.** La IA genera borradores; el usuario siempre revisa y aprueba antes de enviar/guardar.
6. **Portabilidad del dato.** Todo exportable a CSV/Excel/JSON. Nada secuestrado por la plataforma.
7. **Simplicidad de deploy.** Un `git push` despliega. Variables en Railway, no en código.

## 7. KPIs del producto (para medir éxito)

- **TTFM (Time To First Minute AI-generated)**: < 5 min desde sign-up
- **Adopción de IA**: ≥ 60% de las minutas usan generación asistida al mes 3
- **Retención semanal de PMs**: ≥ 75% W4
- **Tiempo medio ahorrado por PM**: ≥ 3 h/semana (encuesta trimestral)
- **NPS interno**: ≥ 40 tras primer trimestre

## 8. Fuera de alcance (explícito)

- ❌ No somos un Jira/Linear para devs (no hay sprints ni board Kanban de tickets de código).
- ❌ No reemplazamos contabilidad/ERP — integramos, no facturamos.
- ❌ No hacemos videoconferencia — consumimos transcripciones, no audio.
- ❌ No entrenamos modelos propios — usamos Ollama/Claude con prompts cuidados.

## 9. Glosario corto

Ver [`glossary.md`](./glossary.md) para la lista completa. Términos clave:

- **Tenant** = cliente (organización que contrata el SaaS). Aísla datos.
- **Organización** = entidad dentro de un tenant (ej. subsidiaria, filial).
- **Programa** = agrupador de proyectos con objetivos estratégicos comunes.
- **Folio** = identificador auto-generado con prefijo (SOL-, PRJ-, …).
- **AID** = Acción / Incidencia / Decisión (sub-tipo del módulo Incidencias).
