import { useEffect, useRef, useState } from 'react'
import { ArrowRight, BriefcaseBusiness, ChartNoAxesCombined, Github, LayoutDashboard, RefreshCw, Search, Sparkles } from 'lucide-react'
import { api, useMocks } from '../api/client'
import type { Dashboard, Settings } from '../types/api'
import { ErrorNotice, Loading, MetaNotice } from './Feedback'
import { MatchBadge, ProfileHeader } from './ProfileHeader'
import { LanguageChart } from './LanguageChart'
import { ContributionHeatmap } from './ContributionHeatmap'
import { RepositoriesPanel } from './RepositoriesPanel'
import { CareerPanel } from './CareerPanel'

export function App() {
  const [search, setSearch] = useState('')
  const [username, setUsername] = useState('')
  const [data, setData] = useState<Dashboard | null>(null)
  const [settings, setSettings] = useState<Settings | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [settingsError, setSettingsError] = useState<unknown>(null)
  const [loading, setLoading] = useState(false)
  const [revision, setRevision] = useState(0)
  const controller = useRef<AbortController | null>(null)

  useEffect(() => {
    const abort = new AbortController()
    setSettingsError(null)
    api.settings(abort.signal).then(value => {
      setSettings(value)
      if (value.default_username) { setUsername(value.default_username); setSearch(value.default_username) }
    }).catch(error => { if (!abort.signal.aborted) setSettingsError(error) })
    return () => abort.abort()
  }, [revision])

  useEffect(() => {
    if (!username) return
    controller.current?.abort()
    const abort = new AbortController()
    controller.current = abort
    setLoading(true)
    setError(null)
    setData(null)
    api.dashboard(username, false, abort.signal).then(setData).catch(error => { if (!abort.signal.aborted) setError(error) }).finally(() => { if (!abort.signal.aborted) setLoading(false) })
    return () => abort.abort()
  }, [username])

  useEffect(() => () => controller.current?.abort(), [])

  function load(refresh = false) {
    if (!username) return
    controller.current?.abort()
    const abort = new AbortController()
    controller.current = abort
    setLoading(true)
    setError(null)
    api.dashboard(username, refresh, abort.signal).then(setData).catch(error => { if (!abort.signal.aborted) setError(error) }).finally(() => { if (!abort.signal.aborted) setLoading(false) })
  }

  return <div className="app-shell">
    <a className="skip-link" href="#main">Skip to content</a>
    <aside className="sidebar"><a className="brand" href="#main"><span className="brand-icon"><Github size={24} /></span>gitfolio<span className="brand-period">.</span></a><span className="sidebar-label">YOUR WORK, IN FOCUS</span><nav aria-label="Main navigation"><a className="nav-item active" href="#main"><LayoutDashboard size={19} />Overview</a><a className="nav-item" href="#activity"><ChartNoAxesCombined size={19} />Activity</a><a className="nav-item" href="#repositories"><Github size={19} />Repositories</a><a className="nav-item" href="#career"><BriefcaseBusiness size={19} />Career match</a></nav><div className="sidebar-note"><Sparkles size={22} /><strong>More than a profile.</strong><p>A little perspective on everything you’re building.</p></div><div className="sidebar-footer"><span className="status-dot" />{useMocks ? 'Fixture preview' : 'Local workspace'}<span className="version">v1.0</span></div></aside>
    <div className="workspace"><header className="topbar"><div className="breadcrumb">Workspace <span>/</span> <strong>Overview</strong></div><form className="search-form" onSubmit={event => { event.preventDefault(); const next = search.trim(); if (next === username) load(); else setUsername(next) }}><label className="sr-only" htmlFor="username">GitHub username</label><Search size={17} /><input id="username" value={search} onChange={event => setSearch(event.target.value)} placeholder="Find a GitHub developer…" required autoComplete="off" spellCheck={false} /><button type="submit" aria-label="Load GitHub portfolio"><ArrowRight size={18} /></button></form></header>
      <main id="main"><div className="page-heading"><div><div className="eyebrow accent">THE BIG PICTURE</div><h1>Your code. Your story.</h1><p>A fresh perspective on your work, growth, and what comes next.</p></div><button className="button secondary" disabled={!data || loading} onClick={() => load(true)}><RefreshCw size={15} className={loading ? 'spin' : ''} />Refresh data</button></div>
        {useMocks && <div className="preview-banner">Preview mode · Sample data, independent of GitHub. Try “empty”, “stale”, or “not-found” to explore states.</div>}
        {!!settingsError && <ErrorNotice error={settingsError} retry={() => setRevision(value => value + 1)} />}
        {!settings && !settingsError && <Loading label="Loading your workspace…" />}
        {!!error && <ErrorNotice error={error} retry={() => load()} />}
        {loading && !data && <Loading />}
        {!username && settings && <section className="panel welcome"><Github size={42} /><h2>Your portfolio starts here</h2><p>Enter a GitHub username above to explore public work, contribution activity, and career fit.</p><button className="button primary" onClick={() => { setSearch('octocat'); setUsername('octocat') }}>Explore octocat <ArrowRight size={16} /></button></section>}
        {data && <div aria-busy={loading}><MetaNotice meta={data.meta} /><MatchBadge match={data.match} /><div className="overview-grid"><ProfileHeader data={data} /><LanguageChart languages={data.languages} /></div><ContributionHeatmap data={data} /><RepositoriesPanel key={`repos-${data.profile.login}-${data.meta.fetched_at}`} username={data.profile.login} /><CareerPanel key={`career-${data.profile.login}`} username={data.profile.login} initialDescription={data.job_description} initialMatch={data.match} onMatch={result => setData(current => current ? { ...current, match: result.match, job_description: result.job_description } : current)} /></div>}
        <footer className="page-footer"><span>Built around your public work.</span><span>Gitfolio <span className="accent">✦</span> A clearer developer story</span></footer>
      </main>
    </div>
  </div>
}
