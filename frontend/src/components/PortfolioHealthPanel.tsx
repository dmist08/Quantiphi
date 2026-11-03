import { useEffect, useState } from 'react'
import { ArrowUpRight, HeartPulse } from 'lucide-react'
import { api } from '../api/client'
import type { PortfolioHealth } from '../types/api'
import { ErrorNotice, Loading, MetaNotice } from './Feedback'
import './PortfolioHealthPanel.css'

export function PortfolioHealthPanel({ username }: { username: string }) {
  const [data, setData] = useState<PortfolioHealth | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<unknown>(null)
  const [revision, setRevision] = useState(0)

  useEffect(() => {
    const abort = new AbortController()
    setLoading(true)
    setError(null)
    api.portfolioHealth(username, abort.signal)
      .then(setData)
      .catch(error => { if (!abort.signal.aborted) setError(error) })
      .finally(() => { if (!abort.signal.aborted) setLoading(false) })
    return () => abort.abort()
  }, [username, revision])

  return <section id="portfolio-health" className="panel health-panel" aria-labelledby="health-title" aria-busy={loading}>
    <div className="section-heading"><div><div className="eyebrow accent">PUT YOUR BEST WORK FORWARD</div><h2 id="health-title">Portfolio Health</h2><p>A closer look at how your public work is presented.</p></div><span className="feature-icon"><HeartPulse size={20} /></span></div>
    {loading ? <Loading label="Loading portfolio health…" /> : error ? <ErrorNotice error={error} retry={() => setRevision(value => value + 1)} /> : data && <>
      <MetaNotice meta={data.meta} />
      <div className="health-layout"><div className="health-summary">
        <span className="eyebrow accent">PRESENTATION SCORE</span>
        {data.status === 'no_repos' || data.score === null ? <><strong className="health-no-score">Score unavailable</strong><p>{data.status === 'no_repos' ? 'No original public repositories to assess yet.' : 'The service did not provide a score.'}</p></> : <div className="health-score" aria-label={`Portfolio health: ${data.score} out of ${data.max_score}`}><strong>{data.score}</strong><span>/ {data.max_score}</span></div>}
        <p className="health-limitation">{data.limitation}</p><p className="health-date">As of {data.as_of}</p>
      </div><div className="health-checks">{data.checks.map(check => <article className="health-check" key={check.key}>
        <div><h3>{check.label}</h3><strong>{check.score} <span>/ {check.max_score}</span></strong></div>
        <meter min={0} max={check.max_score} value={check.score} aria-label={`${check.label}: ${check.score} out of ${check.max_score}`} />
        <p>{check.detail}</p>{check.suggestion && <p className="health-suggestion">{check.suggestion}</p>}
      </article>)}</div></div>
      <div className="health-actions"><h3>Top actions</h3>{data.top_actions.length > 0 ? <ol>{data.top_actions.map((action, index) => <li key={index}><ArrowUpRight size={14} /><span>{action}</span></li>)}</ol> : <p>No recommended actions from the service. Keep sharing your work.</p>}</div>
    </>}
  </section>
}
