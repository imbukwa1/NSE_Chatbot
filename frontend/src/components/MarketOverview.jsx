import StockListTable from './StockListTable.jsx'

function formatCurrency(value) {
  return typeof value === 'number' ? `KES ${value.toLocaleString()}` : 'N/A'
}

function formatNumber(value) {
  return typeof value === 'number' ? value.toLocaleString() : 'N/A'
}

function MarketOverview({ data }) {
  const summary = data.summary || {}
  const status = data.status || {}

  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
            Market
          </p>
          <p className="mt-2 text-lg font-semibold text-slate-950">
            {status.label || 'N/A'}
          </p>
          <p className="mt-1 text-xs text-slate-500">{status.hours}</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
            Turnover
          </p>
          <p className="mt-2 text-lg font-semibold text-slate-950">
            {formatCurrency(summary.total_turnover)}
          </p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
            Shares
          </p>
          <p className="mt-2 text-lg font-semibold text-slate-950">
            {formatNumber(summary.shares_traded)}
          </p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
            Counters
          </p>
          <p className="mt-2 text-lg font-semibold text-slate-950">
            {summary.listed_counters || 'N/A'}
          </p>
        </div>
      </div>

      <StockListTable
        data={{ stocks: data.top_gainers || [], title: 'Top Gainers' }}
      />
      <StockListTable
        data={{ stocks: data.top_losers || [], title: 'Top Losers' }}
      />
      <StockListTable
        data={{ stocks: data.most_active || [], title: 'Most Active' }}
      />

      <p className="text-xs leading-5 text-slate-400">
        Index values, foreign investor participation, deals, and bond summaries need
        a connected NSE/CBK feed before they can be shown as live figures.
      </p>
    </div>
  )
}

export default MarketOverview
