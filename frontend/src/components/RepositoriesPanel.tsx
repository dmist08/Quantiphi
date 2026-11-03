import { useEffect, useState } from 'react'
import { Archive, ArrowDownWideNarrow, ArrowUpRight, BookOpen, ChevronLeft, ChevronRight, GitFork, Star } from 'lucide-react'
import { api } from '../api/client'
import type { Repositories, Repository, RepoQuery, RepoSort } from '../types/api'
import { ErrorNotice, Loading, MetaNotice } from './Feedback'

function RepositoryCard({ repo }: { repo: Repository }) {
  return <article className="repo-card"><div className="repo-title"><BookOpen size={17} /><h3><a href={repo.url} target="_blank" rel="noreferrer">{repo.name}<ArrowUpRight size={13} /></a></h3></div>
    <div className="repo-markers">{repo.is_fork && <span className="tag"><GitFork size={11} />Fork</span>}{repo.is_archived && <span className="tag"><Archive size={11} />Archived</span>}</div>
    <p className="repo-description">{repo.description ?? 'No description provided.'}</p>
    <div className="repo-meta">{repo.language && <span className="repo-language"><span className="color-dot" style={{ backgroundColor: repo.language_color ?? '#a2a7b7' }} />{repo.language}</span>}<span aria-label={`${repo.stars} stars`}><Star size={13} />{repo.stars.toLocaleString()}</span><span aria-label={`${repo.forks} forks`}><GitFork size={13} />{repo.forks.toLocaleString()}</span></div>
  </article>
}

export function RepositoriesPanel({ username }: { username: string }) {
  const [query, setQuery] = useState<RepoQuery>({ sort: 'stars', language: '', include_forks: false, page: 1, page_size: 4 })
  const [data, setData] = useState<Repositories | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<unknown>(null)
  const [revision, setRevision] = useState(0)

  useEffect(() => {
    const abort = new AbortController()
    setLoading(true)
    setError(null)
    api.repositories(username, query, abort.signal).then(setData).catch(error => { if (!abort.signal.aborted) setError(error) }).finally(() => { if (!abort.signal.aborted) setLoading(false) })
    return () => abort.abort()
  }, [username, query, revision])

  function update(next: Partial<RepoQuery>) { setQuery(previous => ({ ...previous, ...next, page: 1 })) }

  return <section id="repositories" className="panel repositories-panel" aria-labelledby="repos-title" aria-busy={loading}>
    <div className="section-heading"><div><div className="eyebrow accent">IDEAS, MADE REAL</div><h2 id="repos-title">The work behind the profile</h2><p>Public projects. Practical experiments. A portfolio in progress.</p></div><span className="count-pill">{data ? `${data.total} repositories` : 'Repositories'}</span></div>
    <div className="repo-controls"><label><span className="sr-only">Sort repositories</span><ArrowDownWideNarrow size={14} /><select value={query.sort} onChange={event => update({ sort: event.target.value as RepoSort })} disabled={loading}><option value="stars">Most stars</option><option value="forks">Most forks</option><option value="updated">Recently updated</option><option value="name">Name A–Z</option></select></label>
      <label><span className="sr-only">Filter by language</span><select value={query.language} onChange={event => update({ language: event.target.value })} disabled={loading}><option value="">All languages</option>{data?.available_languages.map(language => <option key={language} value={language}>{language}</option>)}</select></label>
      <label className="checkbox-label"><input type="checkbox" checked={query.include_forks} onChange={event => update({ include_forks: event.target.checked })} disabled={loading} />Include forks</label>
    </div>
    {!!error && <ErrorNotice error={error} retry={() => setRevision(value => value + 1)} />}
    {loading ? <Loading label="Loading repositories…" /> : !error && data && <><MetaNotice meta={data.meta} />{data.items.length ? <div className="repo-grid">{data.items.map(repo => <RepositoryCard key={repo.url} repo={repo} />)}</div> : <div className="repo-empty"><BookOpen size={27} /><h3>No repositories to show</h3><p>Try another language or include forks to explore more public work.</p></div>}
      <div className="pagination"><span>{data.total_pages > 0 ? `Page ${data.page} of ${data.total_pages}` : 'No results'} · {data.total} repositories</span><div><button className="button secondary small" disabled={data.page <= 1} onClick={() => setQuery(previous => ({ ...previous, page: data.page - 1 }))}><ChevronLeft size={14} />Previous</button><button className="button secondary small" disabled={data.total_pages === 0 || data.page >= data.total_pages} onClick={() => setQuery(previous => ({ ...previous, page: data.page + 1 }))}>Next<ChevronRight size={14} /></button></div></div></>}
  </section>
}
