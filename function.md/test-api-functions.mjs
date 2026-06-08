import assert from 'node:assert/strict'

function extractToken(payload) {
  return payload?.access_token || payload?.token || payload?.data?.access_token || payload?.data?.token || null
}

function extractUser(payload) {
  return payload?.user || payload?.data?.user || payload?.data || null
}

function extractMessage(payload, fallback) {
  return payload?.message || payload?.detail || payload?.error || fallback
}

function createTokenStore() {
  const store = new Map()
  return {
    getStoredToken() {
      return store.get('nse_advisor_token') || null
    },
    storeToken(token) {
      if (token) store.set('nse_advisor_token', token)
    },
    clearStoredToken() {
      store.delete('nse_advisor_token')
    },
  }
}

async function apiRequest(path, options, dependencies) {
  const { baseUrl, fetchImpl, getStoredToken } = dependencies
  const token = getStoredToken()
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  }

  if (token) headers.Authorization = `Bearer ${token}`

  let response
  try {
    response = await fetchImpl(`${baseUrl}${path}`, { ...options, headers })
  } catch {
    throw new Error('Backend unavailable. Please check that the NSE API server is running.')
  }

  const contentType = response.headers.get('content-type') || ''
  const payload = contentType.includes('application/json') ? await response.json() : null

  if (!response.ok) {
    const error = new Error(extractMessage(payload, 'Request failed. Please try again.'))
    error.status = response.status
    throw error
  }

  return payload
}

function jsonResponse(payload, ok = true, status = 200) {
  return {
    ok,
    status,
    headers: {
      get(name) {
        return name === 'content-type' ? 'application/json' : ''
      },
    },
    async json() {
      return payload
    },
  }
}

async function run() {
  assert.equal(extractToken({ access_token: 'direct-token' }), 'direct-token')
  assert.equal(extractToken({ data: { access_token: 'nested-token' } }), 'nested-token')
  assert.equal(extractUser({ data: { user: { email: 'mock@example.com' } } }).email, 'mock@example.com')
  assert.equal(extractMessage({ detail: 'Invalid login' }, 'Fallback'), 'Invalid login')

  const tokenStore = createTokenStore()
  tokenStore.storeToken('mock-token')
  assert.equal(tokenStore.getStoredToken(), 'mock-token')
  tokenStore.clearStoredToken()
  assert.equal(tokenStore.getStoredToken(), null)

  tokenStore.storeToken('mock-token')
  let receivedHeaders = null
  const payload = await apiRequest('/profile/me', {}, {
    baseUrl: 'http://mock-api',
    getStoredToken: tokenStore.getStoredToken,
    fetchImpl: async (_url, options) => {
      receivedHeaders = options.headers
      return jsonResponse({ success: true, data: { user: { role: 'admin' } } })
    },
  })
  assert.equal(payload.data.user.role, 'admin')
  assert.equal(receivedHeaders.Authorization, 'Bearer mock-token')

  await assert.rejects(
    () => apiRequest('/auth/login', {}, {
      baseUrl: 'http://mock-api',
      getStoredToken: () => null,
      fetchImpl: async () => jsonResponse({ detail: 'Invalid email or password.' }, false, 401),
    }),
    /Invalid email or password/,
  )
}

try {
  await run()
  console.log('PASS api-functions')
} catch (error) {
  console.error('FAIL api-functions')
  console.error(error)
  process.exit(1)
}
