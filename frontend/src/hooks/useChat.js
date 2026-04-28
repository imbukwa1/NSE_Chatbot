import { useEffect, useRef, useState } from 'react'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8001'
const DISCLAIMER = 'This is not financial advice.'

function getRequestErrorMessage(error) {
  if (error.name === 'AbortError' || error.message?.includes('aborted')) {
    return 'Request timed out before the advisor finished. Please try a narrower comparison or ask again.'
  }

  return (
    error.message ||
    'There was a problem processing your request. Please try again.'
  )
}

const createWelcomeMessage = () => ({
  id: crypto.randomUUID(),
  role: 'assistant',
  type: 'ai_response',
  data: {},
  message:
    'Welcome to NSE AI Advisor. Ask about price, comparison, risk, or performance.',
  disclaimer: DISCLAIMER,
})

function parseSseBuffer(buffer) {
  const events = []
  const parts = buffer.split('\n\n')
  const remainder = parts.pop() ?? ''

  for (const part of parts) {
    const lines = part.split('\n')
    let event = 'message'
    const dataLines = []

    for (const line of lines) {
      if (line.startsWith('event:')) {
        event = line.slice(6).trim()
      } else if (line.startsWith('data:')) {
        dataLines.push(line.slice(5).trim())
      }
    }

    if (dataLines.length) {
      events.push({ event, data: dataLines.join('\n') })
    }
  }

  return { events, remainder }
}

export function useChat() {
  const [messages, setMessages] = useState([createWelcomeMessage()])
  const [isLoading, setIsLoading] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState('checking')
  const activeStreamMessageId = useRef(null)

  useEffect(() => {
    let cancelled = false

    async function checkHealth() {
      try {
        const response = await fetch(`${API_BASE_URL}/health`)
        if (!response.ok) throw new Error('Health check failed')
        if (!cancelled) setConnectionStatus('online')
      } catch {
        if (!cancelled) setConnectionStatus('offline')
      }
    }

    checkHealth()
    return () => {
      cancelled = true
    }
  }, [])

  const appendMessage = (message) => {
    setMessages((current) => [...current, message])
  }

  const updateMessage = (messageId, updater) => {
    setMessages((current) =>
      current.map((message) =>
        message.id === messageId ? updater(message) : message,
      ),
    )
  }

  const sendMessage = async (query) => {
    const trimmedQuery = query.trim()
    if (!trimmedQuery) return

    appendMessage({
      id: crypto.randomUUID(),
      role: 'user',
      type: 'user_message',
      data: {},
      message: trimmedQuery,
      disclaimer: '',
    })

    setIsLoading(true)

    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: trimmedQuery }),
      })

      const contentType = response.headers.get('content-type') || ''

      if (contentType.includes('application/json')) {
        const payload = await response.json()
        appendMessage({
          id: crypto.randomUUID(),
          role: 'assistant',
          type: payload.type,
          data: payload.data || {},
          message: payload.message || '',
          disclaimer: payload.disclaimer || DISCLAIMER,
        })
        return
      }

      const assistantMessageId = crypto.randomUUID()
      activeStreamMessageId.current = assistantMessageId

      appendMessage({
        id: assistantMessageId,
        role: 'assistant',
        type: 'ai_response',
        data: {},
        message: '',
        disclaimer: DISCLAIMER,
        isStreaming: true,
      })

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      try {
        while (true) {
          const { value, done } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const parsed = parseSseBuffer(buffer)
          buffer = parsed.remainder

          for (const item of parsed.events) {
            if (item.event === 'metadata') {
              const payload = JSON.parse(item.data)
              updateMessage(assistantMessageId, (message) => ({
                ...message,
                type: payload.type,
                data: payload.data || {},
                disclaimer: payload.disclaimer || DISCLAIMER,
              }))
            }

            if (item.event === 'token') {
              updateMessage(assistantMessageId, (message) => {
                const nextMessage = `${message.message}${item.data}`
                const nextData =
                  message.type === 'comparison'
                    ? {
                        ...message.data,
                        scorecard: {
                          ...(message.data.scorecard || {}),
                          analysis: nextMessage,
                        },
                      }
                    : message.data

                return {
                  ...message,
                  message: nextMessage,
                  data: nextData,
                }
              })
            }

            if (item.event === 'done') {
              updateMessage(assistantMessageId, (message) => ({
                ...message,
                isStreaming: false,
              }))
            }
          }
        }
      } finally {
        reader.releaseLock()
      }
    } catch (error) {
      appendMessage({
        id: crypto.randomUUID(),
        role: 'assistant',
        type: 'ai_response',
        data: {},
        message: getRequestErrorMessage(error),
        disclaimer: DISCLAIMER,
      })
    } finally {
      activeStreamMessageId.current = null
      setIsLoading(false)
    }
  }

  return {
    messages,
    isLoading,
    connectionStatus,
    sendMessage,
  }
}
