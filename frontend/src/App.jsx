import { useEffect, useRef, useState } from 'react'
import ChatBubble from './components/ChatBubble.jsx'
import ComparisonTable from './components/ComparisonTable.jsx'
import InputBar from './components/InputBar.jsx'
import PriceChart from './components/PriceChart.jsx'
import Sidebar from './components/Sidebar.jsx'
import StockInfoCard from './components/StockInfoCard.jsx'

const API_URL = 'http://127.0.0.1:8000/chat'
const DISCLAIMER = 'This is not financial advice.'

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
      }

      if (line.startsWith('data:')) {
        dataLines.push(line.slice(5).trim())
      }
    }

    if (dataLines.length) {
      events.push({ event, data: dataLines.join('\n') })
    }
  }

  return { events, remainder }
}

function buildAssistantData(payload) {
  const message =
    payload.message ||
    payload.data?.analysis ||
    'I could not prepare a response for that query. Please try again.'

  return {
    ...(payload.data || {}),
    message,
    analysis: payload.data?.analysis || message,
    disclaimer: payload.disclaimer || DISCLAIMER,
  }
}

const createWelcomeMessage = () => ({
  id: crypto.randomUUID(),
  role: 'assistant',
  type: 'ai_response',
  data: {
    message:
      'Welcome to NSE AI Advisor. Ask about price, valuation, risk, dividend yield, or compare two NSE-listed counters.',
    disclaimer: DISCLAIMER,
  },
})

const createConversation = (title = 'New conversation') => ({
  id: crypto.randomUUID(),
  title,
  messages: [createWelcomeMessage()],
  lastQuery: null,
})

function App() {
  const [query, setQuery] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [conversations, setConversations] = useState([createConversation()])
  const [activeConversationId, setActiveConversationId] = useState(null)
  const [voiceSupported, setVoiceSupported] = useState(false)
  const messagesEndRef = useRef(null)
  const recognitionRef = useRef(null)
  const isRecognitionActiveRef = useRef(false)
  const sendMessageRef = useRef(null)

  useEffect(() => {
    const removeInjectedWidgets = () => {
      const injectedNodes = document.querySelectorAll(
        [
          'iframe',
          '[id*="dify" i]',
          '[class*="dify" i]',
          '[src*="dify" i]',
          '[id*="gorunner" i]',
          '[class*="gorunner" i]',
        ].join(','),
      )

      injectedNodes.forEach((node) => {
        if (!node.closest('#root')) {
          node.remove()
          return
        }

        if (node.tagName.toLowerCase() === 'iframe') {
          node.remove()
        }
      })
    }

    removeInjectedWidgets()

    const observer = new MutationObserver(removeInjectedWidgets)
    observer.observe(document.body, { childList: true, subtree: true })

    return () => {
      observer.disconnect()
    }
  }, [])

  useEffect(() => {
    const firstConversation = conversations[0]
    if (firstConversation && activeConversationId === null) {
      setActiveConversationId(firstConversation.id)
    }
  }, [conversations, activeConversationId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [conversations, activeConversationId, isLoading])

  useEffect(() => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition

    if (!SpeechRecognition) {
      setVoiceSupported(false)
      return
    }

    setVoiceSupported(true)

    const recognition = new SpeechRecognition()
    recognition.lang = 'en-KE'
    recognition.interimResults = false
    recognition.maxAlternatives = 1

    recognition.onstart = () => {
      isRecognitionActiveRef.current = true
      setIsListening(true)
    }

    recognition.onresult = (event) => {
      const transcript = event.results?.[0]?.[0]?.transcript ?? ''
      if (transcript) {
        const cleanedTranscript = transcript.trim()
        setQuery(cleanedTranscript)
        sendMessageRef.current?.(cleanedTranscript)
      }
    }

    recognition.onerror = () => {
      isRecognitionActiveRef.current = false
      setIsListening(false)
    }

    recognition.onend = () => {
      isRecognitionActiveRef.current = false
      setIsListening(false)
    }

    recognitionRef.current = recognition

    return () => {
      recognition.stop()
    }
  }, [])

  const activeConversation =
    conversations.find((conversation) => conversation.id === activeConversationId) ??
    conversations[0]

  const updateActiveConversation = (updater) => {
    if (!activeConversation) {
      return
    }

    setConversations((currentConversations) =>
      currentConversations.map((conversation) =>
        conversation.id === activeConversation.id
          ? updater(conversation)
          : conversation,
      ),
    )
  }

  const appendMessage = (message) => {
    updateActiveConversation((conversation) => ({
      ...conversation,
      messages: [...conversation.messages, message],
    }))
  }

  const handleNewConversation = () => {
    const conversation = createConversation()
    setConversations((currentConversations) => [conversation, ...currentConversations])
    setActiveConversationId(conversation.id)
    setQuery('')
  }

  const handleSelectConversation = (conversationId) => {
    setActiveConversationId(conversationId)
  }

  const handleMicClick = () => {
    if (!recognitionRef.current || isLoading) {
      return
    }

    if (isListening || isRecognitionActiveRef.current) {
      recognitionRef.current.stop()
      return
    }

    try {
      recognitionRef.current.start()
    } catch {
      isRecognitionActiveRef.current = false
      setIsListening(false)
    }
  }

  const updateMessage = (messageId, updater) => {
    updateActiveConversation((conversation) => ({
      ...conversation,
      messages: conversation.messages.map((message) =>
        message.id === messageId ? updater(message) : message,
      ),
    }))
  }

  const sendMessage = async (messageText) => {
    const trimmedQuery = messageText.trim()
    if (!trimmedQuery || isLoading || !activeConversation) {
      return
    }

    appendMessage({
      id: crypto.randomUUID(),
      role: 'user',
      type: 'user_message',
      data: { message: trimmedQuery },
    })

    updateActiveConversation((conversation) => ({
      ...conversation,
      title:
        conversation.lastQuery === null
          ? trimmedQuery.slice(0, 42)
          : conversation.title,
      lastQuery: trimmedQuery,
    }))

    setQuery('')
    setIsLoading(true)

    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: trimmedQuery }),
      })

      if (!response.ok) {
        throw new Error('Unable to reach the NSE AI Advisor backend.')
      }

      const contentType = response.headers.get('content-type') || ''
      if (contentType.includes('application/json')) {
        const payload = await response.json()

        appendMessage({
          id: crypto.randomUUID(),
          role: 'assistant',
          type: payload.type ?? 'ai_response',
          data: buildAssistantData(payload),
        })
        return
      }

      const assistantMessageId = crypto.randomUUID()
      appendMessage({
        id: assistantMessageId,
        role: 'assistant',
        type: 'ai_response',
        data: { message: '', analysis: '', disclaimer: DISCLAIMER },
      })

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { value, done } = await reader.read()
        if (done) {
          break
        }

        buffer += decoder.decode(value, { stream: true })
        const parsed = parseSseBuffer(buffer)
        buffer = parsed.remainder

        for (const item of parsed.events) {
          if (item.event === 'metadata') {
            const payload = JSON.parse(item.data)
            updateMessage(assistantMessageId, (message) => ({
              ...message,
              type: payload.type ?? message.type,
              data: {
                ...buildAssistantData(payload),
                message: message.data.message || '',
                analysis: message.data.analysis || '',
              },
            }))
          }

          if (item.event === 'token') {
            updateMessage(assistantMessageId, (message) => {
              const nextText = `${message.data.message || ''}${item.data}`
              return {
                ...message,
                data: {
                  ...message.data,
                  message: nextText,
                  analysis: nextText,
                },
              }
            })
          }
        }
      }
    } catch (error) {
      appendMessage({
        id: crypto.randomUUID(),
        role: 'assistant',
        type: 'ai_response',
        data: {
          message:
            error.message ||
            'There was a problem processing your request. Please try again.',
          disclaimer: DISCLAIMER,
        },
      })
    } finally {
      setIsLoading(false)
    }
  }

  sendMessageRef.current = sendMessage

  const handleSubmit = async (event) => {
    event.preventDefault()
    await sendMessage(query)
  }

  return (
    <div className="min-h-screen overflow-x-hidden bg-[radial-gradient(circle_at_top,_rgba(129,140,248,0.12),_transparent_36%),linear-gradient(180deg,_#f6f6fb_0%,_#f3f2f9_55%,_#efedf6_100%)] text-slate-900">
      <div className="mx-auto flex min-h-screen max-w-[1640px] min-w-0 flex-col px-0 pb-6 pt-0 lg:px-0">
        <header className="border-b border-slate-200/80 bg-white/70 px-6 py-10 backdrop-blur sm:px-8 lg:px-12">
          <div className="flex items-center gap-4">
            <span className="text-4xl font-semibold tracking-tight text-blue-600">
              NSE
            </span>
            <span className="text-4xl font-light tracking-tight text-slate-700">
              AI Advisor
            </span>
          </div>
          </header>
        <div className="flex min-w-0 flex-1 flex-col lg:flex-row">
          <section className="flex min-w-0 w-full flex-col border-r border-slate-200/70 bg-white/10 lg:w-4/5">
            <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 lg:px-7">
              <div className="h-full rounded-[2rem] border border-white/80 bg-white/90 px-4 py-5 shadow-[0_18px_60px_rgba(128,137,177,0.16)] sm:px-6">
                <div className="mx-auto flex min-h-[56vh] w-full max-w-5xl min-w-0 flex-col gap-5">
                  {activeConversation?.messages.length === 1 && !isLoading && (
                    <div className="flex flex-1 items-center justify-center rounded-[1.75rem] border border-dashed border-slate-200 bg-[linear-gradient(180deg,_rgba(255,255,255,0.95),_rgba(247,247,252,0.9))] p-10 text-center">
                      <div className="max-w-xl">
                        <p className="text-lg text-slate-400">
                          Ask about Safaricom, Kenya Airways, dividends,
                          valuation, risk, or compare two NSE counters.
                        </p>
                      </div>
                    </div>
                  )}

                  {activeConversation?.messages.map((message) => (
                    <ChatBubble key={message.id} role={message.role}>
                      {message.role === 'user' ? (
                        <p className="whitespace-pre-wrap break-words text-sm leading-7 [overflow-wrap:anywhere] sm:text-[15px]">
                          {message.data.message}
                        </p>
                      ) : (
                        <>
                          {message.type === 'stock_info' && (
                            <div className="space-y-4">
                              <StockInfoCard data={message.data} />
                              <PriceChart stock={message.data} />
                            </div>
                          )}
                          {message.type === 'comparison' && (
                            <div className="space-y-4">
                              <ComparisonTable data={message.data} />
                              <PriceChart
                                stock1={message.data.stock1}
                                stock2={message.data.stock2}
                              />
                            </div>
                          )}
                          {message.type !== 'stock_info' &&
                            message.type !== 'comparison' && (
                              <div className="space-y-3">
                                <p className="whitespace-pre-wrap break-words text-sm leading-7 text-slate-700 [overflow-wrap:anywhere] sm:text-[15px]">
                                  {message.data.message}
                                </p>
                                {message.data.disclaimer && (
                                  <p className="text-xs text-slate-400">
                                    Disclaimer: {message.data.disclaimer}
                                  </p>
                                )}
                              </div>
                            )}
                        </>
                      )}
                    </ChatBubble>
                  ))}

                  {isLoading && (
                    <ChatBubble role="assistant">
                      <div className="flex items-center gap-3 text-sm text-slate-500">
                        <span className="h-2 w-2 animate-bounce rounded-full bg-blue-500 [animation-delay:-0.2s]" />
                        <span className="h-2 w-2 animate-bounce rounded-full bg-blue-500 [animation-delay:-0.1s]" />
                        <span className="h-2 w-2 animate-bounce rounded-full bg-blue-500" />
                        <span>Thinking...</span>
                      </div>
                    </ChatBubble>
                  )}

                  <div ref={messagesEndRef} />
                </div>
              </div>
            </div>

            <div className="border-t border-slate-200/70 bg-white/20 px-4 py-5 sm:px-6 lg:px-7">
              <div className="mx-auto w-full max-w-5xl">
                <InputBar
                  isListening={isListening}
                  isLoading={isLoading}
                  onMicClick={handleMicClick}
                  onQueryChange={setQuery}
                  onSubmit={handleSubmit}
                  query={query}
                  voiceSupported={voiceSupported}
                />
              </div>
            </div>
          </section>

          <aside className="w-full bg-white/20 lg:w-1/5">
            <Sidebar
              activeConversationId={activeConversation?.id}
              conversations={conversations}
              onNewConversation={handleNewConversation}
              onSelectConversation={handleSelectConversation}
            />
          </aside>
        </div>
      </div>
    </div>
  )
}

export default App
