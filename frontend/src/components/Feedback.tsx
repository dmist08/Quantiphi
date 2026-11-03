import { AlertCircle, Info, LoaderCircle } from 'lucide-react'
import { ApiError } from '../api/client'
import type { Meta } from '../types/api'

export function ErrorNotice({ error, retry }: { error: unknown; retry?: () => void }) {
  const message = error instanceof Error ? error.message : 'Something went wrong. Please try again.'
  const info = error instanceof ApiError ? error.info : null
  return <div className="notice error" role="alert"><AlertCircle size={18} /><div><p>{message}</p>
    {info?.details?.map((detail, index) => <p key={index}>{detail.field}: {detail.message}</p>)}
    {info?.reset_at && <p>Rate limit resets: {new Date(info.reset_at).toLocaleString()}</p>}
    {retry && <button className="text-button" onClick={retry}>Try again</button>}
  </div></div>
}

export function MetaNotice({ meta }: { meta: Meta }) {
  return <>
    {meta.stale && <div className="notice warning" role="status"><AlertCircle size={18} /><div><p>{meta.warning ?? 'Showing saved data.'}</p><small>Last successful update: {new Date(meta.fetched_at).toLocaleString()}</small></div></div>}
    {meta.notice && <div className="notice" role="status"><Info size={18} /><p>{meta.notice}</p></div>}
    {meta.truncated && <div className="notice" role="status"><Info size={18} /><p>This portfolio includes the top 500 public repositories by stars.</p></div>}
  </>
}

export function Loading({ label = 'Loading portfolio…' }: { label?: string }) {
  return <div className="loading-state" role="status"><LoaderCircle className="spin" size={24} /><span>{label}</span></div>
}
