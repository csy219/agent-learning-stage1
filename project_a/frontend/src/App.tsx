import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Coins,
  Database,
  FileText,
  GitBranch,
  LoaderCircle,
  MessageSquare,
  Send,
  Server,
  ShieldAlert,
  Upload,
} from "lucide-react";
import {
  type ChangeEvent,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  API_BASE_URL,
  askQuestion,
  createSession,
  getHealth,
  getReadiness,
  getTaskStatus,
  streamQuestion,
  uploadDocument,
} from "./api";
import { benchmarkSnapshot } from "./benchmarks";
import type {
  ApiStatus,
  Citation,
  QueryMode,
  SessionResponse,
  TaskStatusResponse,
} from "./types";

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

function App() {
  const [apiStatus, setApiStatus] =
    useState<ApiStatus>("checking");
  const [serviceName, setServiceName] = useState(
    "source-ledger",
  );
  const [databaseReady, setDatabaseReady] =
    useState(false);
  const [redisReady, setRedisReady] = useState(false);
  const [session, setSession] =
    useState<SessionResponse | null>(null);
  const [selectedFile, setSelectedFile] =
    useState<File | null>(null);
  const [uploadedSource, setUploadedSource] =
    useState("");
  const [indexedChunks, setIndexedChunks] = useState(0);
  const [question, setQuestion] = useState(
    "RAG 的完整流程有哪几步？",
  );
  const [mode, setMode] =
    useState<QueryMode>("stream");
  const [answer, setAnswer] = useState("");
  const [citations, setCitations] = useState<
    Citation[]
  >([]);
  const [runId, setRunId] = useState("");
  const [task, setTask] =
    useState<TaskStatusResponse | null>(null);
  const [querying, setQuerying] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function bootstrap() {
      try {
        const [health, readiness, createdSession] =
          await Promise.all([
            getHealth(),
            getReadiness(),
            createSession(),
          ]);

        if (!active) {
          return;
        }

        setServiceName(health.service);
        setDatabaseReady(readiness.database);
        setRedisReady(readiness.redis);
        setSession(createdSession);
        setApiStatus(
          readiness.ready ? "online" : "offline",
        );
      } catch (bootstrapError) {
        if (!active) {
          return;
        }
        setApiStatus("offline");
        setError(
          bootstrapError instanceof Error
            ? bootstrapError.message
            : String(bootstrapError),
        );
      }
    }

    void bootstrap();

    return () => {
      active = false;
    };
  }, []);

  const statusLabel = useMemo(() => {
    if (apiStatus === "online") {
      return "Runtime ready";
    }
    if (apiStatus === "checking") {
      return "Checking runtime";
    }
    return "Runtime offline";
  }, [apiStatus]);

  function handleFileChange(
    event: ChangeEvent<HTMLInputElement>,
  ) {
    setSelectedFile(event.target.files?.[0] ?? null);
    setError("");
  }

  async function handleUpload() {
    if (!selectedFile) {
      return;
    }

    setUploading(true);
    setError("");

    try {
      const result = await uploadDocument(
        selectedFile,
      );
      setUploadedSource(result.source);
      setIndexedChunks(result.indexed_chunks);
    } catch (uploadError) {
      setError(
        uploadError instanceof Error
          ? uploadError.message
          : String(uploadError),
      );
    } finally {
      setUploading(false);
    }
  }

  async function refreshTask(nextRunId: string) {
    try {
      const nextTask = await getTaskStatus(
        nextRunId,
      );
      setTask(nextTask);
    } catch {
      setTask(null);
    }
  }

  async function handleAsk() {
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || !session || querying) {
      return;
    }

    setQuerying(true);
    setError("");
    setAnswer("");
    setCitations([]);
    setRunId("");
    setTask(null);

    const requestId = crypto.randomUUID();

    try {
      if (mode === "stream") {
        let nextRunId = "";

        await streamQuestion(
          {
            question: trimmedQuestion,
            thread_id: session.thread_id,
            request_id: requestId,
            stream: true,
          },
          (event) => {
            if (event.event === "token") {
              const delta = String(
                event.data.delta ?? "",
              );
              setAnswer((current) => current + delta);
            }

            if (event.event === "citation") {
              setCitations((current) => [
                ...current,
                event.data as unknown as Citation,
              ]);
            }

            if (event.event === "start") {
              nextRunId = String(
                event.data.run_id ?? "",
              );
              setRunId(nextRunId);
            }

            if (event.event === "error") {
              throw new Error(
                String(
                  event.data.message ??
                    "stream error",
                ),
              );
            }
          },
        );

        if (nextRunId) {
          await refreshTask(nextRunId);
        }
      } else {
        const response = await askQuestion({
          question: trimmedQuestion,
          thread_id: session.thread_id,
          request_id: requestId,
          stream: false,
        });

        setAnswer(response.answer);
        setCitations(response.citations);
        setRunId(response.run_id);
        await refreshTask(response.run_id);
      }
    } catch (queryError) {
      setError(
        queryError instanceof Error
          ? queryError.message
          : String(queryError),
      );
    } finally {
      setQuerying(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-block">
          <div className="brand-mark">SL</div>
          <div>
            <p className="eyebrow">Verifiable RAG Runtime</p>
            <h1>SourceLedger Workbench</h1>
          </div>
        </div>

        <div className="runtime-status">
          <span
            className={`status-dot status-${apiStatus}`}
          />
          <div>
            <strong>{statusLabel}</strong>
            <span>{serviceName}</span>
          </div>
        </div>
      </header>

      {error ? (
        <div className="error-banner">
          <AlertTriangle size={18} />
          <span>{error}</span>
        </div>
      ) : null}

      <main className="workbench-grid">
        <section className="panel ingest-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Ingest</p>
              <h2>Document Index</h2>
            </div>
            <Database size={20} />
          </div>

          <label className="drop-zone">
            <Upload size={28} />
            <strong>
              {selectedFile
                ? selectedFile.name
                : "Select PDF"}
            </strong>
            <span>
              Parsing, embedding and indexing run on the API.
            </span>
            <input
              type="file"
              accept=".pdf,application/pdf"
              onChange={handleFileChange}
            />
          </label>

          <button
            className="primary-button"
            type="button"
            disabled={!selectedFile || uploading}
            onClick={handleUpload}
          >
            {uploading ? (
              <LoaderCircle
                className="spin"
                size={17}
              />
            ) : (
              <Upload size={17} />
            )}
            {uploading ? "Indexing" : "Upload and index"}
          </button>

          <div className="source-state">
            <FileText size={18} />
            <div>
              <strong>
                {uploadedSource || "No document indexed"}
              </strong>
              <span>
                {uploadedSource
                  ? `${indexedChunks} chunks indexed`
                  : "Upload a document to begin"}
              </span>
            </div>
          </div>
        </section>

        <section className="panel query-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Query</p>
              <h2>Grounded Answer</h2>
            </div>
            <MessageSquare size={20} />
          </div>

          <div
            className="mode-control"
            aria-label="Response mode"
          >
            <button
              className={
                mode === "stream" ? "active" : ""
              }
              type="button"
              onClick={() => setMode("stream")}
            >
              Stream
            </button>
            <button
              className={
                mode === "standard" ? "active" : ""
              }
              type="button"
              onClick={() => setMode("standard")}
            >
              Standard
            </button>
          </div>

          <textarea
            value={question}
            onChange={(event) =>
              setQuestion(event.target.value)
            }
            placeholder="Ask a question against the indexed corpus"
            rows={4}
          />

          <div className="query-actions">
            <div className="identity-line">
              <span>Thread</span>
              <code>
                {session?.thread_id ?? "offline"}
              </code>
            </div>
            <button
              className="send-button"
              type="button"
              disabled={
                querying ||
                !question.trim() ||
                !session
              }
              onClick={handleAsk}
            >
              {querying ? (
                <LoaderCircle
                  className="spin"
                  size={17}
                />
              ) : (
                <Send size={17} />
              )}
              {querying ? "Running" : "Run query"}
            </button>
          </div>

          <article className="answer-surface">
            <div className="answer-header">
              <Activity size={17} />
              <span>Response</span>
              {runId ? (
                <code>{runId.slice(0, 12)}</code>
              ) : null}
            </div>
            <p>
              {answer ||
                "The grounded answer will appear here. Use stream mode to inspect token events."}
            </p>
          </article>
        </section>

        <aside className="panel evidence-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Evidence</p>
              <h2>Citations</h2>
            </div>
            <GitBranch size={20} />
          </div>

          <div className="citation-list">
            {citations.length ? (
              citations.map((citation) => (
                <article
                  className="citation-item"
                  key={`${citation.citation_id}-${citation.source}-${citation.page}`}
                >
                  <span>{citation.citation_id}</span>
                  <div>
                    <strong>
                      {citation.source}
                    </strong>
                    <p>Page {citation.page}</p>
                  </div>
                </article>
              ))
            ) : (
              <div className="empty-state">
                <FileText size={22} />
                <span>
                  Citations appear after a grounded answer.
                </span>
              </div>
            )}
          </div>

          <div className="guardrail-box">
            <ShieldAlert size={19} />
            <div>
              <strong>Untrusted context policy</strong>
              <p>
                Retrieved instructions are treated as
                data. Conflict and injection signals are
                preserved for review.
              </p>
            </div>
          </div>

          <div className="task-box">
            <div>
              <span>Task</span>
              <strong>
                {task?.status ?? "idle"}
              </strong>
            </div>
            <div>
              <span>Node</span>
              <strong>
                {task?.current_node ?? "-"}
              </strong>
            </div>
            <div>
              <span>Step</span>
              <strong>
                {task
                  ? `${task.step_count}/${task.max_steps}`
                  : "-"}
              </strong>
            </div>
          </div>
        </aside>
      </main>

      <section className="metrics-strip">
        <article>
          <Server size={18} />
          <div>
            <span>API</span>
            <strong>
              {apiStatus === "online"
                ? "Ready"
                : "Offline"}
            </strong>
          </div>
        </article>
        <article>
          <Database size={18} />
          <div>
            <span>PostgreSQL</span>
            <strong>
              {databaseReady ? "Healthy" : "Down"}
            </strong>
          </div>
        </article>
        <article>
          <Activity size={18} />
          <div>
            <span>Redis</span>
            <strong>
              {redisReady ? "Healthy" : "Down"}
            </strong>
          </div>
        </article>
        <article>
          <CheckCircle2 size={18} />
          <div>
            <span>Load success</span>
            <strong>
              {benchmarkSnapshot.load.successful}/
              {benchmarkSnapshot.load.successful +
                benchmarkSnapshot.load.failed}
            </strong>
          </div>
        </article>
        <article>
          <Activity size={18} />
          <div>
            <span>p50 / p95</span>
            <strong>
              {benchmarkSnapshot.load.p50} /{" "}
              {benchmarkSnapshot.load.p95} ms
            </strong>
          </div>
        </article>
        <article>
          <Coins size={18} />
          <div>
            <span>Context tokens</span>
            <strong>
              {benchmarkSnapshot.load.contextTokens}
            </strong>
          </div>
        </article>
        <article>
          <GitBranch size={18} />
          <div>
            <span>Citation recall</span>
            <strong>
              {formatPercent(
                benchmarkSnapshot.context
                  .citationRecall,
              )}
            </strong>
          </div>
        </article>
        <article>
          <ShieldAlert size={18} />
          <div>
            <span>Injection coverage</span>
            <strong>
              {
                benchmarkSnapshot.context
                  .injectionCoverage
              }
            </strong>
          </div>
        </article>
      </section>

      <footer className="footer-line">
        <span>{API_BASE_URL}</span>
        <span>
          Hit@1{" "}
          {formatPercent(
            benchmarkSnapshot.retrieval.hitAt1,
          )}
        </span>
        <span>
          MRR{" "}
          {formatPercent(
            benchmarkSnapshot.retrieval.mrr,
          )}
        </span>
      </footer>
    </div>
  );
}

export default App;

