import { useEffect, useRef, useState } from 'react'
import { ArrowRight, BriefcaseBusiness, ChartNoAxesCombined, Github, LayoutDashboard, MessageCircle, RefreshCw, Search, Settings2, Sparkles } from 'lucide-react'
import { ApiError, api, useMocks } from '../api/client'
import type { Dashboard, Settings } from '../types/api'
import { ErrorNotice, Loading, MetaNotice } from './Feedback'
import { MatchBadge, ProfileHeader } from './ProfileHeader'
import { LanguageChart } from './LanguageChart'
import { ContributionHeatmap } from './ContributionHeatmap'
import { RepositoriesPanel } from './RepositoriesPanel'
import { CareerPanel } from './CareerPanel'
import { ChatPanel } from './ChatPanel'
import { SettingsDialog } from './SettingsDialog'

export function App() {
  const [search, setSearch] = useState('')
  const [username, setUsername] = useState('')
  const [data, setData] = useState<Dashboard | null>(null)
  const [settings, setSettings] = useState<Settings | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [settingsError, setSettingsError] = useState<unknown>(null)
  const [loading, setLoading] = useState(false)
  const [revision, setRevision] = useState(0)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [settingsSaved, setSettingsSaved] = useState(false)
  const controller = useRef<AbortController | null>(null)
  const hasSearched = useRef(false)

  useEffect(() => {
    const abort = new AbortController()
    setSettingsError(null)
    api.settings(abort.signal).then(value => {
      setSettings(value)
      if (value.default_username && !hasSearched.current) { setUsername(value.default_username); setSearch(value.default_username) }
    }).catch(error => { if (!abort.signal.aborted) setSettingsError(error) })
    return () => abort.abort()
  }, [revision])

  useEffect(() => {
    if (!username) return
    hasSearched.current = true
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
  useEffect(() => { document.documentElement.dataset.theme = settings?.theme ?? 'system' }, [settings?.theme])

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
    <aside className="sidebar"><a className="brand" href="#main"><span className="brand-icon"><Github size={24} /></span>gitfolio<span className="brand-period">.</span></a><span className="sidebar-label">YOUR WORK, IN FOCUS</span><nav aria-label="Main navigation"><a className="nav-item active" href="#main" aria-label="Overview"><LayoutDashboard size={19} /><span>Overview</span></a><a className="nav-item" href="#activity" aria-label="Activity"><ChartNoAxesCombined size={19} /><span>Activity</span></a><a className="nav-item" href="#repositories" aria-label="Repositories"><Github size={19} /><span>Repositories</span></a><a className="nav-item" href="#career" aria-label="Career match"><BriefcaseBusiness size={19} /><span>Career match</span></a><a className="nav-item" href="#assistant" aria-label="Portfolio Assistant"><MessageCircle size={19} /><span>Assistant</span></a></nav><div className="sidebar-note"><Sparkles size={22} /><strong>More than a profile.</strong><p>A little perspective on everything you’re building.</p></div><div className="sidebar-footer"><span className="status-dot" />{useMocks ? 'Fixture preview' : 'Local workspace'}<span className="version">v1.0</span></div></aside>
    <div className="workspace"><header className="topbar"><div className="breadcrumb">Workspace <span>/</span> <strong>Overview</strong></div><div className="topbar-actions"><form className="search-form" onSubmit={event => { event.preventDefault(); const next = search.trim(); if (!next) { setError(new ApiError({ code: 'invalid_input', message: 'Enter a GitHub username.', field: 'username' })); return } if (next === username) load(); else setUsername(next) }}><label className="sr-only" htmlFor="username">GitHub username</label><Search size={17} /><input id="username" value={search} onChange={event => setSearch(event.target.value)} placeholder="Find a GitHub developer…" required autoComplete="off" spellCheck={false} /><button type="submit" aria-label="Load GitHub portfolio"><ArrowRight size={18} /></button></form><button className="icon-button settings-trigger" aria-label="Open settings" onClick={() => { setSettingsOpen(true); setSettingsSaved(false) }}><Settings2 size={19} /></button></div></header>
      <main id="main"><div className="page-heading"><div><div className="eyebrow accent">THE BIG PICTURE</div><h1>Your code. Your story.</h1><p>A fresh perspective on your work, growth, and what comes next.</p></div><button className="button secondary" disabled={!data || loading} onClick={() => load(true)}><RefreshCw size={15} className={loading ? 'spin' : ''} />Refresh data</button></div>
        {useMocks && <div className="preview-banner">Preview mode · Sample data, independent of GitHub. Try “empty”, “stale”, or “not-found” to explore states.</div>}
        {!!settingsError && <ErrorNotice error={settingsError} retry={() => setRevision(value => value + 1)} />}
        {settingsSaved && <div className="saved-notice" role="status">Preferences saved. Your default username will load next time you open the dashboard.</div>}
        {!settings && !settingsError && <Loading label="Loading your workspace…" />}
        {!!error && <ErrorNotice error={error} retry={() => load()} />}
        {loading && !data && <Loading />}
        {!username && settings && <section className="panel welcome"><Github size={42} /><h2>Your portfolio starts here</h2><p>Enter a GitHub username above to explore public work, contribution activity, and career fit.</p><button className="button primary" onClick={() => { setSearch('octocat'); setUsername('octocat') }}>Explore octocat <ArrowRight size={16} /></button></section>}
        {data && <div aria-busy={loading}>{loading && <div className="refresh-status" role="status">Refreshing portfolio data…</div>}<MetaNotice meta={data.meta} /><MatchBadge match={data.match} /><div className="overview-grid"><ProfileHeader data={data} /><LanguageChart languages={data.languages} /></div><ContributionHeatmap data={data} /><RepositoriesPanel key={`repos-${data.profile.login}-${data.meta.fetched_at}`} username={data.profile.login} /><CareerPanel key={`career-${data.profile.login}-${data.meta.fetched_at}`} username={data.profile.login} initialDescription={data.job_description} initialMatch={data.match} onMatch={result => setData(current => current ? { ...current, match: result.match, job_description: result.job_description } : current)} /><ChatPanel key={`chat-${data.profile.login}`} username={data.profile.login} /></div>}
        <footer className="page-footer"><span>Built around your public work.</span><span>Gitfolio <span className="accent">✦</span> A clearer developer story</span></footer>
      </main>
    </div>
    <SettingsDialog open={settingsOpen} settings={settings} onClose={() => setSettingsOpen(false)} onSaved={value => { setSettings(value); setSettingsError(null); setSettingsSaved(true) }} />
  </div>
}
