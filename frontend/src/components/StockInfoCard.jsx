function formatPercent(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return 'N/A'
  }

  return `${(value * 100).toFixed(2)}%`
}

function formatCurrency(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return 'N/A'
  }

  return `KES ${Number(value).toFixed(2)}`
}

function formatRatio(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return 'N/A'
  }

  return Number(value).toFixed(2)
}

function StockInfoCard({ data }) {
  return (
    <div className="min-w-[280px] rounded-2xl border border-emerald-100 bg-gradient-to-br from-white to-emerald-50 p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-emerald-700">
            Stock Snapshot
          </p>
          <h3 className="mt-2 text-xl font-semibold text-slate-950">
            {data.name}
          </h3>
          {data.ticker && (
            <p className="mt-1 text-sm text-slate-500">{data.ticker}</p>
          )}
        </div>
        <div className="rounded-2xl bg-slate-950 px-3 py-2 text-right text-white shadow-sm">
          <p className="text-[11px] uppercase tracking-[0.2em] text-emerald-200">
            Price
          </p>
          <p className="text-lg font-semibold">{formatCurrency(data.price)}</p>
        </div>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs uppercase tracking-[0.22em] text-slate-400">
            P/E Ratio
          </p>
          <p className="mt-2 text-lg font-semibold text-slate-900">
            {formatRatio(data.pe_ratio)}
          </p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs uppercase tracking-[0.22em] text-slate-400">
            Dividend Yield
          </p>
          <p className="mt-2 text-lg font-semibold text-slate-900">
            {formatPercent(data.dividend_yield)}
          </p>
        </div>
      </div>

      <p className="mt-4 text-xs text-slate-400">
        Source: {data.source || 'fallback'} | Disclaimer: {data.disclaimer}
      </p>
    </div>
  )
}

export default StockInfoCard
