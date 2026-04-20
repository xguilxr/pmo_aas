import type { ReactNode } from "react";
import { ThemeProvider } from "@/components/theme-provider";
import "./globals.css";

export const metadata = {
  title: "PMO-aaS",
  description: "Project Management Office as a Service",
};

// Script blocking para evitar flash of unstyled theme (FOUT): se ejecuta antes
// de hidratar React, lee pmoaas.theme de localStorage y aplica .dark al <html>.
const THEME_INIT_SCRIPT = `
(function(){try{
  var t = localStorage.getItem('pmoaas.theme');
  var dark = t === 'dark' || (t !== 'light' && window.matchMedia('(prefers-color-scheme: dark)').matches);
  var resolved = dark ? 'dark' : 'light';
  var r = document.documentElement;
  if (dark) r.classList.add('dark'); else r.classList.remove('dark');
  r.dataset.theme = resolved;
}catch(e){}})();
`;

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body className="font-sans antialiased">
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
