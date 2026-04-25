/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  async redirects() {
    return [
      // US-036: "Mi tenant" / "Panel del Tenant" / "Configuración" se
      // consolidan en /admin/tenant con tabs internos.
      {
        source: "/admin/supervision",
        destination: "/admin/tenant?tab=stats",
        permanent: true,
      },
      {
        source: "/admin/settings",
        destination: "/admin/tenant?tab=config",
        permanent: true,
      },
      // US-075 (DEC-022): recursos de negocio salen de /admin/* y
      // viven bajo /pmo/*. Redirects 301 mantienen bookmarks viejos
      // y deep-links de audit logs / emails generados pre-refactor.
      // El `:path*` captura todas las sub-rutas (ej. /admin/projects/123/plan
      // → /pmo/projects/123/plan).
      {
        source: "/admin/projects/:path*",
        destination: "/pmo/projects/:path*",
        permanent: true,
      },
      {
        source: "/admin/projects",
        destination: "/pmo/projects",
        permanent: true,
      },
      {
        source: "/admin/programs/:path*",
        destination: "/pmo/programs/:path*",
        permanent: true,
      },
      {
        source: "/admin/programs",
        destination: "/pmo/programs",
        permanent: true,
      },
      {
        source: "/admin/raid/:path*",
        destination: "/pmo/raid/:path*",
        permanent: true,
      },
      {
        source: "/admin/raid",
        destination: "/pmo/raid",
        permanent: true,
      },
      {
        source: "/admin/requests/:path*",
        destination: "/pmo/requests/:path*",
        permanent: true,
      },
      {
        source: "/admin/requests",
        destination: "/pmo/requests",
        permanent: true,
      },
      {
        source: "/admin/changes",
        destination: "/pmo/changes",
        permanent: true,
      },
      {
        source: "/admin/minutes",
        destination: "/pmo/minutes",
        permanent: true,
      },
      {
        source: "/admin/reports",
        destination: "/pmo/reports",
        permanent: true,
      },
      // US-077 (DEC-024): /admin/roles eliminado. Los permisos viven
      // en 5 capabilities admin (modelo capability-based). Redirect a
      // /admin/permissions (página informativa read-only de US-078) o
      // /admin/users si la página informativa aún no se desplegó.
      {
        source: "/admin/roles/:path*",
        destination: "/admin/permissions",
        permanent: true,
      },
      {
        source: "/admin/roles",
        destination: "/admin/permissions",
        permanent: true,
      },
    ];
  },
};
module.exports = nextConfig;
