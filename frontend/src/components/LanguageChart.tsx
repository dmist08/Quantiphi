import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import type { Dashboard } from '../types/api'

export function LanguageChart({ languages }: { languages: Dashboard['languages'] }) {
  // Presentation only: retain the API's percentages unchanged.
  const visibleLanguages = languages.filter(language => language.percent !== 0)
  return <section className="panel languages-panel" aria-labelledby="languages-title">
    <div className="section-heading"><h2 id="languages-title">Top languages</h2><span className="eyebrow">BY CODE SIZE</span></div>
    {visibleLanguages.length === 0 ? <p className="empty-copy">No public language data yet.</p> : <div className="language-content">
      <div className="donut-wrap" aria-hidden="true"><ResponsiveContainer width="100%" height={160}>
        <PieChart><Pie data={visibleLanguages} dataKey="percent" nameKey="name" innerRadius={51} outerRadius={72} paddingAngle={4} stroke="none" isAnimationActive={false}>
          {visibleLanguages.map(language => <Cell key={language.name} fill={language.color ?? '#a2a7b7'} />)}
        </Pie><Tooltip formatter={value => `${value}%`} /></PieChart>
      </ResponsiveContainer><div className="donut-center"><strong>{visibleLanguages.length}</strong><span>languages</span></div></div>
      <ul className="language-legend">{visibleLanguages.map(language => <li key={language.name}><span className="color-dot" style={{ backgroundColor: language.color ?? '#a2a7b7' }} /><span>{language.name}</span><strong>{language.percent}%</strong></li>)}</ul>
    </div>}
    <p className="panel-footnote">Across owned, non-fork public repositories.</p>
  </section>
}
