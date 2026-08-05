import Link from "next/link";
import { ArrowRight, Newspaper, Shield, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 sm:py-16">
      <section className="relative overflow-hidden rounded-3xl border border-border bg-gradient-to-br from-zinc-950 via-black to-zinc-900 px-6 py-14 text-white shadow-lg sm:px-12 sm:py-20">
        <div className="pointer-events-none absolute -right-16 top-0 h-64 w-64 rounded-full bg-teal-400/15 blur-3xl" />
        <div className="pointer-events-none absolute bottom-0 left-10 h-48 w-48 rounded-full bg-white/5 blur-3xl" />
        <p className="text-sm font-medium uppercase tracking-[0.2em] text-teal-300/90">
          Bank Indonesia · KPwBI Bali
        </p>
        <h1 className="mt-4 max-w-3xl font-display text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">
          Sentimen KPwBI Bali
        </h1>
        <p className="mt-4 max-w-2xl text-base leading-relaxed text-zinc-300 sm:text-lg">
          Pantau dan analisis percakapan publik seputar kebijakan, program, dan pemberitaan
          Bank Indonesia Provinsi Bali — dari inflasi, UMKM, QRIS, hingga penukaran uang
          rupiah.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link href="/dashboard">
            <Button size="lg" className="bg-white text-black hover:bg-zinc-200">
              Buka Dashboard <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
          <Link href="/sumber-data">
            <Button
              size="lg"
              variant="outline"
              className="border-white/25 bg-transparent text-white hover:bg-white/10"
            >
              Kelola Sumber Data
            </Button>
          </Link>
        </div>
      </section>

      <section className="mt-10 grid gap-4 md:grid-cols-3">
        {[
          {
            icon: Newspaper,
            title: "Ingestion modular",
            body: "Mulai dari berita RSS & upload CSV/Excel yang legal, lalu sambungkan API X, Instagram, dan TikTok saat siap.",
          },
          {
            icon: Sparkles,
            title: "Mesin sentimen bilingual",
            body: "Klasifikasi via LLM (Claude/OpenAI) dengan cadangan leksikon Bahasa Indonesia (InSet) untuk mode offline.",
          },
          {
            icon: Shield,
            title: "Drill-down yang jelas",
            body: "Dari tren agregat ke post individual: filter platform, sentimen, keyword, dan alasan klasifikasi.",
          },
        ].map((item) => (
          <div
            key={item.title}
            className="rounded-2xl border border-border bg-card/90 p-5 shadow-sm"
          >
            <item.icon className="h-5 w-5 text-primary" />
            <h2 className="mt-3 font-display text-lg font-semibold">{item.title}</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{item.body}</p>
          </div>
        ))}
      </section>
    </div>
  );
}
