import { FormEvent, useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

type Node = { id: string; type: string; name: string; file_path: string; start_line: number; end_line: number; language: string };
type Edge = { source: string; target: string; type: string; resolution: string; source_file: string; source_line: number };
type Status = { repo_id: string; status: "queued" | "processing" | "completed" | "failed"; progress: number; current_stage: string; error?: string | null };
type Graph = { nodes: Node[]; edges: Edge[] };
const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, { headers: { "Content-Type": "application/json" }, ...init });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.error?.message ?? body?.detail ?? `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

function App() {
  const [repoUrl, setRepoUrl] = useState("https://github.com/facebook/react");
  const [branch, setBranch] = useState("main");
  const [repoId, setRepoId] = useState("");
  const [status, setStatus] = useState<Status | null>(null);
  const [graph, setGraph] = useState<Graph>({ nodes: [], edges: [] });
  const [selected, setSelected] = useState<Node | null>(null);
  const [query, setQuery] = useState("");
  const [issueUrl, setIssueUrl] = useState("");
  const [insight, setInsight] = useState<string>("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!repoId || status?.status === "completed" || status?.status === "failed") return;
    const poll = async () => {
      try {
        const nextStatus = await request<Status>(`/api/repos/${repoId}/status`);
        setStatus(nextStatus);
        if (nextStatus.status === "failed") setError(nextStatus.error || "Indexing failed. Please try another repository or branch.");
      } catch (err) { setError(err instanceof Error ? err.message : "Unable to check indexing status"); }
    };
    poll(); const timer = window.setInterval(poll, 1800); return () => window.clearInterval(timer);
  }, [repoId, status?.status]);

  useEffect(() => {
    if (status?.status !== "completed" || !repoId) return;
    request<Graph>(`/api/repos/${repoId}/graph`).then(setGraph).catch(err => setError(err.message));
  }, [repoId, status?.status]);

  const visibleNodes = useMemo(() => graph.nodes.filter(node => `${node.name} ${node.file_path}`.toLowerCase().includes(query.toLowerCase())), [graph, query]);
  const visibleIds = new Set(visibleNodes.map(node => node.id));
  const visibleEdges = graph.edges.filter(edge => visibleIds.has(edge.source) && visibleIds.has(edge.target));

  async function index(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(""); setGraph({ nodes: [], edges: [] }); setSelected(null);
    try { const result = await request<{ repo_id: string }>("/api/repos/index", { method: "POST", body: JSON.stringify({ repo_url: repoUrl, branch }) }); setRepoId(result.repo_id); setStatus({ repo_id: result.repo_id, status: "queued", progress: 0, current_stage: "queued" }); }
    catch (err) { setError(err instanceof Error ? err.message : "Could not index repository"); }
    finally { setBusy(false); }
  }
  async function runImpact() {
    if (!repoId || !selected) return;
    setBusy(true); setError("");
    try { const result = await request<any>(`/api/repos/${repoId}/impact`, { method: "POST", body: JSON.stringify({ symbol_id: selected.id, depth: 2 }) }); setInsight(`Impact analysis for ${selected.name}\n\nDirect callers: ${result.direct_callers?.length ?? 0}\nDependent modules: ${result.dependent_modules?.length ?? 0}\nRelated tests: ${result.related_tests?.length ?? 0}\n\n${(result.limitations ?? []).join("\n")}`); }
    catch (err) { setError(err instanceof Error ? err.message : "Impact analysis failed"); } finally { setBusy(false); }
  }
  async function investigate() {
    if (!repoId || !issueUrl) return;
    setBusy(true); setError("");
    try { const result = await request<any>(`/api/repos/${repoId}/issues/analyze`, { method: "POST", body: JSON.stringify({ issue_url: issueUrl }) }); setInsight(`Issue investigation\n\n${(result.results ?? []).map((item: any, index: number) => `${index + 1}. ${item.name ?? item.file_path ?? "Relevant component"}`).join("\n") || "No matching components returned."}`); }
    catch (err) { setError(err instanceof Error ? err.message : "Issue investigation failed"); } finally { setBusy(false); }
  }

  return <main>
    <nav><div className="brand"><span className="mark">↗</span><span>CODEBASE GPS</span></div><span className="status-dot">{status?.status ?? "READY"}</span></nav>
    <section className="hero"><p className="eyebrow">OPEN SOURCE NAVIGATION SYSTEM</p><h1>Know where<br/>your code goes.</h1><p>Index an unfamiliar repository, trace its relationships, and investigate changes with confidence.</p></section>
    <section className="import-panel">
      <form onSubmit={index}><label>GITHUB REPOSITORY<input value={repoUrl} onChange={e => setRepoUrl(e.target.value)} placeholder="https://github.com/owner/repo"/></label><label>BRANCH<input value={branch} onChange={e => setBranch(e.target.value)} placeholder="main"/></label><button disabled={busy || status?.status === "queued" || status?.status === "processing"}>{busy ? "WORKING…" : status?.status === "queued" || status?.status === "processing" ? "INDEXING…" : "MAP CODEBASE →"}</button></form>
      {status && <div className="progress"><div><b>{status.current_stage.replaceAll("_", " ")}</b><span>{status.progress}%</span></div><i><em style={{ width: `${status.progress}%` }}/></i></div>}
      {error && <p className="error">{error}</p>}
    </section>
    <section className="workspace">
      <aside className="sidebar"><div className="panel-title">EXPLORER <small>{graph.nodes.length} NODES</small></div><input className="search" value={query} onChange={e => setQuery(e.target.value)} placeholder="Filter symbols…"/>
        <div className="nodes">{visibleNodes.map(node => <button className={selected?.id === node.id ? "node active" : "node"} key={node.id} onClick={() => setSelected(node)}><span className={`type ${node.type.toLowerCase()}`}>{node.type.slice(0, 3)}</span><span><b>{node.name}</b><small>{node.file_path}:{node.start_line}</small></span></button>)}{!graph.nodes.length && <p className="empty">Your code map will appear here after indexing.</p>}</div>
      </aside>
      <section className="map"><div className="map-header"><div><span className="lime-square"/>DEPENDENCY MAP</div><span>{visibleEdges.length} RELATIONSHIPS</span></div><div className="graph">{visibleNodes.slice(0, 18).map((node, index) => <button key={node.id} onClick={() => setSelected(node)} className={`graph-node ${selected?.id === node.id ? "selected" : ""}`} style={{ left: `${8 + (index % 4) * 24}%`, top: `${12 + Math.floor(index / 4) * 22}%` }}><span>{node.type}</span>{node.name}</button>)}{graph.nodes.length > 18 && <p className="graph-more">+ {graph.nodes.length - 18} more nodes</p>} {!graph.nodes.length && <div className="radar">+</div>}</div></section>
      <aside className="inspector"><div className="panel-title">INSPECTOR</div>{selected ? <><p className="selected-name">{selected.name}</p><dl><dt>TYPE</dt><dd>{selected.type}</dd><dt>LOCATION</dt><dd>{selected.file_path}:{selected.start_line}–{selected.end_line}</dd><dt>LANGUAGE</dt><dd>{selected.language}</dd></dl><button className="outline" onClick={runImpact} disabled={busy}>ANALYZE IMPACT ↗</button></> : <p className="empty">Select a node to inspect its location and potential impact.</p>}<div className="issue"><label>INVESTIGATE ISSUE<input value={issueUrl} onChange={e => setIssueUrl(e.target.value)} placeholder="GitHub issue URL"/></label><button className="outline" onClick={investigate} disabled={!issueUrl || busy}>FIND RELEVANT CODE →</button></div></aside>
    </section>
    {insight && <section className="insight"><button onClick={() => setInsight("")}>×</button><pre>{insight}</pre></section>}
  </main>;
}
createRoot(document.getElementById("root")!).render(<App/>);
