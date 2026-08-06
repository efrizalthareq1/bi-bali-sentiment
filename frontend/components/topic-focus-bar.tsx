"use client";

type FocusTopic = {
  id: string;
  label: string;
  keyword: string;
  q?: string;
};

const TOPICS: FocusTopic[] = [
  {
    id: "qris-summer",
    label: "QRIS Summer Run",
    keyword: "QRIS Summer Run",
    q: "QRIS Summer Run OR QRIS Summer OR qrissummerrun OR QRIS Run OR @qrissummerrun",
  },
  {
    id: "qris",
    label: "QRIS",
    keyword: "QRIS",
  },
  {
    id: "inflasi",
    label: "Inflasi",
    keyword: "inflasi",
  },
  {
    id: "gpips",
    label: "GPIPS",
    keyword: "GPIPS",
  },
  {
    id: "bi-bali",
    label: "BI Bali",
    keyword: "BI Bali",
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
        const active =
          activeKeyword?.toLowerCase() === topic.keyword.toLowerCase() ||
          (topic.id === "qris-summer" &&
            Boolean(
              activeKeyword &&
                /qris summer|qris run|qrissummerrun/i.test(activeKeyword)
            ));
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
