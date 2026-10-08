import type { Metadata } from "next";
import { DM_Sans, Fraunces } from "next/font/google";
import { AppNav } from "@/components/app-nav";
import "./globals.css";

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-dm-sans",
});

const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-fraunces",
});

export const metadata: Metadata = {
  title: "Sentimen KPwBI Aceh",
  description:
    "Dashboard analisis sentimen publik terhadap Bank Indonesia Kantor Perwakilan Provinsi Aceh",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="id" style={{ colorScheme: "light" }}>
      <body className={`${dmSans.variable} ${fraunces.variable} font-sans antialiased`}>
        <AppNav />
        <main>{children}</main>
      </body>
    </html>
  );
}
