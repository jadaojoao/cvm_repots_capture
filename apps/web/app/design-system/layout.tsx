import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Design System",
  description:
    "Catalogo interno de tokens, componentes e recipes visuais que orientam a UI do CVM Analytics.",
};

export default function DesignSystemLayout({
  children,
}: LayoutProps<"/design-system">) {
  return <>{children}</>;
}
