import { Flame, TrendingUp } from 'lucide-react'
import type { Dashboard } from '../types/api'

export function ContributionHeatmap({ data }: { data: Dashboard }) {
  const { contributions, stats } = data
  return <section className="panel activity-panel" id="activity" aria-labelledby="activity-title">
    <div className="section-heading"><div><h2 id="activity-title">A year of showing up</h2><p><strong>{contributions.total.toLocaleString()}</strong> contributions{contributions.start_date && <> · {contributions.start_date} to {contributions.end_date}</>}</p></div><span className="pill"><span className="status-dot" />Contribution activity</span></div>
    {contributions.weeks.length === 0 ? <p className="empty-copy">No contribution activity to display yet.</p> : <div className="heatmap-scroll" tabIndex={0} role="region" aria-label="Contribution calendar. Scroll horizontally to explore all weeks.">
      <div className="heatmap" style={{ '--weeks': contributions.weeks.length } as React.CSSProperties}>
        <div className="month-labels">{contributions.months.map((month, index) => <span key={index} style={{ gridColumn: month.week_index + 1 }}>{month.label}</span>)}</div>
        <div className="day-labels" aria-hidden="true"><span>Mon</span><span>Wed</span><span>Fri</span></div>
        <div className="calendar-weeks">{contributions.weeks.map((week, weekIndex) => <div className="calendar-week" key={weekIndex}>{week.map((day, dayIndex) => day ? <button type="button" key={day.date} className={`calendar-day level-${day.level}`} aria-label={`${day.date}: ${day.count} contributions`}><span className="day-tooltip" role="tooltip">{day.count} contributions on {day.date}</span></button> : <span className="calendar-padding" key={`padding-${dayIndex}`} />)}</div>)}</div>
      </div>
    </div>}
    <div className="heatmap-bottom"><span className="muted">Every contribution tells a story.</span><div className="heatmap-legend" aria-label="Contribution levels from less to more">Less{[0, 1, 2, 3, 4].map(level => <span key={level} className={`legend-square level-${level}`} />)}More</div></div>
    <div className="activity-stats"><div><Flame size={18} /><span>Current streak<strong>{stats.current_streak} days</strong></span></div><div><TrendingUp size={18} /><span>Longest streak<strong>{stats.longest_streak} days</strong></span></div><div><span className="stat-symbol">↗</span><span>Active days<strong>{stats.active_days} days</strong></span></div><div><span className="stat-symbol">✦</span><span>Best day<strong>{stats.best_day ? `${stats.best_day.count} contributions` : 'No activity yet'}</strong></span></div></div>
  </section>
}
