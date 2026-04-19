export const dynamic = "force-dynamic";

export async function GET() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  let apiOk: boolean | null = null;
  if (apiUrl) {
    try {
      const r = await fetch(`${apiUrl}/health`, { cache: "no-store", signal: AbortSignal.timeout(3000) });
      apiOk = r.ok;
    } catch {
      apiOk = false;
    }
  }
  return Response.json({
    ok: true,
    web: true,
    api_ok: apiOk,
    api_url_configured: Boolean(apiUrl),
    time: new Date().toISOString(),
  });
}
