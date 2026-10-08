"use client";

type FocusTopic = {
  id: string;
  label: string;
  keyword: string;
  q?: string;
};

const TOPICS: FocusTopic[] = [
  {
    id: "bi-aceh",
    label: "BI Aceh",
    keyword: "BI Aceh",
    q: "BI Aceh OR Bank Indonesia Aceh OR KPwBI Aceh OR #BIAceh",
  },
  {
    id: "qris-aceh",
    label: "QRIS Aceh",
    keyword: "QRIS Aceh",
  },
  {
    id: "inflasi-aceh",
    label: "Inflasi Aceh",
    keyword: "inflasi Aceh",
  },
  {
    id: "umkm-aceh",
    label: "UMKM Aceh",
    keyword: "UMKM Aceh",
  },
  {
    id: "syariah",
    label: "Ekonomi Syariah",
    keyword: "ekonomi syariah Aceh",
  },
];

type Props = {
  activeKeyword?: string;
  onSelect: (topic: { keyword: string; q?: string } | null) => void;
};

export function TopicFocusBar({ activeKeyword, onSelect }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-xs font-medium text-muted-foreground">Fokus topik:</span>
      <button
        type="button"
        onClick={() => onSelect(null)}
        className={`rounded-full border px-3 py-1.5 text-xs font-medium transition ${
          !activeKeyword
            ? "border-primary bg-primary text-primary-foreground"
            : "border-border bg-card text-muted-foreground hover:border-primary/40 hover:text-foreground"
        }`}
      >
        Semua
      </button>
      {TOPICS.map((topic) => {
        const active = activeKeyword?.toLowerCase() === topic.keyword.toLowerCase();
        return (
          <button
            key={topic.id}
            type="button"
            onClick={() => onSelect({ keyword: topic.keyword, q: topic.q })}
            className={`rounded-full border px-3 py-1.5 text-xs font-medium transition ${
              active
                ? "border-primary bg-primary/10 text-primary"
                : "border-border bg-card text-muted-foreground hover:border-primary/40 hover:text-foreground"
            }`}
          >
            {topic.label}
          </button>
        );
      })}
    </div>
  );
}
