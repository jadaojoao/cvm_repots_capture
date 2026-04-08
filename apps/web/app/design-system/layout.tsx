import type { ReactNode } from "react";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Design System",
  description:
    "Catalogo interno de tokens, componentes e recipes visuais que orientam a UI do CVM Analytics.",
};

type DesignSystemLayoutProps = {
  children: ReactNode;
};

export default function DesignSystemLayout({
  children,
}: DesignSystemLayoutProps) {
  return <>{children}</>;
}
