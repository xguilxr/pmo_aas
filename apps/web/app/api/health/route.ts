export async function GET() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  let apiOk = false;
  if (apiUrl) {
    try {
      const r = await fetch(`${apiUrl}/health`, { cache: "no-store" });
      apiOk = r.ok;
    } catch {
      apiOk = false;
    }
  }
  return Response.json(
    { ok: apiOk, web: true, time: new Date().toISOString() },
    { status: apiOk ? 200 : 503 }
  );
}
