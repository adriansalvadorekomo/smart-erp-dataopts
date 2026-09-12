import { useState } from "react";
import { Link } from "react-router-dom";
import { SendHorizontal, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

interface Source {
  endpoint: string;
  params: Record<string, unknown>;
  document?: string | null;
  chunk_index?: number | null;
  score?: number | null;
}

interface AskResult {
  answer: string;
  intent: string;
  sources: Source[];
  sql?: string;
  rows?: Record<string, unknown>[];
}

type Mode = "data" | "docs" | "genie";

const MODES: { id: Mode; label: string; hint: string }[] = [
  { id: "data", label: "Data", hint: "Computed answers over OLTP + forecasts" },
  { id: "docs", label: "Documents", hint: "Grounded in your attached documents" },
  { id: "genie", label: "Genie", hint: "Databricks SQL over Gold (needs Space)" },
];

const EXAMPLES: Record<Mode, string[]> = {
  data: [
    "What is total revenue?",
    "Top 5 sellers?",
    "Which products need reordering?",
    "Forecast revenue next month",
    "Is data quality green?",
    "Revenue by region",
  ],
  docs: [
    "What drove growth in Q1?",
    "Summarize the attached reports",
  ],
  genie: [
    "Total revenue by month",
    "Return rate by category",
  ],
};

async function ask(mode: Mode, question: string): Promise<AskResult> {
  const path = mode === "data" ? "/api/ai/ask" : mode === "docs" ? "/api/ai/ask-docs" : "/api/ai/ask-genie";
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(typeof body?.detail === "string" ? body.detail : "Ask failed");
  return body as AskResult;
}

export default function Assistant() {
  const [mode, setMode] = useState<Mode>("data");
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AskResult | null>(null);

  async function submit(question: string) {
    const text = question.trim();
    if (!text || busy) return;
    setBusy(true);
    setError(null);
    try {
      setResult(await ask(mode, text));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ask failed");
      setResult(null);
    } finally {
      setBusy(false);
    }
  }

  function switchMode(m: Mode) {
    setMode(m);
    setResult(null);
    setError(null);
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="inline-flex items-center gap-2 text-[32px] font-semibold tracking-tight">
          <Sparkles size={26} strokeWidth={1.75} /> Ask
        </h1>
        <p className="mt-1 text-[15px] text-muted-foreground">
          {MODES.find((m) => m.id === mode)?.hint} — every reply cites its sources. No guessing.
        </p>
      </div>

      <div className="inline-flex rounded-full bg-secondary p-1">
        {MODES.map((m) => (
          <button
            key={m.id}
            type="button"
            onClick={() => switchMode(m.id)}
            className={`rounded-full px-3.5 py-1.5 text-[13px] font-medium transition-all ${
              mode === m.id
                ? "bg-card text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {m.label}
          </button>
        ))}
      </div>

      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          submit(q);
        }}
      >
        <Input
          placeholder="e.g. Which sellers need attention?"
          aria-label="Ask a business question"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <Button type="submit" className="rounded-xl" disabled={busy} aria-label="Ask">
          <SendHorizontal size={16} />
        </Button>
      </form>

      <div className="flex flex-wrap gap-2">
        {EXAMPLES[mode].map((ex) => (
          <button
            key={ex}
            type="button"
            onClick={() => {
              setQ(ex);
              submit(ex);
            }}
            className="rounded-full bg-secondary px-3 py-1.5 text-[13px] font-medium text-secondary-foreground transition-colors hover:bg-accent"
          >
            {ex}
          </button>
        ))}
      </div>

      {error && <p className="text-[15px] text-destructive">{error}</p>}

      {result && (
        <Card className="border-border/60 shadow-sm">
          <CardContent className="space-y-4 pt-6">
            <p className="text-[17px] leading-relaxed">{result.answer}</p>
            {result.sql && (
              <pre className="overflow-x-auto rounded-xl bg-secondary p-3 font-mono text-xs text-secondary-foreground">
                {result.sql}
              </pre>
            )}
            {result.rows && result.rows.length > 0 && (
              <p className="text-[13px] tabular-nums text-muted-foreground">
                {result.rows.length} row(s), first:{" "}
                {Object.entries(result.rows[0]).slice(0, 3).map(([k, v]) => `${k}=${v}`).join(", ")}
              </p>
            )}
            <div className="flex flex-wrap items-center gap-2 border-t border-border/60 pt-3">
              <span className="text-[13px] text-muted-foreground">Sources:</span>
              {result.sources.length > 0 ? (
                result.sources.map((s, i) => (
                  <code key={`${s.endpoint}-${i}`} className="rounded-md bg-secondary px-2 py-1 font-mono text-xs text-secondary-foreground">
                    {s.document ? `${s.document}#${s.chunk_index} (${s.score})` : s.endpoint}
                  </code>
                ))
              ) : (
                <span className="text-[13px] text-muted-foreground">none — try an example above</span>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      <p className="text-[13px] text-muted-foreground">
        Grounded in OLTP + batch forecasts today; governed Gold next.{" "}
        <Link to="/pipeline" className="text-primary hover:underline">
          Pipeline status →
        </Link>
      </p>
    </div>
  );
}
