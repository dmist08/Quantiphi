import { ArrowUpRight, BookOpen, Github, Star, Users } from 'lucide-react'
import type { Dashboard, MatchResult } from '../types/api'

export function MatchBadge({ match }: { match: MatchResult | null }) {
  const enough = match?.status === 'ok' && match.score !== null
  return <div className="match-badge"><span className="match-icon">✦</span><div><span className="eyebrow">CAREER MATCH</span><strong>{match ? enough ? `${match.score}% match` : 'Not enough assessable keywords' : 'Your next chapter awaits'}</strong><small>{match ? 'Based on public repository languages' : 'Add a job description to discover your fit'}</small></div><a href="#career" aria-label="Explore career match"><ArrowUpRight size={20} /></a></div>
}

export function ProfileHeader({ data }: { data: Dashboard }) {
  const { profile, stats } = data
  return <section className="panel profile-panel" aria-labelledby="profile-name"><div className="profile-banner"><span className="profile-label"><Github size={14} /> PUBLIC DEVELOPER PROFILE</span><span className="banner-decoration">{'{ }'}</span></div>
    <div className="profile-content"><div className="profile-top"><div className="avatar">{profile.avatar_url ? <img src={profile.avatar_url} alt={`${profile.login}'s avatar`} /> : <Github size={36} />}</div>{profile.url && <a className="button secondary small" href={profile.url} target="_blank" rel="noreferrer">GitHub <ArrowUpRight size={14} /></a>}</div>
      <h2 id="profile-name">{profile.name ?? profile.login}</h2><p className="handle">@{profile.login}</p><p className="bio">{profile.bio ?? 'Building a story through public code.'}</p>
      <div className="profile-stats"><div><Users size={16} /><strong>{profile.followers.toLocaleString()}</strong><span>Followers</span></div><div><Star size={16} /><strong>{stats.total_stars.toLocaleString()}</strong><span>Total stars</span></div><div><BookOpen size={16} /><strong>{stats.public_repos.toLocaleString()}</strong><span>Repositories</span></div></div>
    </div>
  </section>
}
