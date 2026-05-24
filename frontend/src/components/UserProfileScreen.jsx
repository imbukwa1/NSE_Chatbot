import { useCallback, useEffect, useMemo, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import { profileApi } from '../services/api.js'

function formatCurrency(value) {
  return typeof value === 'number' ? `KES ${value.toFixed(2)}` : 'N/A'
}

function formatChange(value) {
  if (typeof value !== 'number') return 'N/A'
  return `${value > 0 ? '+' : ''}${value.toFixed(2)}%`
}

function formatDate(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function formatShortDate(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  })
}

function normalizeStockItem(item) {
  const stock = item?.stock || item || {}
  return {
    ticker: stock.ticker || item?.ticker || '',
    name: stock.name || stock.company_name || item?.name || item?.ticker || 'NSE counter',
    price: stock.price,
    change: stock.change_pct,
    createdAt: item?.created_at,
  }
}

function EmptyState({ children }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-8 text-center text-sm text-slate-500">
      {children}
    </div>
  )
}

function LoadingCard() {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="h-4 w-24 animate-pulse rounded bg-slate-100" />
      <div className="mt-3 h-3 w-16 animate-pulse rounded bg-slate-100" />
      <div className="mt-6 h-5 w-28 animate-pulse rounded bg-slate-100" />
    </div>
  )
}

function FavoriteStockCard({ stock, onRemove }) {
  const isPositive = Number(stock.change || 0) >= 0

  return (
    <div className="group rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-900">{stock.name}</p>
          <p className="mt-1 text-xs text-slate-400">{stock.ticker}</p>
        </div>
        <button
          type="button"
          onClick={() => onRemove(stock.ticker)}
          className="rounded-full px-2 py-1 text-xs font-semibold text-slate-400 opacity-100 transition hover:bg-rose-50 hover:text-rose-600 sm:opacity-0 sm:group-hover:opacity-100"
          aria-label={`Remove ${stock.ticker} from favorites`}
          title="Remove favorite"
        >
          Remove
        </button>
      </div>
      <div className="mt-4 flex items-end justify-between gap-3">
        <p className="text-lg font-semibold text-blue-600">{formatCurrency(stock.price)}</p>
        <span
          className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
            isPositive ? 'bg-emerald-50 text-emerald-600' : 'bg-rose-50 text-rose-500'
          }`}
        >
          {formatChange(stock.change)}
        </span>
      </div>
    </div>
  )
}

function HistoryItem({ preview, time, title }) {
  return (
    <div className="w-full rounded-2xl border border-slate-200 bg-white p-4 text-left shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="line-clamp-1 text-sm font-semibold text-slate-900">
            {title}
          </p>
          <p className="mt-1 line-clamp-2 text-xs leading-5 text-slate-500">
            {preview || 'No message preview available.'}
          </p>
        </div>
        <span className="shrink-0 text-xs text-slate-400">{time}</span>
      </div>
    </div>
  )
}

function WatchlistRow({ stock, onRemove }) {
  const isPositive = Number(stock.change || 0) >= 0

  return (
    <div className="group flex items-center justify-between gap-3 rounded-2xl bg-slate-50 px-4 py-3">
      <div className="min-w-0">
        <p className="truncate text-sm font-semibold text-slate-900">{stock.name}</p>
        <p className="mt-1 text-xs text-slate-400">{stock.ticker}</p>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <span
          className={`rounded-full px-3 py-1 text-xs font-semibold ${
            isPositive ? 'bg-emerald-50 text-emerald-600' : 'bg-rose-50 text-rose-500'
          }`}
        >
          {formatChange(stock.change)}
        </span>
        <button
          type="button"
          onClick={() => onRemove(stock.ticker)}
          className="rounded-full px-2 py-1 text-xs font-semibold text-slate-400 opacity-100 transition hover:bg-rose-50 hover:text-rose-600 sm:opacity-0 sm:group-hover:opacity-100"
          aria-label={`Remove ${stock.ticker} from watchlist`}
          title="Remove from watchlist"
        >
          Remove
        </button>
      </div>
    </div>
  )
}

function InsightBox({ favorites, recentSearches, watchlist }) {
  const hasEnoughActivity =
    favorites.length + watchlist.length + recentSearches.length >= 3

  if (!hasEnoughActivity) {
    return (
      <div className="rounded-[1.75rem] border border-blue-100 bg-blue-50/70 p-5 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">
          AI personal insights
        </p>
        <p className="mt-3 text-sm leading-7 text-slate-600">
          Use NSE AI Advisor more to unlock personalized investment insights.
        </p>
      </div>
    )
  }

  const tickers = [...new Set([...favorites, ...watchlist].map((item) => item.ticker))]
    .filter(Boolean)
    .slice(0, 4)

  return (
    <div className="rounded-[1.75rem] border border-blue-100 bg-blue-50/70 p-5 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">
        AI personal insights
      </p>
      <p className="mt-3 text-sm leading-7 text-slate-700">
        Your saved activity currently focuses on {tickers.join(', ') || 'NSE counters'}.
        Keep asking questions and saving counters to improve this profile.
      </p>
      <p className="mt-4 text-xs text-slate-400">This is not financial advice.</p>
    </div>
  )
}

function UserProfileScreen({ onBackToChat, onRequireLogin }) {
  const { logout, user } = useAuth()
  const [profile, setProfile] = useState(null)
  const [favorites, setFavorites] = useState([])
  const [watchlist, setWatchlist] = useState([])
  const [sessions, setSessions] = useState([])
  const [recentSearches, setRecentSearches] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [feedback, setFeedback] = useState('')

  const favoriteStocks = useMemo(
    () => favorites.map(normalizeStockItem),
    [favorites],
  )
  const watchlistStocks = useMemo(
    () => watchlist.map(normalizeStockItem),
    [watchlist],
  )

  const loadProfileData = useCallback(async () => {
    setIsLoading(true)
    setError('')

    try {
      // Profile sections must be empty for new users unless the backend has real activity.
      const [profilePayload, favoritesPayload, watchlistPayload, sessionsPayload, searchesPayload] =
        await Promise.all([
          profileApi.getProfile(),
          profileApi.getFavorites(),
          profileApi.getWatchlist(),
          profileApi.getChatSessions(),
          profileApi.getRecentSearches(),
        ])

      setProfile(profilePayload.data?.profile || null)
      setFavorites(favoritesPayload.data?.favorites || profilePayload.data?.favorites || [])
      setWatchlist(watchlistPayload.data?.watchlist || profilePayload.data?.watchlist || [])
      setSessions(sessionsPayload.data?.sessions || [])
      setRecentSearches(searchesPayload.data?.recent_searches || profilePayload.data?.recent_searches || [])
    } catch (err) {
      if (err.status === 401 || err.status === 403) {
        await logout()
        onRequireLogin?.()
        return
      }
      setError(err.message || 'Unable to load your profile right now.')
    } finally {
      setIsLoading(false)
    }
  }, [logout, onRequireLogin])

  useEffect(() => {
    loadProfileData()
  }, [loadProfileData])

  const handleRemoveFavorite = async (ticker) => {
    try {
      await profileApi.removeFavorite(ticker)
      setFavorites((items) => items.filter((item) => item.ticker !== ticker))
      setFeedback(`${ticker} removed from favorites.`)
    } catch (err) {
      setFeedback(err.message || `Could not remove ${ticker}.`)
    }
  }

  const handleRemoveWatchlist = async (ticker) => {
    try {
      await profileApi.removeWatchlist(ticker)
      setWatchlist((items) => items.filter((item) => item.ticker !== ticker))
      setFeedback(`${ticker} removed from watchlist.`)
    } catch (err) {
      setFeedback(err.message || `Could not remove ${ticker}.`)
    }
  }

  const handleLogout = async () => {
    await logout()
    onBackToChat()
  }

  const displayName = profile?.display_name || profile?.full_name || user?.fullName || 'NSE Investor'
  const email = profile?.email || user?.email || ''
  const initial = displayName.trim().charAt(0).toUpperCase() || 'U'

  return (
    <main className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl space-y-6">
        <section className="rounded-[1.75rem] border border-slate-200 bg-white p-5 shadow-[0_18px_50px_rgba(96,126,203,0.12)] sm:p-6">
          <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-4">
              <div className="flex h-20 w-20 items-center justify-center rounded-3xl bg-blue-600 text-2xl font-semibold text-white shadow-[0_14px_28px_rgba(37,99,235,0.2)]">
                {initial}
              </div>
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-2xl font-semibold text-slate-950">
                    {displayName}
                  </h2>
                  <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
                    {profile?.investor_level || 'Investor Explorer'}
                  </span>
                </div>
                <p className="mt-1 text-sm text-slate-500">{email}</p>
                <p className="mt-2 text-xs text-slate-400">
                  {profile?.member_since ? `Joined ${formatDate(profile.member_since)}` : 'Profile loading'}
                </p>
              </div>
            </div>

            <div className="flex gap-3">
              <button
                type="button"
                onClick={onBackToChat}
                className="rounded-full bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-[0_12px_24px_rgba(37,99,235,0.18)] transition hover:bg-blue-700"
              >
                Back to Chat
              </button>
              <button
                type="button"
                onClick={handleLogout}
                className="rounded-full border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-600 transition hover:border-blue-200 hover:text-blue-700"
              >
                Logout
              </button>
            </div>
          </div>
        </section>

        {feedback && (
          <p className="rounded-2xl bg-blue-50 px-4 py-3 text-sm font-medium text-blue-700">
            {feedback}
          </p>
        )}

        {error && (
          <p className="rounded-2xl bg-rose-50 px-4 py-3 text-sm font-medium text-rose-600">
            {error}
          </p>
        )}

        <section className="grid gap-6 xl:grid-cols-[1fr_22rem]">
          <div className="space-y-6">
            <section className="rounded-[1.75rem] border border-slate-200 bg-white/95 p-5 shadow-sm">
              <div className="mb-4 flex items-center justify-between">
                <h3 className="text-lg font-semibold text-slate-950">
                  Favorite stocks
                </h3>
                <span className="text-xs font-medium text-slate-400">Saved NSE counters</span>
              </div>
              {isLoading ? (
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  {[1, 2, 3, 4].map((item) => <LoadingCard key={item} />)}
                </div>
              ) : favoriteStocks.length ? (
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  {favoriteStocks.map((stock) => (
                    <FavoriteStockCard
                      key={stock.ticker}
                      stock={stock}
                      onRemove={handleRemoveFavorite}
                    />
                  ))}
                </div>
              ) : (
                <EmptyState>No favorite stocks yet.</EmptyState>
              )}
            </section>

            <section className="grid gap-6 lg:grid-cols-2">
              <div className="rounded-[1.75rem] border border-slate-200 bg-white/95 p-5 shadow-sm">
                <h3 className="text-lg font-semibold text-slate-950">
                  Recent searches
                </h3>
                <div className="mt-4">
                  {isLoading ? (
                    <div className="flex flex-wrap gap-2">
                      {[1, 2, 3].map((item) => (
                        <span key={item} className="h-10 w-36 animate-pulse rounded-full bg-slate-100" />
                      ))}
                    </div>
                  ) : recentSearches.length ? (
                    <div className="flex flex-wrap gap-2">
                      {recentSearches.map((search) => (
                        <span
                          key={search.id || search.search_query}
                          className="rounded-full border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-medium text-slate-600"
                        >
                          {search.search_query}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <EmptyState>Your recent searches will appear here.</EmptyState>
                  )}
                </div>
              </div>

              <InsightBox
                favorites={favoriteStocks}
                recentSearches={recentSearches}
                watchlist={watchlistStocks}
              />
            </section>

            <section className="rounded-[1.75rem] border border-slate-200 bg-white/95 p-5 shadow-sm">
              <h3 className="text-lg font-semibold text-slate-950">
                Chat history
              </h3>
              <div className="mt-4 space-y-3">
                {isLoading ? (
                  [1, 2, 3].map((item) => (
                    <div key={item} className="h-24 animate-pulse rounded-2xl bg-slate-100" />
                  ))
                ) : sessions.length ? (
                  sessions.map((session) => (
                    <HistoryItem
                      key={session.id}
                      title={session.title || 'NSE conversation'}
                      preview={session.first_message || session.preview || 'Open this conversation from chat history.'}
                      time={formatShortDate(session.updated_at || session.created_at)}
                    />
                  ))
                ) : (
                  <EmptyState>No conversations yet.</EmptyState>
                )}
              </div>
            </section>
          </div>

          <aside className="space-y-6">
            <section className="rounded-[1.75rem] border border-slate-200 bg-white/95 p-5 shadow-sm">
              <h3 className="text-lg font-semibold text-slate-950">
                Watchlist
              </h3>
              <div className="mt-4 space-y-3">
                {isLoading ? (
                  [1, 2, 3].map((item) => (
                    <div key={item} className="h-20 animate-pulse rounded-2xl bg-slate-100" />
                  ))
                ) : watchlistStocks.length ? (
                  watchlistStocks.map((stock) => (
                    <WatchlistRow
                      key={stock.ticker}
                      stock={stock}
                      onRemove={handleRemoveWatchlist}
                    />
                  ))
                ) : (
                  <EmptyState>Your watchlist is empty.</EmptyState>
                )}
              </div>
            </section>

            <section className="rounded-[1.75rem] border border-slate-200 bg-white/95 p-5 shadow-sm">
              <h3 className="text-lg font-semibold text-slate-950">
                Saved searches
              </h3>
              <div className="mt-4">
                <EmptyState>No saved searches yet.</EmptyState>
              </div>
            </section>
          </aside>
        </section>
      </div>
    </main>
  )
}

export default UserProfileScreen
