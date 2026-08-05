"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, Database, Home } from "lucide-react";
import { cn } from "@/lib/utils";

const links = [
  { href: "/", label: "Beranda", icon: Home },
  { href: "/dashboard", label: "Dashboard", icon: BarChart3 },
  { href: "/sumber-data", label: "Sumber Data", icon: Database },
];

export function AppNav() {
  const pathname = usePathname();
  return (
    <header className="sticky top-0 z-40 border-b border-border/80 bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
        <Link href="/" className="group flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-sm font-bold text-primary-foreground shadow-sm">
            BI
          </div>
          <div className="leading-tight">
            <p className="font-display text-base font-semibold text-foreground group-hover:text-primary">
              Sentimen KPwBI Bali
            </p>
            <p className="hidden text-xs text-muted-foreground sm:block">
              Monitoring percakapan publik
            </p>
          </div>
        </Link>
        <nav className="flex items-center gap-1">
          {links.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || (href !== "/" && pathname.startsWith(href));
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition",
                  active
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
              >
                <Icon className="h-4 w-4" />
                <span className="hidden sm:inline">{label}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
