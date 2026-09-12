import { useState } from "react";
import { Link } from "react-router-dom";
import { SendHorizontal, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

interface Source {
  endpoint: string;
  params: Record<string, unknown>;
}

interface AskResult {
  answer: string;
  intent: string;
  sources: Source[];
}

const EXAMPLES = [
  "What is total revenue?",
  "Top 5 sellers?",
  "Which products need reordering?",
  "Forecast revenue next month",
  "Is data quality green?",
  "Revenue by region",
];

async function ask(question: string): Promise<AskResult> {
  const res = await fetch("/api/ai/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(typeof body?.detail === "string" ? body.detail : "Ask failed");
  return body as AskResult;
}

export default function Assistant() {
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
      setResult(await ask(text));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ask failed");
      setResult(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="inline-flex items-center gap-2 text-[32px] font-semibold tracking-tight">
          <Sparkles size={26} strokeWidth={1.75} /> Ask
        </h1>
        <p className="mt-1 text-[15px] text-muted-foreground">
          Answers computed live from governed data — every reply cites its sources. No guessing.
        </p>
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
        {EXAMPLES.map((ex) => (
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
            <div className="flex flex-wrap items-center gap-2 border-t border-border/60 pt-3">
              <span className="text-[13px] text-muted-foreground">Sources:</span>
              {result.sources.length > 0 ? (
                result.sources.map((s) => (
                  <code key={s.endpoint} className="rounded-md bg-secondary px-2 py-1 font-mono text-xs text-secondary-foreground">
                    {s.endpoint}
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
