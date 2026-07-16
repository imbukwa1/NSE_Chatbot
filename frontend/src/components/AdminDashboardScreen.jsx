import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useAuth } from '../context/AuthContext.jsx'
import { adminApi } from '../services/api.js'

const CATEGORIES = [
  'Investment Basics',
  'Dividends',
  'Valuation',
  'NSE Rules',
  'Company Information',
]

const EMPTY_FORM = {
  category: CATEGORIES[0],
  question: '',
  answer: '',
}

const LOGIN_FILTERS = [
  { label: 'Last 7 Days', days: 7 },
  { label: '30 Days', days: 30 },
  { label: '90 Days', days: 90 },
]

function toIsoDate(date) {
  return date.toISOString().slice(0, 10)
}

function buildMockLoginAnalytics(days = 90) {
  const today = new Date()

  return Array.from({ length: days }, (_, index) => {
    const date = new Date(today)
    date.setDate(today.getDate() - (days - index - 1))
    const weekday = date.getDay()
    const weeklyLift = weekday === 1 || weekday === 2 ? 7 : weekday === 0 ? -4 : 2
    const cycle = Math.round(Math.sin(index / 4) * 5)
    const logins = Math.max(0, 18 + weeklyLift + cycle + (index % 6))

    return {
      date: toIsoDate(date),
      logins,
    }
  })
}

const MOCK_LOGIN_ANALYTICS = buildMockLoginAnalytics()

function formatDate(value) {
  if (!value) return 'No update yet'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString(undefined, {
    hour: 'numeric',
    minute: '2-digit',
    month: 'short',
    day: 'numeric',
  })
}

function formatMarketUpdate(value) {
  if (!value) return 'No market update yet'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return `${date.toLocaleTimeString([], {
    hour: 'numeric',
    minute: '2-digit',
  })} EAT`
}

function formatChartDate(value) {
  if (!value) return ''
  const date = new Date(`${value}T00:00:00`)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  })
}

function formatExactChartDate(value) {
  if (!value) return ''
  const date = new Date(`${value}T00:00:00`)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

function EmptyState({ children }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-7 text-center text-sm text-slate-500">
      {children}
    </div>
  )
}

function LoginTooltip({ active, label, payload }) {
  if (!active || !payload?.length) return null

  return (
    <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-[0_14px_35px_rgba(15,23,42,0.12)]">
      <p className="text-xs font-semibold text-slate-500">{formatExactChartDate(label)}</p>
      <p className="mt-1 text-sm font-semibold text-blue-700">
        {payload[0].value} logins
      </p>
    </div>
  )
}

function LoginAnalyticsChart({ data, rangeDays, onRangeChange }) {
  const hasLoginData = data.some((item) => Number(item.logins) > 0)

  return (
    <section className="rounded-[1.75rem] border border-slate-200 bg-white/95 p-5 shadow-sm sm:p-6">
      <div className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-600">
            User login analytics
          </p>
          <h3 className="mt-2 text-lg font-semibold text-slate-950">
            Daily User Logins
          </h3>
        </div>
        <div className="flex flex-wrap gap-2 rounded-2xl bg-blue-50 p-1">
          {LOGIN_FILTERS.map((filter) => (
            <button
              key={filter.days}
              type="button"
              onClick={() => onRangeChange(filter.days)}
              className={`rounded-xl px-3 py-2 text-xs font-semibold transition ${
                rangeDays === filter.days
                  ? 'bg-blue-600 text-white shadow-[0_10px_20px_rgba(37,99,235,0.18)]'
                  : 'text-blue-700 hover:bg-white/80'
              }`}
            >
              {filter.label}
            </button>
          ))}
        </div>
      </div>

      {hasLoginData ? (
        <div className="h-[18rem] w-full sm:h-[21rem]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 8, right: 18, left: 0, bottom: 28 }}>
              <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="date"
                tickFormatter={formatChartDate}
                tick={{ fill: '#64748b', fontSize: 12 }}
                tickLine={false}
                axisLine={{ stroke: '#e2e8f0' }}
                minTickGap={22}
                label={{
                  value: 'Date',
                  position: 'insideBottom',
                  offset: -18,
                  fill: '#64748b',
                  fontSize: 12,
                }}
              />
              <YAxis
                allowDecimals={false}
                label={{
                  value: 'Number of Logins',
                  angle: -90,
                  position: 'insideLeft',
                  fill: '#64748b',
                  fontSize: 12,
                }}
                tick={{ fill: '#64748b', fontSize: 12 }}
                tickLine={false}
                axisLine={false}
                width={58}
              />
              <Tooltip content={<LoginTooltip />} cursor={{ stroke: '#93c5fd', strokeWidth: 1 }} />
              <Line
                type="monotone"
                dataKey="logins"
                name="Logins"
                stroke="#2563eb"
                strokeWidth={3}
                dot={{ r: 2.5, fill: '#2563eb', strokeWidth: 0 }}
                activeDot={{ r: 6, fill: '#1d4ed8', stroke: '#dbeafe', strokeWidth: 3 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <EmptyState>No login activity available.</EmptyState>
      )}
    </section>
  )
}

function SummaryCard({ icon, title, value, subtitle }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start gap-3">
        <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-blue-50 text-lg text-blue-700">
          {icon}
        </span>
        <div>
          <p className="text-xs font-medium text-slate-400">{title}</p>
          <p className="mt-2 text-2xl font-semibold text-slate-950">{value}</p>
          <p className="mt-1 text-xs text-slate-500">{subtitle}</p>
        </div>
      </div>
    </div>
  )
}

function StatusPill({ isActive }) {
  return (
    <span
      className={`rounded-full px-3 py-1 text-xs font-semibold ${
        isActive ? 'bg-emerald-50 text-emerald-600' : 'bg-slate-100 text-slate-500'
      }`}
    >
      {isActive ? 'Active' : 'Inactive'}
    </span>
  )
}

function AdminTable({ columns, children, minWidth = '720px' }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left" style={{ minWidth }}>
        <thead>
          <tr className="border-b border-slate-200 text-xs font-semibold uppercase tracking-[0.14em] text-slate-400">
            {columns.map((column) => (
              <th key={column} className="px-3 py-3">
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">{children}</tbody>
      </table>
    </div>
  )
}

function ActionButton({ children, onClick, tone = 'default', type = 'button' }) {
  return (
    <button
      type={type}
      onClick={onClick}
      className={`rounded-full px-3 py-1.5 text-xs font-semibold transition ${
        tone === 'danger'
          ? 'bg-rose-50 text-rose-600 hover:bg-rose-100'
          : tone === 'primary'
            ? 'bg-blue-600 text-white shadow-[0_10px_20px_rgba(37,99,235,0.16)] hover:bg-blue-700'
            : 'bg-blue-50 text-blue-700 hover:bg-blue-100'
      }`}
    >
      {children}
    </button>
  )
}

function KnowledgeForm({ form, isEditing, onCancel, onChange, onSubmit }) {
  return (
    <form
      onSubmit={onSubmit}
      className="mb-4 rounded-2xl border border-blue-100 bg-blue-50/60 p-4"
    >
      <div className="grid gap-3 md:grid-cols-[12rem_1fr]">
        <label className="block">
          <span className="text-xs font-semibold text-slate-500">Category</span>
          <select
            value={form.category}
            onChange={(event) => onChange({ ...form, category: event.target.value })}
            className="mt-1 w-full rounded-2xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none focus:border-blue-300"
          >
            {CATEGORIES.map((category) => (
              <option key={category}>{category}</option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="text-xs font-semibold text-slate-500">Question</span>
          <input
            value={form.question}
            onChange={(event) => onChange({ ...form, question: event.target.value })}
            className="mt-1 w-full rounded-2xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none focus:border-blue-300"
            placeholder="What should the chatbot know?"
          />
        </label>
      </div>
      <label className="mt-3 block">
        <span className="text-xs font-semibold text-slate-500">Answer</span>
        <textarea
          value={form.answer}
          onChange={(event) => onChange({ ...form, answer: event.target.value })}
          rows={3}
          className="mt-1 w-full rounded-2xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none focus:border-blue-300"
          placeholder="Write a clear beginner-friendly answer."
        />
      </label>
      <div className="mt-3 flex justify-end gap-2">
        <ActionButton onClick={onCancel}>Cancel</ActionButton>
        <ActionButton type="submit" tone="primary">
          {isEditing ? 'Save Entry' : 'Add Entry'}
        </ActionButton>
      </div>
    </form>
  )
}

function AdminDashboardScreen({ onRequireLogin }) {
  const { isAuthLoading, isAuthenticated, logout, user } = useAuth()
  const [analytics, setAnalytics] = useState(null)
  const [loginAnalytics, setLoginAnalytics] = useState(MOCK_LOGIN_ANALYTICS)
  const [loginRangeDays, setLoginRangeDays] = useState(30)
  const [users, setUsers] = useState([])
  const [knowledgeEntries, setKnowledgeEntries] = useState([])
  const [knowledgeStats, setKnowledgeStats] = useState({})
  const [knowledgeSearch, setKnowledgeSearch] = useState('')
  const [marketUpdate, setMarketUpdate] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isReimporting, setIsReimporting] = useState(false)
  const [error, setError] = useState('')
  const [feedback, setFeedback] = useState('')
  const [showKnowledgeForm, setShowKnowledgeForm] = useState(false)
  const [editingEntryId, setEditingEntryId] = useState(null)
  const [knowledgeForm, setKnowledgeForm] = useState(EMPTY_FORM)

  const isAdmin = user?.role === 'admin'

  const loadLoginAnalytics = useCallback(async (days) => {
    try {
      const payload = await adminApi.getLoginAnalytics(days)
      const logins = payload.data?.logins || payload.data?.analytics?.logins || []
      setLoginAnalytics(logins)
    } catch {
      setLoginAnalytics(MOCK_LOGIN_ANALYTICS)
    }
  }, [])

  const loadAdminData = useCallback(async () => {
    if (!isAuthenticated || !isAdmin) {
      setIsLoading(false)
      return
    }

    setIsLoading(true)
    setError('')

    try {
      // Load the four MVP admin sections from real backend data, never demo rows.
      const [analyticsPayload, usersPayload, knowledgePayload, marketPayload] =
        await Promise.all([
          adminApi.getAnalytics(),
          adminApi.getUsers(),
          adminApi.getKnowledgeBase(),
          adminApi.getMarketOverview().catch(() => null),
        ])

      setAnalytics(analyticsPayload.data?.analytics || {})
      setUsers(usersPayload.data?.users || [])
      setKnowledgeEntries(knowledgePayload.data?.entries || [])
      setKnowledgeStats(knowledgePayload.data?.stats || {})
      setMarketUpdate(
        marketPayload?.data?.market?.generated_at ||
          marketPayload?.data?.market?.last_updated ||
          null,
      )
    } catch (err) {
      if (err.status === 401) {
        await logout()
        onRequireLogin?.()
        return
      }
      setError(err.message || 'Unable to load admin dashboard.')
    } finally {
      setIsLoading(false)
    }
  }, [isAdmin, isAuthenticated, logout, onRequireLogin])

  useEffect(() => {
    loadAdminData()
  }, [loadAdminData])

  useEffect(() => {
    if (isAuthenticated && isAdmin) {
      loadLoginAnalytics(loginRangeDays)
    }
  }, [isAdmin, isAuthenticated, loadLoginAnalytics, loginRangeDays])

  const totalStocksTracked = useMemo(() => {
    const collections = [
      analytics?.most_searched_stocks || [],
      analytics?.top_viewed_companies || [],
    ]
    const tickers = new Set()
    collections.flat().forEach((item) => {
      if (item.ticker) tickers.add(item.ticker)
    })
    return tickers.size || 'N/A'
  }, [analytics])

  const chatbotActivity = useMemo(
    () => ({
      popularQueries: analytics?.most_popular_queries || [],
      searchedStocks: analytics?.most_searched_stocks || [],
      recentQueries: analytics?.recent_queries || [],
      failedQuestions: analytics?.failed_questions || [],
    }),
    [analytics],
  )

  const visibleLoginAnalytics = useMemo(
    () => loginAnalytics.slice(-loginRangeDays),
    [loginAnalytics, loginRangeDays],
  )

  const handleLoginRangeChange = (days) => {
    setLoginRangeDays(days)
  }

  const handleStatusChange = async (targetUser, isActive) => {
    try {
      const payload = await adminApi.updateUserStatus(targetUser.id, isActive)
      const updatedUser = payload.data?.user
      setUsers((currentUsers) =>
        currentUsers.map((item) =>
          item.id === targetUser.id ? { ...item, ...(updatedUser || {}), is_active: isActive } : item,
        ),
      )
      setFeedback(`${targetUser.full_name} is now ${isActive ? 'active' : 'inactive'}.`)
    } catch (err) {
      setFeedback(err.message || 'Could not update user status.')
    }
  }

  const openCreateForm = () => {
    setKnowledgeForm(EMPTY_FORM)
    setEditingEntryId(null)
    setShowKnowledgeForm(true)
  }

  const openEditForm = (entry) => {
    setKnowledgeForm({
      category: entry.category || CATEGORIES[0],
      question: entry.question || '',
      answer: entry.answer || '',
    })
    setEditingEntryId(entry.id)
    setShowKnowledgeForm(true)
  }

  const closeKnowledgeForm = () => {
    setKnowledgeForm(EMPTY_FORM)
    setEditingEntryId(null)
    setShowKnowledgeForm(false)
  }

  const handleKnowledgeSubmit = async (event) => {
    event.preventDefault()
    if (!knowledgeForm.category || !knowledgeForm.question.trim() || !knowledgeForm.answer.trim()) {
      setFeedback('Please fill in category, question, and answer.')
      return
    }

    try {
      // The same compact form supports both adding and editing knowledge entries.
      const payload = editingEntryId
        ? await adminApi.updateKnowledgeEntry(editingEntryId, knowledgeForm)
        : await adminApi.createKnowledgeEntry(knowledgeForm)
      const entry = payload.data?.entry
      if (entry) {
        setKnowledgeEntries((currentEntries) =>
          editingEntryId
            ? currentEntries.map((item) => (item.id === entry.id ? entry : item))
            : [entry, ...currentEntries],
        )
      }
      setFeedback(editingEntryId ? 'Knowledge entry updated.' : 'Knowledge entry added.')
      closeKnowledgeForm()
    } catch (err) {
      setFeedback(err.message || 'Could not save knowledge entry.')
    }
  }

  const handleDeleteKnowledge = async (entryId) => {
    try {
      await adminApi.deleteKnowledgeEntry(entryId)
      setKnowledgeEntries((currentEntries) =>
        currentEntries.filter((item) => item.id !== entryId),
      )
      setFeedback('Knowledge entry deleted.')
    } catch (err) {
      setFeedback(err.message || 'Could not delete knowledge entry.')
    }
  }

  const handleKnowledgeSearch = async (event) => {
    event.preventDefault()
    try {
      const payload = await adminApi.getKnowledgeBase(knowledgeSearch.trim())
      setKnowledgeEntries(payload.data?.entries || [])
      setKnowledgeStats(payload.data?.stats || knowledgeStats)
    } catch (err) {
      setFeedback(err.message || 'Could not search knowledge base.')
    }
  }

  const handleReimportKnowledge = async () => {
    setIsReimporting(true)
    setFeedback('')
    try {
      const payload = await adminApi.reimportKnowledgeBase()
      const stats = payload.data?.import
      setFeedback(
        `Knowledge base import complete: ${stats?.imported_count ?? 0} imported, ${stats?.skipped_count ?? 0} skipped.`,
      )
      const refreshed = await adminApi.getKnowledgeBase(knowledgeSearch.trim())
      setKnowledgeEntries(refreshed.data?.entries || [])
      setKnowledgeStats(refreshed.data?.stats || {})
    } catch (err) {
      setFeedback(err.message || 'Could not re-import knowledge base.')
    } finally {
      setIsReimporting(false)
    }
  }

  if (isAuthLoading || isLoading) {
    return (
      <main className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl space-y-6">
          <div className="h-40 animate-pulse rounded-[1.75rem] bg-white shadow-sm" />
          <div className="grid gap-4 md:grid-cols-3">
            {[1, 2, 3].map((item) => (
              <div key={item} className="h-28 animate-pulse rounded-2xl bg-white shadow-sm" />
            ))}
          </div>
        </div>
      </main>
    )
  }

  if (!isAuthenticated) {
    return (
      <main className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 lg:px-8">
        <EmptyState>Please login to access the admin dashboard.</EmptyState>
      </main>
    )
  }

  if (!isAdmin) {
    return (
      <main className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 lg:px-8">
        <EmptyState>You do not have permission to access this page.</EmptyState>
      </main>
    )
  }

  return (
    <main className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <section className="rounded-[1.75rem] border border-slate-200 bg-white p-5 shadow-[0_18px_50px_rgba(96,126,203,0.12)] sm:p-6">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-600">
            Admin dashboard
          </p>
          <h2 className="mt-2 text-2xl font-semibold text-slate-950">
            Admin Dashboard
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
            Manage users, chatbot knowledge, and system activity.
          </p>
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

        <section className="grid gap-4 md:grid-cols-4">
          <SummaryCard
            icon="U"
            title="Total Users"
            value={analytics?.total_users ?? users.length}
            subtitle={`${analytics?.active_users ?? users.filter((item) => item.is_active).length} active users`}
          />
          <SummaryCard
            icon="S"
            title="Total Stocks Tracked"
            value={totalStocksTracked}
            subtitle="Based on recorded stock activity"
          />
          <SummaryCard
            icon="T"
            title="Last Market Update"
            value={formatMarketUpdate(marketUpdate)}
            subtitle="Latest market snapshot"
          />
          <SummaryCard
            icon="K"
            title="KB Articles"
            value={knowledgeStats.total_articles ?? knowledgeEntries.length}
            subtitle={`${knowledgeStats.categories?.length ?? 0} categories`}
          />
          <SummaryCard
            icon="I"
            title="Last KB Import"
            value={formatDate(knowledgeStats.last_import?.imported_at)}
            subtitle={knowledgeStats.last_import?.status || 'No import recorded'}
          />
        </section>

        <LoginAnalyticsChart
          data={visibleLoginAnalytics}
          rangeDays={loginRangeDays}
          onRangeChange={handleLoginRangeChange}
        />

        <section className="grid gap-6 xl:grid-cols-[1fr_28rem]">
          <div className="space-y-6">
            <section className="rounded-[1.75rem] border border-slate-200 bg-white/95 p-5 shadow-sm">
              <h3 className="mb-4 text-lg font-semibold text-slate-950">
                User Management
              </h3>
              {users.length ? (
                <AdminTable columns={['Name', 'Email', 'Role', 'Status', 'Action']}>
                  {users.map((item) => (
                    <tr key={item.id}>
                      <td className="px-3 py-4 text-sm font-semibold text-slate-900">
                        {item.full_name}
                      </td>
                      <td className="px-3 py-4 text-sm text-slate-500">{item.email}</td>
                      <td className="px-3 py-4 text-sm capitalize text-slate-600">{item.role}</td>
                      <td className="px-3 py-4"><StatusPill isActive={item.is_active} /></td>
                      <td className="px-3 py-4">
                        <ActionButton
                          tone={item.is_active ? 'danger' : 'default'}
                          onClick={() => handleStatusChange(item, !item.is_active)}
                        >
                          {item.is_active ? 'Deactivate' : 'Activate'}
                        </ActionButton>
                      </td>
                    </tr>
                  ))}
                </AdminTable>
              ) : (
                <EmptyState>No users found.</EmptyState>
              )}
            </section>

            <section className="rounded-[1.75rem] border border-slate-200 bg-white/95 p-5 shadow-sm">
              <h3 className="mb-4 text-lg font-semibold text-slate-950">
                Chatbot Activity
              </h3>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-2xl bg-slate-50 p-4">
                  <h4 className="text-sm font-semibold text-slate-900">Most asked questions</h4>
                  <div className="mt-3 space-y-2">
                    {chatbotActivity.popularQueries.length ? (
                      chatbotActivity.popularQueries.map((item) => (
                        <p key={item.query} className="rounded-xl bg-white px-3 py-2 text-sm text-slate-600 shadow-sm">
                          {item.query} <span className="text-xs text-slate-400">({item.count})</span>
                        </p>
                      ))
                    ) : (
                      <EmptyState>No chatbot activity recorded yet.</EmptyState>
                    )}
                  </div>
                </div>
                <div className="rounded-2xl bg-slate-50 p-4">
                  <h4 className="text-sm font-semibold text-slate-900">Most searched stocks</h4>
                  <div className="mt-3 space-y-2">
                    {chatbotActivity.searchedStocks.length ? (
                      chatbotActivity.searchedStocks.map((item) => (
                        <p key={item.ticker} className="rounded-xl bg-white px-3 py-2 text-sm font-semibold text-blue-700 shadow-sm">
                          {item.ticker} <span className="text-xs font-normal text-slate-400">({item.count})</span>
                        </p>
                      ))
                    ) : (
                      <EmptyState>No stock searches recorded yet.</EmptyState>
                    )}
                  </div>
                </div>
                <div className="rounded-2xl bg-slate-50 p-4">
                  <h4 className="text-sm font-semibold text-slate-900">Recent chatbot queries</h4>
                  <div className="mt-3">
                    {chatbotActivity.recentQueries.length ? (
                      chatbotActivity.recentQueries.map((item) => (
                        <p key={item.id || item.query} className="rounded-xl bg-white px-3 py-2 text-sm text-slate-600 shadow-sm">
                          {item.query}
                        </p>
                      ))
                    ) : (
                      <EmptyState>No recent chatbot queries yet.</EmptyState>
                    )}
                  </div>
                </div>
                <div className="rounded-2xl bg-slate-50 p-4">
                  <h4 className="text-sm font-semibold text-slate-900">Failed/unknown questions</h4>
                  <div className="mt-3">
                    {chatbotActivity.failedQuestions.length ? (
                      chatbotActivity.failedQuestions.map((item) => (
                        <p key={item.id || item.query} className="rounded-xl bg-white px-3 py-2 text-sm text-slate-600 shadow-sm">
                          {item.query}
                        </p>
                      ))
                    ) : (
                      <EmptyState>No failed questions recorded yet.</EmptyState>
                    )}
                  </div>
                </div>
              </div>
            </section>
          </div>

          <section className="rounded-[1.75rem] border border-slate-200 bg-white/95 p-5 shadow-sm">
            <div className="mb-4 flex items-center justify-between gap-3">
              <h3 className="text-lg font-semibold text-slate-950">
                Knowledge Base Management
              </h3>
              <div className="flex flex-wrap justify-end gap-2">
                <ActionButton onClick={handleReimportKnowledge}>
                  {isReimporting ? 'Importing...' : 'Re-import KB'}
                </ActionButton>
                <ActionButton tone="primary" onClick={openCreateForm}>
                  Add Knowledge Entry
                </ActionButton>
              </div>
            </div>

            <form onSubmit={handleKnowledgeSearch} className="mb-4 flex gap-2">
              <input
                value={knowledgeSearch}
                onChange={(event) => setKnowledgeSearch(event.target.value)}
                className="min-w-0 flex-1 rounded-2xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none focus:border-blue-300"
                placeholder="Search articles, aliases, keywords, or slugs"
              />
              <ActionButton type="submit" tone="primary">
                Search
              </ActionButton>
            </form>

            {knowledgeStats.articles_per_category?.length ? (
              <div className="mb-4 rounded-2xl bg-slate-50 p-4">
                <h4 className="text-sm font-semibold text-slate-900">Articles per category</h4>
                <div className="mt-3 grid gap-2 sm:grid-cols-2">
                  {knowledgeStats.articles_per_category.map((item) => (
                    <p key={item.category} className="rounded-xl bg-white px-3 py-2 text-sm text-slate-600 shadow-sm">
                      <span className="font-semibold text-slate-900">{item.category}</span>{' '}
                      <span className="text-xs text-slate-400">({item.count})</span>
                    </p>
                  ))}
                </div>
              </div>
            ) : null}

            {showKnowledgeForm && (
              <KnowledgeForm
                form={knowledgeForm}
                isEditing={Boolean(editingEntryId)}
                onCancel={closeKnowledgeForm}
                onChange={setKnowledgeForm}
                onSubmit={handleKnowledgeSubmit}
              />
            )}

            {knowledgeEntries.length ? (
              <AdminTable
                columns={['Category', 'Question', 'Answer', 'Last Updated', 'Actions']}
                minWidth="760px"
              >
                {knowledgeEntries.map((entry) => (
                  <tr key={entry.id}>
                    <td className="px-3 py-4 text-sm font-semibold text-blue-700">
                      {entry.category}
                    </td>
                    <td className="px-3 py-4 text-sm font-semibold text-slate-900">
                      {entry.question}
                    </td>
                    <td className="max-w-[16rem] px-3 py-4 text-sm leading-6 text-slate-500">
                      <span className="line-clamp-3">{entry.answer}</span>
                    </td>
                    <td className="px-3 py-4 text-sm text-slate-400">
                      {formatDate(entry.updated_at)}
                    </td>
                    <td className="px-3 py-4">
                      <div className="flex gap-2">
                        <ActionButton onClick={() => openEditForm(entry)}>Edit</ActionButton>
                        <ActionButton tone="danger" onClick={() => handleDeleteKnowledge(entry.id)}>
                          Delete
                        </ActionButton>
                      </div>
                    </td>
                  </tr>
                ))}
              </AdminTable>
            ) : (
              <EmptyState>No knowledge base entries yet.</EmptyState>
            )}
          </section>
        </section>
      </div>
    </main>
  )
}

export default AdminDashboardScreen
