export default function HomePage() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "";
  return (
    <main style={{ padding: "48px", maxWidth: 720, margin: "0 auto" }}>
      <h1 style={{ fontSize: 32, fontWeight: 600 }}>PMO-aaS</h1>
      <p style={{ color: "#555" }}>Project Management Office — desplegado en Railway.</p>
      <p style={{ color: "#777", fontSize: 14 }}>API: {apiUrl || "not configured"}</p>
      <a href="/login" style={{ display: "inline-block", marginTop: 16, padding: "10px 16px", background: "#111", color: "#fff", borderRadius: 8, textDecoration: "none" }}>
        Iniciar sesión
      </a>
    </main>
  );
}
