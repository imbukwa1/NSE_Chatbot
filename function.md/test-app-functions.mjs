import assert from 'node:assert/strict'

const DISCLAIMER = 'This is not financial advice.'
const VALID_SCREENS = new Set(['chat', 'about', 'profile', 'admin'])

function getInitialScreen(storage) {
  const storedScreen = storage.getItem('nse_advisor_active_screen')
  return VALID_SCREENS.has(storedScreen) ? storedScreen : 'chat'
}

function getInitialLandingState(storage, initialScreen) {
  const storedLanding = storage.getItem('nse_advisor_show_landing')
  if (storedLanding === 'true') return true
  if (storedLanding === 'false') return false
  return initialScreen === 'chat'
}

function parseSseBuffer(buffer) {
  const events = []
  const parts = buffer.split('\n\n')
  const remainder = parts.pop() ?? ''

  for (const part of parts) {
    const lines = part.split('\n')
    let event = 'message'
    const dataLines = []

    for (const line of lines) {
      if (line.startsWith('event:')) event = line.slice(6).trim()
      if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
    }

    if (dataLines.length) events.push({ event, data: dataLines.join('\n') })
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

  return error.message || 'There was a problem processing your request. Please try again.'
}

function mockStorage(values = {}) {
  return {
    getItem(key) {
      return values[key] ?? null
    },
  }
}

function run() {
  assert.equal(getInitialScreen(mockStorage({ nse_advisor_active_screen: 'admin' })), 'admin')
  assert.equal(getInitialScreen(mockStorage({ nse_advisor_active_screen: 'bad' })), 'chat')
  assert.equal(getInitialLandingState(mockStorage({ nse_advisor_show_landing: 'false' }), 'admin'), false)
  assert.equal(getInitialLandingState(mockStorage({}), 'chat'), true)

  const parsed = parseSseBuffer('event: metadata\ndata: {"type":"ai_response"}\n\nevent: token\ndata: hello')
  assert.deepEqual(parsed.events, [{ event: 'metadata', data: '{"type":"ai_response"}' }])
  assert.equal(parsed.remainder, 'event: token\ndata: hello')

  const assistantData = buildAssistantData({
    data: { analysis: 'NCBA trend is up.' },
    disclaimer: 'Custom disclaimer.',
  })
  assert.equal(assistantData.message, 'NCBA trend is up.')
  assert.equal(assistantData.disclaimer, 'Custom disclaimer.')

  assert.match(getRequestErrorMessage({ name: 'AbortError', message: 'aborted' }), /timed out/)
  assert.equal(getRequestErrorMessage({ message: 'Backend down' }), 'Backend down')
}

try {
  run()
  console.log('PASS app-functions')
} catch (error) {
  console.error('FAIL app-functions')
  console.error(error)
  process.exit(1)
}
