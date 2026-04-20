/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  async redirects() {
    return [
      // US-NEW-036: "Mi tenant" / "Panel del Tenant" / "Configuración" se
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
    ];
  },
};
module.exports = nextConfig;
