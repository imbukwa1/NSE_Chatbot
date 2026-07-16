export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8001'

const TOKEN_KEY = 'nse_advisor_token'

export function getStoredToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function storeToken(token) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token)
  }
}

export function clearStoredToken() {
  localStorage.removeItem(TOKEN_KEY)
}

function extractMessage(payload, fallback) {
  return (
    payload?.message ||
    payload?.detail ||
    payload?.error ||
    fallback
  )
}

export function extractToken(payload) {
  return (
    payload?.access_token ||
    payload?.token ||
    payload?.data?.access_token ||
    payload?.data?.token ||
    null
  )
}

export function extractUser(payload) {
  return (
    payload?.user ||
    payload?.data?.user ||
    payload?.data ||
    null
  )
}

export async function apiRequest(path, options = {}) {
  const token = getStoredToken()
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  }

  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  // Centralize authenticated API calls so future protected endpoints inherit JWT handling.
  let response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers,
    })
  } catch {
    throw new Error('Backend unavailable. Please check that the NSE API server is running.')
  }

  const contentType = response.headers.get('content-type') || ''
  const payload = contentType.includes('application/json')
    ? await response.json()
    : null

  if (!response.ok) {
    const error = new Error(extractMessage(payload, 'Request failed. Please try again.'))
    error.status = response.status
    throw error
  }

  return payload
}

export const authApi = {
  async login({ email, password }) {
    return apiRequest('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
  },

  async register({ fullName, email, password }) {
    return apiRequest('/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        full_name: fullName,
        email,
        password,
      }),
    })
  },

  async me() {
    return apiRequest('/auth/me')
  },

  async logout() {
    return apiRequest('/auth/logout', {
      method: 'POST',
    })
  },
}

export const profileApi = {
  async getProfile() {
    return apiRequest('/profile/me')
  },

  async getFavorites() {
    return apiRequest('/users/me/favorites')
  },

  async addFavorite(ticker) {
    return apiRequest('/users/me/favorites', {
      method: 'POST',
      body: JSON.stringify({ ticker }),
    })
  },

  async removeFavorite(ticker) {
    return apiRequest(`/users/me/favorites/${encodeURIComponent(ticker)}`, {
      method: 'DELETE',
    })
  },

  async getWatchlist() {
    return apiRequest('/users/me/watchlist')
  },

  async addWatchlist(ticker) {
    return apiRequest('/users/me/watchlist', {
      method: 'POST',
      body: JSON.stringify({ ticker }),
    })
  },

  async removeWatchlist(ticker) {
    return apiRequest(`/users/me/watchlist/${encodeURIComponent(ticker)}`, {
      method: 'DELETE',
    })
  },

  async getChatSessions() {
    return apiRequest('/chat/sessions')
  },

  async getRecentSearches() {
    return apiRequest('/profile/recent-searches')
  },

  async saveRecentSearch(searchQuery) {
    return apiRequest('/profile/recent-searches', {
      method: 'POST',
      body: JSON.stringify({ search_query: searchQuery }),
    })
  },
}

export const adminApi = {
  async getAnalytics() {
    return apiRequest('/admin/analytics')
  },

  async getLoginAnalytics(days = 30) {
    return apiRequest(`/admin/analytics/logins?days=${encodeURIComponent(days)}`)
  },

  async getUsers() {
    return apiRequest('/admin/users')
  },

  async updateUserStatus(userId, isActive) {
    return apiRequest(`/admin/users/${userId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ is_active: isActive }),
    })
  },

  async getKnowledgeBase(query = '') {
    const suffix = query ? `?q=${encodeURIComponent(query)}` : ''
    return apiRequest(`/admin/knowledge-base${suffix}`)
  },

  async getKnowledgeBaseStats() {
    return apiRequest('/admin/knowledge-base/stats')
  },

  async reimportKnowledgeBase() {
    return apiRequest('/admin/knowledge-base/reimport', {
      method: 'POST',
    })
  },

  async createKnowledgeEntry(entry) {
    return apiRequest('/admin/knowledge-base', {
      method: 'POST',
      body: JSON.stringify(entry),
    })
  },

  async updateKnowledgeEntry(entryId, entry) {
    return apiRequest(`/admin/knowledge-base/${entryId}`, {
      method: 'PUT',
      body: JSON.stringify(entry),
    })
  },

  async deleteKnowledgeEntry(entryId) {
    return apiRequest(`/admin/knowledge-base/${entryId}`, {
      method: 'DELETE',
    })
  },

  async getMarketOverview() {
    return apiRequest('/market/overview')
  },
}
