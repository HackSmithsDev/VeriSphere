import { useEffect, useRef, useState } from 'react'
import { ArrowUp, Bot, Sparkles } from 'lucide-react'
import { chatWithAssistant } from '../../api/assistant'
import { ActionButton } from '../ui/ActionButton'
import { Card } from '../ui/Card'

export function AssistantChat({ role, token }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, busy])

  const sendMessage = async (event) => {
    event.preventDefault()
    const content = input.trim()
    if (!content || busy) return

    const updatedMessages = [...messages, { role: 'user', content }]
    const history = updatedMessages.slice(-12)
    setMessages(updatedMessages)
    setInput('')
    setError('')
    setBusy(true)
    try {
      const result = await chatWithAssistant(token, history)
      setMessages([...updatedMessages, { role: 'assistant', content: result.reply }])
    } catch (requestError) {
      setMessages(messages)
      setInput(content)
      setError(requestError.message)
    } finally {
      setBusy(false)
    }
  }

  const isTeacher = role === 'teacher'
  return (
    <div className="assistant-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">PERSONALIZED GUIDANCE</span>
          <h1>Learning assistant</h1>
          <p className="muted">
            {isTeacher
              ? 'Get ideas for constructive feedback and next steps from pending evidence.'
              : 'Ask questions and get suggestions based on your learning progress.'}
          </p>
        </div>
        <span className="theme-badge"><Sparkles size={13} /> AI assistant</span>
      </div>

      <Card className="assistant-card">
        <div className="assistant-messages" aria-live="polite">
          {messages.length === 0 && (
            <div className="assistant-empty">
              <span className="assistant-icon"><Bot size={22} /></span>
              <strong>{isTeacher ? 'Plan supportive next steps' : 'Make your next step clear'}</strong>
              <p>
                {isTeacher
                  ? 'Ask for feedback ideas, resources, or follow-up questions for current submissions.'
                  : 'Ask what to focus on next, or how to approach a milestone you are working through.'}
              </p>
            </div>
          )}
          {messages.map((message, index) => (
            <div
              className={`assistant-message assistant-message-${message.role}`}
              key={`${index}-${message.role}`}
            >
              {message.role === 'assistant' && <Bot size={16} aria-hidden="true" />}
              <p>{message.content}</p>
            </div>
          ))}
          {busy && <div className="assistant-thinking" role="status">Thinking…</div>}
          <div ref={bottomRef} />
        </div>
        {error && <div className="assistant-error" role="alert">{error}</div>}
        <form className="assistant-form" onSubmit={sendMessage}>
          <label className="sr-only" htmlFor="assistant-question">Your question</label>
          <textarea
            id="assistant-question"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Ask a question…"
            maxLength={2000}
            rows={2}
            disabled={busy}
          />
          <ActionButton
            type="submit"
            aria-label="Send question"
            disabled={busy || !input.trim()}
          >
            <ArrowUp size={17} />
          </ActionButton>
        </form>
        <p className="assistant-disclaimer">
          Your chat and relevant learning context are sent to the configured AI provider.
          AI suggestions can be incomplete; verify important academic decisions with your instructor.
        </p>
      </Card>
    </div>
  )
}
