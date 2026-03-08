'use client'

import { useEffect, useState, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Upload, FileText, Trash2 } from 'lucide-react'
import { apiFetch, apiUpload } from '@/lib/api'
import type { Document } from '@/lib/types'

export default function KnowledgePage() {
  const params = useParams()
  const router = useRouter()
  const chatbotId = params.id as string

  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [dragOver, setDragOver] = useState(false)

  const fetchDocuments = useCallback(async () => {
    try {
      const docs = await apiFetch<Document[]>(`/api/v1/chatbots/${chatbotId}/documents`)
      setDocuments(docs)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load documents')
    } finally {
      setLoading(false)
    }
  }, [chatbotId])

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      router.push('/login')
      return
    }
    fetchDocuments()
  }, [router, fetchDocuments])

  async function handleUpload(files: FileList | null) {
    if (!files || files.length === 0) return

    const file = files[0]
    const ext = file.name.toLowerCase().split('.').pop()
    if (ext !== 'pdf' && ext !== 'txt') {
      setError('Only PDF and TXT files are supported')
      return
    }

    setError('')
    setUploading(true)

    try {
      const formData = new FormData()
      formData.append('file', file)
      await apiUpload<Document>(`/api/v1/chatbots/${chatbotId}/documents`, formData)
      await fetchDocuments()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  async function handleDelete(docId: string) {
    try {
      await apiFetch(`/api/v1/chatbots/${chatbotId}/documents/${docId}`, {
        method: 'DELETE',
      })
      setDocuments((prev) => prev.filter((d) => d.id !== docId))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete document')
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragOver(false)
    handleUpload(e.dataTransfer.files)
  }

  const statusColor: Record<string, string> = {
    processed: 'bg-green-100 text-green-800',
    pending: 'bg-yellow-100 text-yellow-800',
    processing: 'bg-blue-100 text-blue-800',
    error: 'bg-red-100 text-red-800',
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <div className="mb-6">
        <Link
          href={`/dashboard/${chatbotId}`}
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors mb-4"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to chatbot
        </Link>
        <h1 className="text-2xl font-bold text-foreground">Knowledge Base</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Upload documents to train your chatbot. Supports PDF and TXT files.
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</div>
      )}

      {/* Upload zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        className={`mb-6 rounded-lg border-2 border-dashed p-8 text-center transition-colors ${
          dragOver ? 'border-primary bg-primary/5' : 'border-border'
        }`}
      >
        <Upload className="mx-auto h-8 w-8 text-muted-foreground mb-2" />
        <p className="text-sm text-muted-foreground mb-3">
          {uploading ? 'Uploading...' : 'Drag and drop a file, or browse'}
        </p>
        <label className="cursor-pointer rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 transition-opacity">
          Browse files
          <input
            type="file"
            accept=".pdf,.txt"
            className="hidden"
            onChange={(e) => handleUpload(e.target.files)}
            disabled={uploading}
          />
        </label>
      </div>

      {/* Document list */}
      {loading ? (
        <p className="text-muted-foreground">Loading documents...</p>
      ) : documents.length === 0 ? (
        <p className="text-center text-muted-foreground py-8">
          No documents uploaded yet. Upload your first document above.
        </p>
      ) : (
        <div className="space-y-3">
          {documents.map((doc) => (
            <div
              key={doc.id}
              className="flex items-center justify-between rounded-lg border border-border bg-card p-4"
            >
              <div className="flex items-center gap-3">
                <FileText className="h-5 w-5 text-muted-foreground" />
                <div>
                  <p className="text-sm font-medium text-foreground">{doc.filename}</p>
                  <p className="text-xs text-muted-foreground">
                    {doc.chunk_count} chunks
                    {doc.error_message && ` - ${doc.error_message}`}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span
                  className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                    statusColor[doc.status] || 'bg-gray-100 text-gray-800'
                  }`}
                >
                  {doc.status}
                </span>
                <button
                  onClick={() => handleDelete(doc.id)}
                  className="rounded p-1 text-muted-foreground hover:text-red-600 transition-colors"
                  aria-label="Delete document"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
