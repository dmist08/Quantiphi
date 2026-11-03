import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import type { Dashboard } from '../types/api'

export function LanguageChart({ languages }: { languages: Dashboard['languages'] }) {
  return <section className="panel languages-panel" aria-labelledby="languages-title">
    <div className="section-heading"><h2 id="languages-title">Top languages</h2><span className="eyebrow">BY CODE SIZE</span></div>
    {languages.length === 0 ? <p className="empty-copy">No public language data yet.</p> : <div className="language-content">
      <div className="donut-wrap" aria-hidden="true"><ResponsiveContainer width="100%" height={160}>
        <PieChart><Pie data={languages} dataKey="percent" nameKey="name" innerRadius={51} outerRadius={72} paddingAngle={4} stroke="none" isAnimationActive={false}>
          {languages.map(language => <Cell key={language.name} fill={language.color ?? '#a2a7b7'} />)}
        </Pie><Tooltip formatter={value => `${value}%`} /></PieChart>
      </ResponsiveContainer><div className="donut-center"><strong>{languages.length}</strong><span>languages</span></div></div>
      <ul className="language-legend">{languages.map(language => <li key={language.name}><span className="color-dot" style={{ backgroundColor: language.color ?? '#a2a7b7' }} /><span>{language.name}</span><strong>{language.percent}%</strong></li>)}</ul>
    </div>}
    <p className="panel-footnote">Across owned, non-fork public repositories.</p>
  </section>
}
