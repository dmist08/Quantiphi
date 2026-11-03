import { useEffect, useRef, useState } from 'react'
import { ArrowUp, ArrowUpRight, CheckCheck, MessageCircle, RotateCcw, Sparkles } from 'lucide-react'
import { api } from '../api/client'
import type { ChatMessage, ChatResponse } from '../types/api'
import { ErrorNotice } from './Feedback'

interface DisplayMessage extends ChatMessage { id: number; response?: ChatResponse }
const initialSuggestions = ['What are my top languages?', 'Which are my best repos?', 'What is my current streak?', 'What is my match score?', 'What are my gaps?', 'How can I improve my portfolio?']

export function ChatPanel({ username }: { username: string }) {
  const [messages, setMessages] = useState<DisplayMessage[]>([])
  const [draft, setDraft] = useState('')
  const [suggestions, setSuggestions] = useState(initialSuggestions)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const [failed, setFailed] = useState<{ message: string; history: ChatMessage[] } | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const idRef = useRef(0)
  const historyRef = useRef<HTMLDivElement>(null)

  useEffect(() => () => abortRef.current?.abort(), [])
  useEffect(() => {
    const history = historyRef.current
    if (history) history.scrollTop = history.scrollHeight
  }, [messages, loading])

  async function send(message: string, retry = false) {
    if (loading) return
    const history = retry && failed ? failed.history : messages.slice(-20).map(({ role, content }) => ({ role, content: content.slice(0, 4000) }))
    const abort = new AbortController()
    abortRef.current = abort
    setLoading(true)
    setError(null)
    setFailed(null)
    setDraft('')
    if (!retry && message.trim()) setMessages(previous => [...previous, { id: ++idRef.current, role: 'user', content: message }])
    try {
      const response = await api.chat(username, message, history, abort.signal)
      setMessages(previous => [...previous, { id: ++idRef.current, role: 'assistant', content: response.answer, response }])
      setSuggestions(response.suggestions)
    } catch (error) {
      if (!abort.signal.aborted) { setError(error); setFailed({ message, history }) }
    } finally { if (!abort.signal.aborted) setLoading(false) }
  }

  function clear() {
    abortRef.current?.abort()
    setMessages([])
    setSuggestions(initialSuggestions)
    setDraft('')
    setLoading(false)
    setFailed(null)
    setError(null)
  }

  return <section id="assistant" className="panel chat-panel" aria-labelledby="assistant-title"><div className="section-heading"><div className="assistant-title"><span className="feature-icon"><MessageCircle size={19} /></span><div><h2 id="assistant-title">Portfolio Assistant</h2><p>A conversation with the facts behind your work.</p></div></div><button className="icon-button" aria-label="Clear conversation" title="Clear conversation" disabled={messages.length === 0 && !loading} onClick={clear}><RotateCcw size={16} /></button></div>
    <div className="chat-body"><div className="chat-intro"><span className="eyebrow accent">LET’S TALK ABOUT YOUR WORK</span><h3>A little clarity goes a long way.</h3><p>Ask about your languages, standout repositories, contribution streaks, or saved career match.</p><span className="assistant-source"><CheckCheck size={13} />Answers grounded in cached portfolio data</span></div>
      <div className="chat-conversation"><div className="chat-history" ref={historyRef} role="log" aria-label="Portfolio Assistant conversation" aria-live="polite" aria-relevant="additions text" tabIndex={0}>
        {messages.length === 0 && <div className="chat-empty"><Sparkles size={21} /><p>What would you like to know about @{username}?</p><span>Choose a question below to get started.</span></div>}
        {messages.map(message => <article className={`chat-message ${message.role}`} key={message.id}><span className="message-label">{message.role === 'user' ? 'You' : 'Portfolio Assistant'}</span><p>{message.content}</p>{message.response && message.response.evidence.length > 0 && <details className="chat-evidence"><summary>View supporting evidence</summary><ul>{message.response.evidence.map((evidence, index) => <li key={index}>{evidence.url ? <a href={evidence.url} target="_blank" rel="noreferrer">{evidence.label}<ArrowUpRight size={11} /></a> : <strong>{evidence.label}</strong>}<span>{evidence.value}</span></li>)}</ul></details>}</article>)}
        {loading && <div className="chat-thinking" role="status"><span className="typing-dots"><i /><i /><i /></span>Checking portfolio facts…</div>}
      </div>
      {!!error && <ErrorNotice error={error} retry={failed ? () => void send(failed.message, true) : undefined} />}
      <div className="suggested-questions" aria-label="Suggested questions">{suggestions.map(question => <button key={question} type="button" disabled={loading} onClick={() => void send(question)}>{question}<ArrowUpRight size={11} /></button>)}</div>
      <form className="chat-composer" onSubmit={event => { event.preventDefault(); void send(draft) }}><label className="sr-only" htmlFor="chat-message">Ask Portfolio Assistant</label><textarea id="chat-message" rows={1} value={draft} onChange={event => setDraft(event.target.value)} placeholder="Ask about this portfolio…" aria-describedby="chat-help" disabled={loading} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); void send(draft) } }} /><button className="send-button" type="submit" aria-label="Send message" disabled={loading}><ArrowUp size={18} /></button></form><p className="chat-help" id="chat-help">Up to 2,000 characters · Enter to send · Shift + Enter for a new line</p></div>
    </div>
  </section>
}
