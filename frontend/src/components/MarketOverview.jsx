import { useEffect, useState } from 'react'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8001'

function formatCurrency(value) {
  if (typeof value !== 'number') return 'N/A'
  return `KES ${value.toLocaleString(undefined, {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  })}`
}

function formatCompactNumber(value) {
  if (typeof value !== 'number') return 'N/A'
  if (value >= 1000000) return `${(value / 1000000).toFixed(value >= 10000000 ? 1 : 2)}M`
  if (value >= 1000) return `${(value / 1000).toFixed(value >= 100000 ? 0 : 1)}K`
  return value.toLocaleString()
}

function formatPercent(value) {
  if (typeof value !== 'number') return 'N/A'
  return `${value > 0 ? '+' : ''}${value.toFixed(2)}%`
}

function formatLastUpdated(value) {
  if (!value) return 'Latest NSE snapshot'

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value

  const eatTime = new Date(
    date.toLocaleString('en-US', { timeZone: 'Africa/Nairobi' }),
  )
  const hour = eatTime.getHours()
  const snapshotHour = hour >= 15 ? 15 : hour >= 12 ? 12 : 9
  const snapshotDate = new Date(eatTime)
  snapshotDate.setHours(snapshotHour, 0, 0, 0)

  return `${snapshotDate.toLocaleTimeString([], {
    hour: 'numeric',
    minute: '2-digit',
  })} EAT`
}

function MarketRow({ stock, mode = 'change' }) {
  const change = Number(stock.change_pct || 0)
  const isNegative = change < 0

  return (
    <div className="grid min-w-0 grid-cols-[3.2rem_minmax(0,1fr)_auto] items-center gap-2 rounded-2xl bg-slate-50 px-3 py-2 text-xs">
      <span className="whitespace-nowrap font-semibold text-slate-950">{stock.ticker || '-'}</span>
      <span className="min-w-0 truncate text-slate-500">
        {stock.name || stock.company_name || 'NSE company'}
      </span>
      <span className="whitespace-nowrap text-right">
        {mode === 'volume' ? (
          <>
            <span className="block font-semibold text-slate-700">
              {formatCompactNumber(stock.volume)} vol
            </span>
            <span className="block text-[11px] font-semibold text-blue-600">
              {formatCurrency(stock.price)}
            </span>
          </>
        ) : (
          <>
            <span className="block font-semibold text-slate-800">
              {formatCurrency(stock.price)}
            </span>
            <span
              className={`block text-[11px] font-semibold ${
                isNegative ? 'text-rose-500' : 'text-emerald-600'
              }`}
            >
              {formatPercent(change)}
            </span>
          </>
        )}
      </span>
    </div>
  )
}

function MarketColumn({ title, items = [], mode = 'change' }) {
  const visibleItems = items.slice(0, 5)

  return (
    <section className="min-w-0 rounded-3xl border border-slate-100 bg-white p-3.5 shadow-sm">
      <div className="mb-2.5 flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-slate-950">{title}</h3>
        <span className="whitespace-nowrap rounded-full bg-slate-50 px-2.5 py-1 text-[11px] font-medium text-slate-400">
          Top 5
        </span>
      </div>

      <div className="space-y-2">
        {visibleItems.length ? (
          visibleItems.map((stock) => (
            <MarketRow
              key={`${title}-${stock.ticker}`}
              stock={stock}
              mode={mode}
            />
          ))
        ) : (
          <p className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-3 py-4 text-xs text-slate-500">
            Market data is currently unavailable.
          </p>
        )}
      </div>
    </section>
  )
}

function MarketOverview({ data }) {
  const [scraperUpdatedAt, setScraperUpdatedAt] = useState(null)
  const status = data.status || {}
  const topGainers = data.top_gainers || []
  const topLosers = data.top_losers || []
  const mostActive = data.most_active || []
  const movement = topGainers[0]?.change_pct || 0
  const updatedAt =
    scraperUpdatedAt ||
    data.last_updated ||
    topGainers[0]?.last_updated ||
    topLosers[0]?.last_updated ||
    mostActive[0]?.last_updated ||
    data.generated_at

  useEffect(() => {
    let isMounted = true

    async function loadScraperStatus() {
      try {
        const response = await fetch(`${API_BASE_URL}/scraper/status`)
        if (!response.ok) return
        const payload = await response.json()
        if (isMounted) {
          setScraperUpdatedAt(payload.last_database_update || null)
        }
      } catch {
        if (isMounted) {
          setScraperUpdatedAt(null)
        }
      }
    }

    loadScraperStatus()

    return () => {
      isMounted = false
    }
  }, [])

  return (
    <div className="w-full max-w-6xl overflow-hidden rounded-[1.5rem] border border-slate-200 bg-white/95 p-4 shadow-[0_18px_50px_rgba(96,126,203,0.12)] sm:p-5">
      <div className="flex flex-col gap-3 border-b border-slate-100 pb-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-600">
          Market movers
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-blue-50 px-3 py-1.5 text-xs font-semibold text-blue-700">
            {status.label || 'Market status'}
          </span>
          <span
            className={`rounded-full px-3 py-1.5 text-xs font-semibold ${
              movement >= 0
                ? 'bg-emerald-50 text-emerald-700'
                : 'bg-rose-50 text-rose-600'
            }`}
          >
            {formatPercent(movement)}
          </span>
        </div>
      </div>

      <div className="mt-4 grid gap-3 xl:grid-cols-3">
        <MarketColumn title="Top Gainers" items={topGainers} />
        <MarketColumn title="Top Losers" items={topLosers} />
        <MarketColumn title="Most Active" items={mostActive} mode="volume" />
      </div>

      <p className="mt-4 text-[11px] leading-5 text-slate-400">
        Last updated: {formatLastUpdated(updatedAt)} &middot; Source: NSE
      </p>
    </div>
  )
}

export default MarketOverview
