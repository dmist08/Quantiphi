import { useEffect, useRef, useState } from 'react'
import { Check, Monitor, Moon, Sun, X } from 'lucide-react'
import { api } from '../api/client'
import type { Settings } from '../types/api'
import { ErrorNotice } from './Feedback'

export function SettingsDialog({ open, settings, onClose, onSaved }: {
  open: boolean; settings: Settings | null; onClose: () => void; onSaved: (settings: Settings) => void
}) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const abortRef = useRef<AbortController | null>(null)
  const [username, setUsername] = useState('')
  const [theme, setTheme] = useState<Settings['theme']>('system')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>(null)

  useEffect(() => {
    if (open) {
      setUsername(settings?.default_username ?? '')
      setTheme(settings?.theme ?? 'system')
      setError(null)
      dialogRef.current?.showModal()
    } else { dialogRef.current?.close(); abortRef.current?.abort(); setBusy(false) }
  }, [open, settings])
  useEffect(() => () => abortRef.current?.abort(), [])

  async function save() {
    const abort = new AbortController()
    abortRef.current = abort
    setBusy(true)
    setError(null)
    try {
      // Both fields are required here: omitting either resets it on the server.
      const saved = await api.saveSettings({ default_username: username.trim() || null, theme }, abort.signal)
      onSaved(saved)
      onClose()
    } catch (error) { if (!abort.signal.aborted) setError(error) }
    finally { if (!abort.signal.aborted) setBusy(false) }
  }

  return <dialog ref={dialogRef} className="settings-dialog" aria-labelledby="settings-title" onClose={onClose}><div className="dialog-heading"><div><div className="eyebrow accent">YOUR WORKSPACE</div><h2 id="settings-title">Make yourself at home.</h2></div><button className="icon-button" onClick={onClose} aria-label="Close settings"><X size={19} /></button></div>
    <form onSubmit={event => { event.preventDefault(); void save() }}><label className="settings-label" htmlFor="default-username">Default GitHub username</label><input id="default-username" value={username} onChange={event => setUsername(event.target.value)} placeholder="e.g. octocat" disabled={busy} autoComplete="off" spellCheck={false} aria-describedby="default-help" /><p id="default-help" className="field-help">Load this developer when you open the dashboard. Leave blank to start with search.</p>
      <fieldset disabled={busy}><legend>Appearance</legend><div className="theme-options">{([{ value: 'light', label: 'Light', Icon: Sun }, { value: 'dark', label: 'Dark', Icon: Moon }, { value: 'system', label: 'System', Icon: Monitor }] as const).map(({ value, label, Icon }) => <label className={`theme-option ${theme === value ? 'selected' : ''}`} key={value}><input type="radio" name="theme" value={value} checked={theme === value} onChange={() => setTheme(value)} /><Icon size={18} /><span>{label}</span>{theme === value && <Check size={12} />}</label>)}</div></fieldset>
      {!!error && <ErrorNotice error={error} />}<div className="dialog-actions"><button type="button" className="button secondary" onClick={onClose}>Cancel</button><button type="submit" className="button primary" disabled={busy}>{busy ? 'Saving…' : 'Save preferences'}</button></div>
    </form>
  </dialog>
}
