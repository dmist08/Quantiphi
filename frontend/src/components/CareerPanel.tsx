import { useEffect, useRef, useState } from 'react'
import { ArrowRight, ArrowUpRight, Check, Compass, FileText, Sparkles } from 'lucide-react'
import { api } from '../api/client'
import type { GapCoach, MatchResponse, MatchResult } from '../types/api'
import { ErrorNotice, Loading, MetaNotice } from './Feedback'

function Score({ match }: { match: Pick<MatchResult, 'score' | 'status'> }) {
  return match.status === 'no_assessable_keywords' || match.score === null
    ? <strong className="no-score">Not enough assessable keywords</strong>
    : <strong className="match-score">{match.score}<span>%</span></strong>
}

function MatchDetails({ match }: { match: MatchResult }) {
  return <><div className="score-summary"><div><div className="eyebrow accent">LANGUAGE COVERAGE</div><Score match={match} /></div><span className="score-context">{match.matched_count} matched<br />{match.assessable_count} assessable</span></div><p className="score-explanation">{match.explanation}</p>
    <div className="match-group"><h3><Check size={13} />Matched skills</h3>{match.matched.length === 0 && <p>No matching language evidence found.</p>}{match.matched.map(item => <div className="matched-item" key={item.name}><span className="tag positive">{item.name}</span><div>{item.evidence.map(evidence => <a key={`${evidence.repo}-${evidence.language}`} href={evidence.url} target="_blank" rel="noreferrer">{evidence.repo} <span>· {evidence.language}</span><ArrowUpRight size={11} /></a>)}</div></div>)}</div>
    <div className="match-group"><h3>Gaps to explore</h3><div className="tag-list">{match.missing.map(item => <span className="tag gap" key={item.name}>{item.name}</span>)}</div>{match.missing.length === 0 && <p>No missing assessable skills.</p>}</div>
    <div className="match-group"><h3>Cannot assess from repository languages</h3><div className="tag-list">{match.unassessable.map(item => <span className="tag" key={item}>{item}</span>)}</div>{match.unassessable.length === 0 && <p>No recognized unassessable skills.</p>}</div>
  </>
}

function CoachDetails({ coach }: { coach: GapCoach }) {
  return <div className="coach-result"><div className="section-heading"><h3><Compass size={15} />Your gap coach</h3><span className="tag">Repository evidence</span></div>
    <div className="coach-score"><Score match={coach} /></div>
    {coach.strengths.map(strength => <div className="coach-strength" key={strength.name}><strong>{strength.name}</strong><p>{strength.summary}</p><div className="evidence-links">{strength.evidence.map(evidence => <a href={evidence.url} target="_blank" rel="noreferrer" key={`${evidence.repo}-${evidence.language}`}>{evidence.repo} · {evidence.language}<ArrowUpRight size={11} /></a>)}</div></div>)}
    <h4>Missing language evidence</h4><div className="tag-list">{coach.missing.map(item => <span className="tag gap" key={item}>{item}</span>)}{coach.missing.length === 0 && <p className="muted">No gaps identified.</p>}</div>
    {coach.unassessable.length > 0 && <><h4>Not assessable from languages</h4><div className="tag-list">{coach.unassessable.map(item => <span className="tag" key={item}>{item}</span>)}</div></>}
    {coach.highlight_repos.length > 0 && <><h4>Projects to put forward</h4>{coach.highlight_repos.map(repo => <div className="coach-project" key={repo.url}><a href={repo.url} target="_blank" rel="noreferrer">{repo.name}<ArrowUpRight size={12} /></a><p>{repo.reason}</p><small>{repo.stars} stars · {repo.matched_languages.join(', ')}</small></div>)}</>}
    <h4>Your talking points</h4><div className="pitch">{coach.pitch.map((line, index) => <p key={index}>{line}</p>)}</div><p className="coach-disclaimer">{coach.disclaimer}</p>
  </div>
}

export function CareerPanel({ username, initialDescription, initialMatch, onMatch }: {
  username: string; initialDescription: string | null; initialMatch: MatchResult | null
  onMatch: (result: MatchResponse) => void
}) {
  const [description, setDescription] = useState(initialDescription ?? '')
  const [result, setResult] = useState<MatchResponse | null>(null)
  const [coach, setCoach] = useState<GapCoach | null>(null)
  const [busy, setBusy] = useState<'match' | 'coach' | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [evaluatedDescription, setEvaluatedDescription] = useState(initialDescription ?? '')
  const abortRef = useRef<AbortController | null>(null)
  const match = result?.match ?? initialMatch
  const edited = description !== evaluatedDescription

  useEffect(() => () => abortRef.current?.abort(), [])

  async function evaluate(action: 'match' | 'coach') {
    abortRef.current?.abort()
    const abort = new AbortController()
    abortRef.current = abort
    setBusy(action)
    setError(null)
    try {
      if (action === 'match') {
        const response = await api.match(username, description, abort.signal)
        setResult(response)
        setDescription(response.job_description)
        setEvaluatedDescription(response.job_description)
        setCoach(null)
        onMatch(response)
      } else {
        setCoach(await api.coach(username, description, abort.signal))
      }
    } catch (error) { if (!abort.signal.aborted) setError(error) }
    finally { if (!abort.signal.aborted) setBusy(null) }
  }

  return <section id="career" className="panel career-panel" aria-labelledby="career-title"><div className="section-heading"><div><div className="eyebrow accent">MAKE YOUR NEXT MOVE</div><h2 id="career-title">Find where your work fits</h2><p>Connect the code you’ve written with the role you’re looking for.</p></div><span className="feature-icon"><Sparkles size={20} /></span></div>
    <div className="career-layout"><form className="jd-form" onSubmit={event => { event.preventDefault(); void evaluate('match') }}><label htmlFor="job-description"><FileText size={15} />Job description</label><p>Paste a role to compare its technology requirements with your public repositories.</p><textarea id="job-description" value={description} onChange={event => { setDescription(event.target.value); setCoach(null); setError(null) }} rows={9} placeholder="We’re looking for a developer with Python, TypeScript, and Rust experience…" disabled={busy !== null} aria-describedby="jd-help" /><div id="jd-help" className="field-help">Up to 20,000 characters. Your latest analyzed description is saved per developer.</div><div className="jd-actions"><button type="submit" className="button primary" disabled={busy !== null}>{busy === 'match' ? 'Analyzing…' : 'Analyze match'}<ArrowRight size={14} /></button><button type="button" className="button secondary" disabled={busy !== null} onClick={() => void evaluate('coach')}><Compass size={14} />{busy === 'coach' ? 'Preparing…' : 'Get gap coaching'}</button></div>{!!error && <ErrorNotice error={error} />}</form>
      <div className="career-results" aria-live="polite" aria-busy={busy !== null}>{busy && <Loading label={busy === 'match' ? 'Comparing repository evidence…' : 'Preparing your talking points…'} />}{!busy && <>{match ? <>{edited && <div className="draft-note">Description edited. Analyze again to update the saved match.</div>}{result && <MetaNotice meta={result.meta} />}<MatchDetails match={match} /></> : <div className="match-placeholder"><div className="placeholder-orbit"><Sparkles size={28} /></div><h3>Your experience, in perspective.</h3><p>Add a job description to see matching languages, gaps, and the projects that support your story.</p><span className="pill">Grounded in your public repositories</span></div>}{coach && <CoachDetails coach={coach} />}</>}</div>
    </div><div className="career-footnote">Language coverage shows public code evidence. It does not measure proficiency or hiring suitability.</div>
  </section>
}
