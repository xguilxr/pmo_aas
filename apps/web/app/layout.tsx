import type { ReactNode } from "react";
import { DM_Sans, JetBrains_Mono } from "next/font/google";
import { LocaleProvider } from "@/components/locale-provider";
import { ThemeProvider } from "@/components/theme-provider";
import "./globals.css";

// MCS SEG-01 · ASVS 10.3.2 — «integrity protections, such as code signing or
// subresource integrity».
//
// Antes esto eran tres `<link>` a `fonts.googleapis.com` y `fonts.gstatic.com`:
// una hoja de estilo de un tercero, sin `integrity`, con permiso para declarar
// de dónde bajar los tipos. Quien controlara ese origen —o el DNS del visitante—
// elegía qué CSS ejecutaba el navegador en toda la aplicación.
//
// **No se arregla con `integrity`,** y por eso no se intentó: Google devuelve un
// CSS distinto según el `User-Agent` para servir woff2 o ttf, así que un hash
// fijo rompería el sitio en cuanto cambiara el navegador del visitante. La forma
// correcta de dar integridad a un subrecurso que varía es dejar de pedírselo a
// un tercero.
//
// `next/font/google` descarga los tipos **en el build** y los sirve desde
// nuestro propio origen con los nombres con hash de Next. En ejecución no queda
// ni una petición a Google, así que tampoco queda nada que firmar. De paso, la
// hoja de estilo bloqueante desaparece del `<head>` y ya no hay fuga del
// `Referer` de cada visitante hacia un tercero.
//
// El trinquete que impide que vuelva a entrar un subrecurso externo sin
// integridad es `scripts/check_subrecursos.py`, en el CI.
const fuenteSans = DM_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
  variable: "--font-dm-sans",
});

const fuenteMono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  display: "swap",
  variable: "--font-jetbrains-mono",
});

export const metadata = {
  title: "PMO-aaS",
  description: "Project Management Office as a Service",
};

// US-164: viewport explícito sin maximum-scale / user-scalable=no, para no
// bloquear el pinch-zoom de trackpad ni los atajos ⌘+/⌘-.
export const viewport = {
  width: "device-width",
  initialScale: 1,
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
    <html
      lang="es"
      className={`${fuenteSans.variable} ${fuenteMono.variable}`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body className="font-sans antialiased">
        <ThemeProvider>
          <LocaleProvider>{children}</LocaleProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
