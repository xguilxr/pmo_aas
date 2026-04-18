import type { ReactNode } from "react";

export const metadata = {
  title: "PMO-aaS",
  description: "Project Management Office as a Service",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es">
      <body style={{ fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro', 'Inter', sans-serif", margin: 0 }}>
        {children}
      </body>
    </html>
  );
}
