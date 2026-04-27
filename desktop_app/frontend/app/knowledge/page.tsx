"use client"

import { useCallback, useEffect, useState } from "react"
import { AppShell } from "@/components/app-shell"
import { EmptyState, ErrorState, LoadingState } from "@/components/api-state"
import { useServerEvents } from "@/hooks/use-server-events"
import { apiClient } from "@/lib/api"
import type { KnowledgeImportResult, KnowledgeSearchResult, KnowledgeStatus, WebKnowledgeBuildResult } from "@/lib/api"
import { BookOpen, Cloud, Database, FileText, RefreshCw, Search, UploadCloud } from "lucide-react"

export default function KnowledgePage() {
  const [status, setStatus] = useState<KnowledgeStatus | null>(null)
  const [query, setQuery] = useState("")
  const [filePathsText, setFilePathsText] = useState("")
  const [searchResults, setSearchResults] = useState<KnowledgeSearchResult[]>([])
  const [importResult, setImportResult] = useState<KnowledgeImportResult | null>(null)
  const [webResult, setWebResult] = useState<WebKnowledgeBuildResult | null>(null)
  const [loadingStatus, setLoadingStatus] = useState(true)
  const [busyAction, setBusyAction] = useState<"search" | "import" | "web" | "">("")
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")

  const loadStatus = useCallback(async () => {
    setError("")
    setLoadingStatus(true)
    try {
      const response = await apiClient.getKnowledgeStatus()
      if (!response.success || !response.data) {
        setError(response.error ? `${response.error.code}: ${response.error.message}` : "知识库状态加载失败")
        return
      }
      setStatus(response.data)
    } catch (err) {
      setError(err instanceof Error ? err.message : "无法连接知识库服务")
    } finally {
      setLoadingStatus(false)
    }
  }, [])

  async function searchKnowledge() {
    const keyword = query.trim()
    if (!keyword) {
      setError("请输入要检索的问题或关键词")
      return
    }
    setBusyAction("search")
    setError("")
    setNotice("")
    try {
      const response = await apiClient.searchKnowledge(keyword, 5)
      if (!response.success || !response.data) {
        setError(response.error ? `${response.error.code}: ${response.error.message}` : "知识库检索失败")
        return
      }
      setSearchResults(response.data)
      setNotice(`已返回 ${response.data.length} 条检索结果。`)
    } catch (err) {
      setError(err instanceof Error ? err.message : "无法连接检索接口")
    } finally {
      setBusyAction("")
    }
  }

  async function importFiles() {
    const filePaths = parseFilePaths(filePathsText)
    if (!filePaths.length) {
      setError("请先填写或拖入至少一个本地文件路径")
      return
    }
    setBusyAction("import")
    setError("")
    setNotice("")
    try {
      const response = await apiClient.importKnowledgeFiles(filePaths)
      if (!response.success || !response.data) {
        setError(response.error ? `${response.error.code}: ${response.error.message}` : "文件入库失败")
        return
      }
      setImportResult(response.data)
      setNotice(response.data.index_rebuilt ? "文件已入库并重建索引。" : "文件已提交入库。")
      await loadStatus()
    } catch (err) {
      setError(err instanceof Error ? err.message : "无法连接文件入库接口")
    } finally {
      setBusyAction("")
    }
  }

  async function buildWebKnowledge() {
    const filePaths = parseFilePaths(filePathsText)
    if (!filePaths.length) {
      setError("请先提供用于联网扩库的文档路径")
      return
    }
    setBusyAction("web")
    setError("")
    setNotice("")
    try {
      const response = await apiClient.buildWebKnowledgeFromDocuments(filePaths, 5)
      if (!response.success || !response.data) {
        setError(response.error ? `${response.error.code}: ${response.error.message}` : "联网扩库失败")
        return
      }
      setWebResult(response.data)
      setNotice(`联网扩库任务完成：${response.data.status}`)
      await loadStatus()
    } catch (err) {
      setError(err instanceof Error ? err.message : "无法连接联网扩库接口")
    } finally {
      setBusyAction("")
    }
  }

  function handleDrop(event: React.DragEvent<HTMLTextAreaElement>) {
    event.preventDefault()
    const dropped = Array.from(event.dataTransfer.files).map((file) => filePathFromDrop(file))
    if (!dropped.length) return
    setFilePathsText((current) => [current.trim(), ...dropped].filter(Boolean).join("\n"))
  }

  useEffect(() => {
    void loadStatus()
  }, [loadStatus])

  useServerEvents(() => {
    void loadStatus()
  }, { eventTypes: ["knowledge.progress"], replay: 1 })

  return (
    <AppShell title="知识库">
      <div className="grid min-h-[656px] flex-1 grid-cols-[1.05fr_0.95fr] gap-5 bg-[#f6f8fb] p-6">
        <section className="space-y-5">
          {error ? <ErrorState message={error} /> : null}
          {notice ? <div className="rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{notice}</div> : null}
          {loadingStatus ? <LoadingState label="正在读取知识库状态" /> : <StatusPanel status={status} onRefresh={loadStatus} />}

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-4 flex items-center gap-2 text-[15px] font-semibold text-slate-800">
              <UploadCloud className="h-4 w-4 text-blue-500" />
              本地文件入库
            </div>
            <p className="mb-3 text-xs leading-relaxed text-slate-500">
              支持把 PDF、DOCX、图片、TXT、Markdown 等文档路径提交给后端拆分入库。桌面壳接入后可把拖拽文件自动转换为绝对路径。
            </p>
            <textarea
              value={filePathsText}
              onChange={(event) => setFilePathsText(event.target.value)}
              onDrop={handleDrop}
              onDragOver={(event) => event.preventDefault()}
              rows={7}
              placeholder={"每行一个本地文件路径，例如：\nC:\\docs\\产品手册.pdf\nC:\\docs\\行业资料.docx"}
              className="w-full resize-none rounded-xl border border-dashed border-blue-200 bg-blue-50/40 px-4 py-3 text-sm leading-relaxed text-slate-800 outline-none focus:border-blue-400"
            />
            <div className="mt-4 flex gap-3">
              <button
                disabled={busyAction === "import"}
                onClick={importFiles}
                className="flex h-10 flex-1 items-center justify-center gap-2 rounded-xl bg-blue-500 text-sm font-semibold text-white hover:bg-blue-600 disabled:cursor-not-allowed disabled:bg-slate-300"
              >
                <Database className="h-4 w-4" />
                {busyAction === "import" ? "入库中" : "拆分入库"}
              </button>
              <button
                disabled={busyAction === "web"}
                onClick={buildWebKnowledge}
                className="flex h-10 flex-1 items-center justify-center gap-2 rounded-xl border border-blue-200 bg-white text-sm font-semibold text-blue-600 hover:bg-blue-50 disabled:cursor-not-allowed disabled:text-slate-400"
              >
                <Cloud className="h-4 w-4" />
                {busyAction === "web" ? "扩库中" : "联网扩库"}
              </button>
            </div>
          </div>

          <ResultPanel importResult={importResult} webResult={webResult} />
        </section>

        <section className="space-y-5">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-4 flex items-center gap-2 text-[15px] font-semibold text-slate-800">
              <Search className="h-4 w-4 text-blue-500" />
              知识库检索
            </div>
            <div className="flex gap-3">
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") void searchKnowledge()
                }}
                placeholder="输入客户问题，例如：试用政策是什么？"
                className="h-10 flex-1 rounded-xl border border-slate-200 bg-slate-50 px-4 text-sm text-slate-800 outline-none focus:border-blue-400"
              />
              <button
                disabled={busyAction === "search"}
                onClick={searchKnowledge}
                className="h-10 rounded-xl bg-blue-500 px-5 text-sm font-semibold text-white hover:bg-blue-600 disabled:cursor-not-allowed disabled:bg-slate-300"
              >
                {busyAction === "search" ? "检索中" : "检索"}
              </button>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-4 flex items-center gap-2 text-[15px] font-semibold text-slate-800">
              <BookOpen className="h-4 w-4 text-blue-500" />
              检索结果
            </div>
            {searchResults.length ? (
              <div className="space-y-3">
                {searchResults.map((item) => (
                  <div key={item.chunk_id} className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3">
                    <div className="mb-2 flex items-center justify-between text-xs text-slate-400">
                      <span>{item.chunk_id || "未命名片段"}</span>
                      <span>相关度 {item.score.toFixed(2)}</span>
                    </div>
                    <p className="text-sm leading-relaxed text-slate-700">{item.text}</p>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState title="暂无检索结果">先导入文档，或输入问题后点击检索。</EmptyState>
            )}
          </div>
        </section>
      </div>
    </AppShell>
  )
}

function filePathFromDrop(file: File) {
  const maybeDesktopFile = file as File & { path?: string }
  return maybeDesktopFile.path || file.name
}

function StatusPanel({ status, onRefresh }: { status: KnowledgeStatus | null; onRefresh: () => void }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2 text-[15px] font-semibold text-slate-800">
          <Database className="h-4 w-4 text-blue-500" />
          知识库状态
        </div>
        <button onClick={onRefresh} className="flex h-8 items-center gap-1.5 rounded-lg border border-slate-200 px-3 text-xs text-slate-600 hover:bg-slate-50">
          <RefreshCw className="h-3.5 w-3.5" />
          刷新
        </button>
      </div>
      <div className="grid grid-cols-4 gap-3">
        <Metric label="索引状态" value={status?.ready ? "已就绪" : "未就绪"} accent={status?.ready ? "green" : "orange"} />
        <Metric label="文档数" value={String(status?.documents_loaded ?? 0)} />
        <Metric label="片段数" value={String(status?.chunks_created ?? 0)} />
        <Metric label="向量模型" value={status?.embedding_provider || "本地检索"} />
      </div>
      <div className="mt-4 rounded-xl bg-slate-50 px-4 py-3 text-xs leading-relaxed text-slate-500">
        <div>索引路径：{status?.index_path || "暂无"}</div>
        <div>支持格式：{status?.supported_extensions?.join("、") || "等待后端返回"}</div>
        <div>最近构建：{formatDate(status?.last_built_at)}</div>
      </div>
    </div>
  )
}

function Metric({ label, value, accent }: { label: string; value: string; accent?: "green" | "orange" }) {
  const color = accent === "green" ? "text-emerald-600" : accent === "orange" ? "text-orange-600" : "text-slate-900"
  return (
    <div className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3">
      <div className="text-xs text-slate-500">{label}</div>
      <div className={`mt-1 truncate text-lg font-bold ${color}`}>{value}</div>
    </div>
  )
}

function ResultPanel({
  importResult,
  webResult,
}: {
  importResult: KnowledgeImportResult | null
  webResult: WebKnowledgeBuildResult | null
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-center gap-2 text-[15px] font-semibold text-slate-800">
        <FileText className="h-4 w-4 text-blue-500" />
        最近任务
      </div>
      {!importResult && !webResult ? (
        <EmptyState title="暂无入库任务">提交本地文件或联网扩库后，这里会显示最近结果。</EmptyState>
      ) : (
        <div className="space-y-3">
          {importResult ? (
            <div className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3">
              <div className="mb-2 text-sm font-semibold text-slate-800">本地入库</div>
              <div className="text-xs text-slate-500">索引重建：{importResult.index_rebuilt ? "是" : "否"}</div>
              <div className="mt-2 space-y-1">
                {importResult.files.map((file) => (
                  <div key={`${file.file_name}-${file.status}`} className="flex justify-between gap-3 text-xs text-slate-600">
                    <span className="truncate">{file.file_name}</span>
                    <span>{file.status}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
          {webResult ? (
            <div className="rounded-xl border border-blue-100 bg-blue-50/50 px-4 py-3">
              <div className="mb-2 text-sm font-semibold text-slate-800">联网扩库</div>
              <div className="text-xs text-slate-500">状态：{webResult.status}，搜索上限：{webResult.search_limit}</div>
              <div className="mt-2 space-y-1">
                {webResult.documents.map((document) => (
                  <div key={document} className="truncate text-xs text-slate-600">{document}</div>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      )}
    </div>
  )
}

function parseFilePaths(value: string) {
  return value
    .split(/\r?\n/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function formatDate(value: string | null | undefined) {
  if (!value) return "暂无"
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return parsed.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  })
}
