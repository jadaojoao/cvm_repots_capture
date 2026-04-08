import type { ReactNode } from "react";
import type { Metadata } from "next";
import { IBM_Plex_Mono, Manrope, Space_Grotesk } from "next/font/google";

import { Providers } from "@/components/providers";
import { SiteFooter } from "@/components/shared/site-footer";
import { SiteHeader } from "@/components/shared/site-header";
import "./globals.css";

const bodyFont = Manrope({
  variable: "--font-body",
  subsets: ["latin"],
});

const headingFont = Space_Grotesk({
  variable: "--font-heading",
  subsets: ["latin"],
});

const monoFont = IBM_Plex_Mono({
  variable: "--font-mono",
  weight: ["400", "500"],
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "CVM Analytics",
    template: "%s | CVM Analytics",
  },
  description:
    "Plataforma publica de analise financeira com dados da CVM para descoberta rapida, leitura historica e navegacao por empresas.",
};

type RootLayoutProps = {
  children: ReactNode;
};

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html
      lang="pt-BR"
      suppressHydrationWarning
      className={`${bodyFont.variable} ${headingFont.variable} ${monoFont.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-background text-foreground">
        <Providers>
          <div className="relative flex min-h-screen flex-col overflow-x-hidden">
            <div className="pointer-events-none absolute inset-x-0 top-0 -z-30 h-[28rem] overflow-hidden sm:h-[34rem] lg:h-[39rem]">
              <video
                autoPlay
                loop
                muted
                playsInline
                preload="auto"
                aria-hidden="true"
                className="absolute inset-0 h-full w-full scale-105 object-cover opacity-24 saturate-[0.72] brightness-[0.72]"
              >
                <source
                  src="/ambient/abstract-loop-background.mp4"
                  type="video/mp4"
                />
              </video>
              <div className="absolute inset-0 bg-[linear-gradient(180deg,_rgba(12,15,14,0.76)_0%,_rgba(14,17,16,0.64)_38%,_rgba(16,20,18,0.28)_68%,_rgba(16,20,18,0)_100%)]" />
            </div>
            <div className="pointer-events-none absolute inset-x-0 top-0 -z-20 h-[30rem] bg-[radial-gradient(circle_at_top_left,_rgba(183,110,44,0.12),_transparent_28%),radial-gradient(circle_at_top_right,_rgba(19,71,52,0.12),_transparent_26%),linear-gradient(180deg,_rgba(14,16,15,0.18)_0%,_rgba(14,16,15,0.08)_46%,_rgba(14,16,15,0)_100%)] sm:h-[36rem] lg:h-[41rem]" />
            <div className="pointer-events-none absolute inset-0 -z-10 bg-[linear-gradient(rgba(33,39,33,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(33,39,33,0.03)_1px,transparent_1px)] bg-[size:52px_52px] [mask-image:linear-gradient(to_bottom,white_20%,transparent_95%)]" />
            <SiteHeader />
            <main className="flex-1">{children}</main>
            <SiteFooter />
          </div>
        </Providers>
      </body>
    </html>
  );
}
