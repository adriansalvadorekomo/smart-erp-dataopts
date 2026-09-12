import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileText, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface Doc {
  document_id: number;
  filename: string;
  mime_type: string;
  size_bytes: number;
  status: "uploaded" | "ready" | "failed";
  error: string | null;
}

interface Hit {
  document: string;
  chunk_index: number;
  content: string;
  score: number;
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, init);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(typeof body?.detail === "string" ? body.detail : `Request failed (${res.status})`);
  return body as T;
}

const listDocs = () => api<Doc[]>("/documents");
const searchDocs = (query: string, k = 5) =>
  api<Hit[]>("/documents/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, k }),
  });

export default function Documents() {
  const qc = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<Hit[] | null>(null);
  const docs = useQuery({ queryKey: ["documents"], queryFn: listDocs, refetchInterval: 5000 });

  const upload = useMutation({
    mutationFn: async (f: File) => {
      const form = new FormData();
      form.append("file", f);
      return api<Doc>("/documents", { method: "POST", body: form });
    },
    onSuccess: () => {
      setFile(null);
      setError(null);
      qc.invalidateQueries({ queryKey: ["documents"] });
    },
    onError: (e) => setError(e instanceof Error ? e.message : "Upload failed"),
  });

  const remove = useMutation({
    mutationFn: (id: number) => api(`/documents/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["documents"] }),
    onError: (e) => setError(e instanceof Error ? e.message : "Delete failed"),
  });

  async function search(e: React.FormEvent) {
    e.preventDefault();
    if (!q.trim()) return;
    setError(null);
    try {
      setHits(await searchDocs(q.trim()));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed");
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-[32px] font-semibold tracking-tight">Documents</h1>
        <p className="mt-1 text-[15px] text-muted-foreground">
          Attach business documents (PDF, Markdown, text, CSV — 20 MB max). They are
          parsed, chunked and embedded for grounded insights; retrieval below previews matches.
        </p>
      </div>

      <Card className="border-border/60 shadow-sm">
        <CardContent className="flex flex-wrap items-center gap-3 pt-6">
          <Input
            type="file"
            accept=".pdf,.md,.markdown,.txt,.csv"
            aria-label="Choose document"
            className="max-w-sm"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
          <Button
            className="rounded-full"
            disabled={!file || upload.isPending}
            onClick={() => file && upload.mutate(file)}
          >
            {upload.isPending ? "Uploading…" : "Attach"}
          </Button>
          {error && <p className="w-full text-[15px] text-destructive">{error}</p>}
        </CardContent>
      </Card>

      <Card className="overflow-hidden border-border/60 shadow-sm">
        <CardHeader>
          <CardTitle className="text-[15px] font-semibold">Attached</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="text-xs font-medium uppercase tracking-wide">File</TableHead>
                <TableHead className="text-right text-xs font-medium uppercase tracking-wide">Size</TableHead>
                <TableHead className="text-xs font-medium uppercase tracking-wide">Status</TableHead>
                <TableHead className="text-right text-xs font-medium uppercase tracking-wide">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(docs.data ?? []).map((d) => (
                <TableRow key={d.document_id}>
                  <TableCell>
                    <span className="inline-flex items-center gap-2 font-medium">
                      <FileText size={15} className="text-muted-foreground" />
                      {d.filename}
                    </span>
                    {d.error && <p className="mt-0.5 text-xs text-destructive">{d.error}</p>}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {(d.size_bytes / 1024).toFixed(1)} KB
                  </TableCell>
                  <TableCell>
                    <Badge variant={d.status === "ready" ? "default" : d.status === "failed" ? "destructive" : "secondary"}>
                      {d.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <Button variant="ghost" size="sm" aria-label={`Delete ${d.filename}`} onClick={() => remove.mutate(d.document_id)}>
                      <Trash2 size={15} />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {docs.data?.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} className="py-10 text-center text-muted-foreground">
                    Nothing attached yet.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card className="border-border/60 shadow-sm">
        <CardHeader>
          <CardTitle className="text-[15px] font-semibold">Try retrieval</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <form className="flex gap-2" onSubmit={search}>
            <Input
              placeholder="e.g. return policy for electronics"
              aria-label="Search documents"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            <Button type="submit" className="rounded-xl">Search</Button>
          </form>
          {hits && (
            <div className="space-y-3">
              {hits.length === 0 && <p className="text-[15px] text-muted-foreground">No matches.</p>}
              {hits.map((h, i) => (
                <div key={i} className="rounded-xl border border-border/60 p-4">
                  <p className="text-[13px] font-medium text-muted-foreground tabular-nums">
                    {h.document} · chunk {h.chunk_index} · score {h.score.toFixed(3)}
                  </p>
                  <p className="mt-1 text-[15px] leading-relaxed">{h.content.slice(0, 400)}{h.content.length > 400 ? "…" : ""}</p>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
