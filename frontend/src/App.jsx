import { useEffect, useRef, useState } from 'react'
import AboutPage from './components/AboutPage.jsx'
import ChatBubble from './components/ChatBubble.jsx'
import ComparisonTable from './components/ComparisonTable.jsx'
import InputBar from './components/InputBar.jsx'
import AdminDashboardScreen from './components/AdminDashboardScreen.jsx'
import MarketOverview from './components/MarketOverview.jsx'
import PriceChart from './components/PriceChart.jsx'
import PortfolioTable from './components/PortfolioTable.jsx'
import StockDetailsScreen from './components/StockDetailsScreen.jsx'
import StockListTable from './components/StockListTable.jsx'
import UserProfileScreen from './components/UserProfileScreen.jsx'
import { useNissy } from './hooks/useNissy.js'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8001'
const API_URL = `${API_BASE_URL}/chat`
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
  data: {
    message:
      'Welcome to NSE AI Advisor. Ask about price, valuation, risk, dividend yield, news, or compare NSE-listed counters.',
    disclaimer: DISCLAIMER,
  },
})

const createConversation = (title = 'New conversation') => ({
  id: crypto.randomUUID(),
  title,
  messages: [createWelcomeMessage()],
  lastQuery: null,
})

function MiniChart() {
  const bars = [44, 64, 50, 78, 58, 86, 72]

  return (
    <div className="flex h-20 items-end gap-2">
      {bars.map((height, index) => (
        <span
          key={index}
          className="w-full rounded-t-lg bg-blue-100"
          style={{ height: `${height}%` }}
        />
      ))}
    </div>
  )
}

function StockPreviewCard({ ticker, name, price, change }) {
  const isPositive = change.startsWith('+')

  return (
    <div className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-[0_18px_45px_rgba(96,126,203,0.12)]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-900">{ticker}</p>
          <p className="mt-1 text-xs text-slate-500">{name}</p>
        </div>
        <span
          className={`rounded-full px-2.5 py-1 text-xs font-medium ${
            isPositive ? 'bg-emerald-50 text-emerald-600' : 'bg-rose-50 text-rose-500'
          }`}
        >
          {change}
        </span>
      </div>
      <p className="mt-4 text-xl font-semibold text-slate-900">{price}</p>
    </div>
  )
}

function LandingScreen({ onAbout, onStartChatting }) {
  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,_#f8fafc_0%,_#f3f6fb_56%,_#eef2f8_100%)] text-slate-900">
      <nav className="mx-auto flex w-full max-w-7xl items-center justify-between px-5 py-5 sm:px-8 lg:px-10">
        <button
          type="button"
          onClick={onStartChatting}
          className="flex items-center gap-3 text-left"
          aria-label="NSE AI Advisor home"
        >
          <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-blue-600 text-sm font-bold text-white shadow-[0_12px_28px_rgba(37,99,235,0.28)]">
            NSE
          </span>
          <span>
            <span className="block text-base font-semibold text-slate-900">
              NSE AI Advisor
            </span>
            <span className="block text-xs text-slate-500">
              Nairobi Securities Exchange
            </span>
          </span>
        </button>

        <div className="hidden items-center gap-8 text-sm font-medium text-slate-500 md:flex">
          <button type="button" className="text-blue-600">
            Home
          </button>
          <button type="button" onClick={onStartChatting} className="hover:text-blue-600">
            AI Chatbot
          </button>
          <button type="button" onClick={onAbout} className="hover:text-blue-600">
            About
          </button>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            className="hidden rounded-full px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-white sm:inline-flex"
          >
            Login
          </button>
          <button
            type="button"
            className="rounded-full bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-[0_12px_26px_rgba(37,99,235,0.22)] transition hover:bg-blue-700"
          >
            Register
          </button>
        </div>
      </nav>

      <main className="mx-auto grid min-h-[calc(100vh-86px)] w-full max-w-7xl items-center gap-10 px-5 pb-10 pt-4 sm:px-8 lg:grid-cols-[1fr_0.92fr] lg:px-10">
        <section className="max-w-2xl">
          <div className="mb-6 inline-flex rounded-full border border-blue-100 bg-white px-4 py-2 text-sm font-medium text-blue-700 shadow-sm">
            Smart NSE research, made simple
          </div>
          <h1 className="max-w-3xl text-4xl font-semibold leading-tight tracking-normal text-slate-950 sm:text-5xl lg:text-6xl">
            Your AI-Powered NSE Investment Assistant
          </h1>
          <p className="mt-5 max-w-xl text-lg leading-8 text-slate-600">
            A premium fintech AI assistant for the Nairobi Securities Exchange.
          </p>

          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <button
              type="button"
              onClick={onStartChatting}
              className="rounded-full bg-blue-600 px-7 py-4 text-sm font-semibold text-white shadow-[0_18px_32px_rgba(37,99,235,0.24)] transition hover:bg-blue-700"
            >
              Start Chatting
            </button>
          </div>

          <div className="mt-12 grid max-w-2xl gap-4 sm:grid-cols-3">
            <StockPreviewCard
              ticker="SCOM"
              name="Safaricom PLC"
              price="KES 22.80"
              change="+0.44%"
            />
            <StockPreviewCard
              ticker="EQTY"
              name="Equity Group"
              price="KES 47.50"
              change="+0.21%"
            />
            <StockPreviewCard
              ticker="KCB"
              name="KCB Group"
              price="KES 38.75"
              change="-0.39%"
            />
          </div>
        </section>

        <section className="relative mx-auto w-full max-w-xl">
          <div className="absolute -left-4 top-10 hidden rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-[0_18px_45px_rgba(96,126,203,0.13)] sm:block">
            <p className="text-xs text-slate-500">AI insight</p>
            <p className="mt-1 text-sm font-semibold text-slate-900">
              Dividend leaders ready
            </p>
          </div>

          <div className="rounded-[2rem] border border-white bg-white/90 p-5 shadow-[0_28px_80px_rgba(96,126,203,0.18)]">
            <div className="rounded-[1.5rem] border border-slate-100 bg-slate-50 p-5">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold text-slate-900">Market Preview</p>
                  <p className="mt-1 text-xs text-slate-500">NSE sample analytics</p>
                </div>
                <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-600">
                  Calm signal
                </span>
              </div>

              <div className="mt-6 rounded-2xl bg-white p-4 shadow-sm">
                <div className="mb-4 flex items-center justify-between">
                  <div>
                    <p className="text-xs text-slate-500">Safaricom PLC</p>
                    <p className="mt-1 text-2xl font-semibold text-slate-900">SCOM</p>
                  </div>
                  <p className="text-right text-sm font-semibold text-blue-600">
                    KES 22.80
                    <span className="block text-xs font-medium text-emerald-600">
                      +0.44%
                    </span>
                  </p>
                </div>
                <MiniChart />
              </div>

              <div className="mt-4 grid grid-cols-2 gap-4">
                <div className="rounded-2xl bg-white p-4 shadow-sm">
                  <p className="text-xs text-slate-500">Dividend yield</p>
                  <p className="mt-2 text-xl font-semibold text-slate-900">6.7%</p>
                </div>
                <div className="rounded-2xl bg-white p-4 shadow-sm">
                  <p className="text-xs text-slate-500">P/E ratio</p>
                  <p className="mt-2 text-xl font-semibold text-slate-900">19.2</p>
                </div>
              </div>

              <div className="mt-4 rounded-2xl bg-blue-600 p-4 text-white shadow-[0_16px_32px_rgba(37,99,235,0.22)]">
                <p className="text-xs text-blue-100">Sample chatbot prompt</p>
                <p className="mt-2 text-sm font-medium">
                  “Compare Safaricom and Equity for a beginner investor.”
                </p>
              </div>
            </div>
          </div>

          <div className="absolute -bottom-4 right-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-[0_18px_45px_rgba(96,126,203,0.13)]">
            <p className="text-xs text-slate-500">Market chart</p>
            <div className="mt-2 flex h-10 items-end gap-1.5">
              {[18, 28, 22, 35, 30, 42].map((height, index) => (
                <span
                  key={index}
                  className="w-3 rounded-t bg-blue-200"
                  style={{ height }}
                />
              ))}
            </div>
          </div>
        </section>
      </main>
    </div>
  )
}

function App() {
  const [query, setQuery] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [conversations, setConversations] = useState([createConversation()])
  const [activeConversationId, setActiveConversationId] = useState(null)
  const [voiceSupported, setVoiceSupported] = useState(false)
  const [showLanding, setShowLanding] = useState(true)
  const [activeScreen, setActiveScreen] = useState('chat')
  const { speak, voiceEnabled, setVoiceEnabled } = useNissy()
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
    console.log("Sending query:", messageText)
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
    let requestTimeout

    try {
      // Keep the full response below one minute while allowing larger comparisons.
      const controller = new AbortController()
      requestTimeout = setTimeout(() => {
        console.warn("55-second fetch timeout triggered")
        controller.abort()
      }, 55000)

      console.log("Fetch fired")
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: trimmedQuery }),
        signal: controller.signal,
      })

      if (!response.ok) {
        throw new Error('Unable to reach the NSE AI Advisor backend.')
      }

      const contentType = response.headers.get('content-type') || ''
      if (contentType.includes('application/json')) {
        const payload = await response.json()
        console.log("JSON response received:", payload)

        const messageData = buildAssistantData(payload)
        console.log("Built assistant data:", messageData)

        appendMessage({
          id: crypto.randomUUID(),
          role: 'assistant',
          type: payload.type ?? 'ai_response',
          data: messageData,
        })

        // Read response aloud if Nissy voice is enabled
        const messageText =
          payload.message || payload.data?.message || ''
        if (messageText) {
          speak(messageText)
        }
        clearTimeout(requestTimeout)
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

          if (item.event === 'done') {
            // Read the complete response aloud if Nissy voice is enabled
            updateMessage(assistantMessageId, (message) => {
              const finalText = message.data.message || ''
              if (finalText) {
                speak(finalText)
              }
              return message
            })
          }
        }
      }
      clearTimeout(requestTimeout)
    } catch (error) {
      console.error("Request error:", error.name, error.message)

      appendMessage({
        id: crypto.randomUUID(),
        role: 'assistant',
        type: 'ai_response',
        data: {
          message: getRequestErrorMessage(error),
          disclaimer: DISCLAIMER,
        },
      })
    } finally {
      clearTimeout(requestTimeout)
      setIsLoading(false)
    }
  }

  sendMessageRef.current = sendMessage

  const handleSubmit = async (event) => {
    event.preventDefault()
    await sendMessage(query)
  }

  const handleStartChatting = () => {
    setShowLanding(false)
    setActiveScreen('chat')
  }

  const handleShowAbout = () => {
    setShowLanding(false)
    setActiveScreen('about')
  }

  const handleBackHome = () => {
    setShowLanding(true)
    setActiveScreen('chat')
  }

  const suggestedQuestions = [
    'Safaricom share price',
    'Top gainers today',
    'Compare KCB and Equity',
    'What are dividends?',
  ]

  if (showLanding) {
    return (
      <LandingScreen
        onAbout={handleShowAbout}
        onStartChatting={handleStartChatting}
      />
    )
  }

  if (activeScreen === 'about') {
    return (
      <AboutPage
        onBackHome={handleBackHome}
        onStartChatting={handleStartChatting}
      />
    )
  }

  return (
    <div className="min-h-screen overflow-x-hidden bg-[linear-gradient(180deg,_#f8fafc_0%,_#f3f6fb_56%,_#eef2f8_100%)] text-slate-900">
      <div className="mx-auto flex min-h-screen max-w-[1640px] min-w-0 flex-col">
        <header className="border-b border-slate-200/80 bg-white/80 px-4 py-3 backdrop-blur sm:px-6 lg:px-8">
          <div className="flex items-center justify-between gap-4">
            <button
              type="button"
              onClick={() => setShowLanding(true)}
              className="flex shrink-0 items-center gap-3 text-left"
              aria-label="Back to NSE AI Advisor welcome screen"
            >
              <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-blue-600 text-xs font-bold text-white shadow-[0_10px_22px_rgba(37,99,235,0.2)]">
                NSE
              </span>
              <span>
                <span className="block text-sm font-semibold text-slate-900">
                  NSE AI Advisor
                </span>
                <span className="hidden text-xs text-slate-400 sm:block">
                  AI market assistant
                </span>
              </span>
            </button>

            <div className="hidden min-w-0 w-[42%] max-w-[34rem] flex-none items-center rounded-full border border-slate-200 bg-slate-50 px-4 py-2.5 text-slate-400 shadow-inner md:flex">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                className="h-4 w-4 shrink-0"
                aria-hidden="true"
              >
                <circle cx="11" cy="11" r="7" />
                <path d="m20 20-3.5-3.5" />
              </svg>
              <input
                type="search"
                placeholder="Search NSE topics or conversations"
                className="min-w-0 flex-1 bg-transparent px-3 text-sm text-slate-700 outline-none placeholder:text-slate-400"
              />
            </div>
            <button
              type="button"
              onClick={() => setVoiceEnabled(!voiceEnabled)}
              className={`hidden items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition sm:inline-flex ${
                voiceEnabled
                  ? 'bg-blue-50 text-blue-700 hover:bg-blue-100'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
              title="Toggle voice output"
            >
              <span className="text-lg">🎤</span>
              <span>Nissy {voiceEnabled ? 'On' : 'Off'}</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveScreen('admin')}
              className="hidden h-10 w-10 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-500 transition hover:text-blue-600 sm:inline-flex"
              aria-label="Admin dashboard"
              title="Admin dashboard"
            >
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                className="h-5 w-5"
                aria-hidden="true"
              >
                <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" />
                <path d="M13.73 21a2 2 0 0 1-3.46 0" />
              </svg>
            </button>
            <button
              type="button"
              onClick={() => setActiveScreen('about')}
              className="hidden rounded-full px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-100 hover:text-blue-700 md:inline-flex"
            >
              About
            </button>
            <button
              type="button"
              onClick={() => setActiveScreen('profile')}
              className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-600 text-sm font-semibold text-white shadow-[0_10px_22px_rgba(37,99,235,0.18)]"
              aria-label="User profile"
              title="User profile"
            >
              U
            </button>
          </div>
        </header>
        {activeScreen === 'profile' ? (
          <UserProfileScreen onBackToChat={() => setActiveScreen('chat')} />
        ) : activeScreen === 'admin' ? (
          <AdminDashboardScreen />
        ) : (
        <div className="flex min-w-0 flex-1 flex-col">
          <section className="flex min-w-0 w-full flex-1 flex-col">
            <div className="flex-1 overflow-y-auto px-4 py-5 sm:px-6 lg:px-8">
              <div className="mx-auto flex min-h-[62vh] w-full max-w-6xl min-w-0 flex-col gap-4">
                  {activeConversation?.messages.map((message) => (
                    <div key={message.id} className="group flex gap-2">
                      <ChatBubble role={message.role}>
                        {message.role === 'user' ? (
                          <p className="whitespace-pre-wrap break-words text-sm leading-7 [overflow-wrap:anywhere] sm:text-[15px]">
                            {message.data.message}
                          </p>
                        ) : (
                          <div>
                            {/* Stock Info Response */}
                            {message.type === 'stock_info' && message.data.ticker && (
                              <StockDetailsScreen data={message.data} onAsk={sendMessage} />
                            )}

                            {/* Comparison Response */}
                            {message.type === 'comparison' && message.data.stocks && (
                              <div className="space-y-4">
                                <ComparisonTable data={message.data} />
                                {message.data.stocks.length > 0 && (
                                  <PriceChart
                                    stock={message.data.stocks[0]}
                                    title={`${message.data.stocks.map(s => s.ticker).join(' vs ')} - Available Price History`}
                                  />
                                )}
                              </div>
                            )}

                            {/* Stock List Response */}
                            {message.type === 'stock_list' && (
                              <StockListTable data={message.data} />
                            )}

                            {/* Market Overview Response */}
                            {message.type === 'market_overview' && (
                              <MarketOverview data={message.data} />
                            )}

                            {/* Portfolio Response */}
                            {message.type === 'portfolio' && (
                              <PortfolioTable data={message.data} />
                            )}

                            {/* Text Response (Analysis, Error, etc) */}
                            {message.type !== 'stock_info' &&
                             message.type !== 'comparison' &&
                             message.type !== 'stock_list' &&
                             message.type !== 'market_overview' &&
                             message.type !== 'portfolio' &&
                             message.data.message && (
                              <div className="space-y-3">
                                <p className="whitespace-pre-wrap break-words text-sm leading-7 text-slate-700 [overflow-wrap:anywhere] sm:text-[15px]">
                                  {message.data.message}
                                </p>
                                {message.data.stocks && (
                                  <StockListTable data={message.data} />
                                )}
                                {message.data.disclaimer && (
                                  <p className="text-xs text-slate-400">
                                    Disclaimer: {message.data.disclaimer}
                                  </p>
                                )}
                              </div>
                            )}

                            {/* Debug: Show if nothing rendered */}
                            {!message.data.message &&
                             !message.data.ticker &&
                             !message.data.stocks &&
                             message.type !== 'stock_list' &&
                             message.type !== 'market_overview' &&
                             message.type !== 'portfolio' && (
                              <div className="p-3 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-700">
                                <p className="font-mono font-bold">⚠️ Debug Info</p>
                                <p>Type: <code>{message.type}</code></p>
                                <p>Data Keys: <code>{Object.keys(message.data || {}).join(', ')}</code></p>
                                <p>Full Data: <code className="text-[10px]">{JSON.stringify(message.data).substring(0, 200)}...</code></p>
                              </div>
                            )}
                          </div>
                        )}
                      </ChatBubble>

                      {message.role === 'assistant' && message.data.message && (
                        <button
                          type="button"
                          onClick={() => speak(message.data.message)}
                          className="invisible mb-4 mt-1 inline-flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-slate-200 text-slate-600 transition hover:bg-slate-300 group-hover:visible"
                          title="Read message aloud"
                          aria-label="Read message aloud"
                        >
                          <span className="text-lg">🔊</span>
                        </button>
                      )}
                    </div>
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

            <div className="border-t border-slate-200/70 bg-white/70 px-4 py-3 backdrop-blur sm:px-6 lg:px-8">
              <div className="mx-auto w-full max-w-5xl">
                <div className="mb-3 flex flex-wrap gap-2">
                  {suggestedQuestions.map((question) => (
                    <button
                      key={question}
                      type="button"
                      onClick={() => sendMessage(question)}
                      disabled={isLoading}
                      className="rounded-full border border-slate-200 bg-white px-3.5 py-2 text-xs font-medium text-slate-600 shadow-sm transition hover:border-blue-200 hover:text-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {question}
                    </button>
                  ))}
                </div>
                <InputBar
                  isListening={isListening}
                  isLoading={isLoading}
                  onMicClick={handleMicClick}
                  onQueryChange={setQuery}
                  onSubmit={handleSubmit}
                  placeholder="Ask about Safaricom, dividends, market trends..."
                  query={query}
                  voiceSupported={voiceSupported}
                />
              </div>
            </div>
          </section>
        </div>
        )}
      </div>
    </div>
  )
}

export default App
