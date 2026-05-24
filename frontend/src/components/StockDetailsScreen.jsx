function formatCurrency(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return 'N/A'
  }

  return `KES ${Number(value).toLocaleString(undefined, {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  })}`
}

function formatYield(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return 'N/A'
  }

  return `${(Number(value) * 100).toFixed(2)}%`
}

function formatRatio(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return 'N/A'
  }

  return Number(value).toFixed(2)
}

function formatLastUpdated(value) {
  if (!value) {
    return 'Latest cached snapshot'
  }

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }

  return `${date.toLocaleTimeString([], {
    hour: 'numeric',
    minute: '2-digit',
  })} EAT`
}

function buildInsight(data) {
  const price = formatCurrency(data.price)
  const change = Number(data.change_pct)
  const isPositive = Number.isFinite(change) && change > 0
  const isNegative = Number.isFinite(change) && change < 0

  if (data.ticker === 'KQ') {
    return `${data.name} is currently trading at ${price}. The stock remains relatively high-risk because airline earnings can be affected by fuel costs, debt levels, and travel demand.`
  }

  if (data.ticker === 'SCOM') {
    return `${data.name} continues to show relatively stable market positioning with strong investor attention on the NSE. Watch trading activity and dividend consistency before making any decision.`
  }

  if (isPositive) {
    return `${data.name} is currently trading at ${price}, with a positive daily move. This suggests improved market interest, but investors should still compare valuation, dividends, and recent news.`
  }

  if (isNegative) {
    return `${data.name} is currently trading at ${price}, with a softer daily move. This may reflect cautious sentiment, so it is useful to review company news and sector conditions.`
  }

  return `${data.name} is currently trading at ${price}. The stock can be reviewed using simple signals such as price movement, dividend yield, valuation, and recent market activity.`
}

function MetricCard({ label, value, tone = 'default' }) {
  const toneClass =
    tone === 'positive'
      ? 'text-emerald-600'
      : tone === 'blue'
        ? 'text-blue-600'
        : 'text-slate-950'

  return (
    <div className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
      <p className="text-xs font-medium text-slate-400">{label}</p>
      <p className={`mt-3 text-xl font-semibold ${toneClass}`}>{value}</p>
    </div>
  )
}

function AnalysisPill({ label, value, tone = 'default' }) {
  const toneClass =
    tone === 'positive'
      ? 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-100'
      : tone === 'warning'
        ? 'bg-amber-50 text-amber-700 ring-1 ring-amber-100'
        : 'bg-blue-50 text-blue-700 ring-1 ring-blue-100'
  const dotClass =
    tone === 'positive'
      ? 'bg-emerald-500'
      : tone === 'warning'
        ? 'bg-amber-500'
        : 'bg-blue-500'

  return (
    <div className="flex items-center justify-between gap-3 rounded-2xl bg-slate-50 px-4 py-3">
      <p className="text-xs font-medium text-slate-500">{label}</p>
      <p className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold ${toneClass}`}>
        <span className={`h-1.5 w-1.5 rounded-full ${dotClass}`} />
        {value}
      </p>
    </div>
  )
}

function RelatedCompanyCard({ ticker, name, onAsk }) {
  return (
    <button
      type="button"
      onClick={() => onAsk?.(`Tell me about ${ticker}`)}
      className="rounded-full border border-slate-200 bg-white px-4 py-2 text-left text-xs shadow-sm transition hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700"
    >
      <span className="font-semibold text-slate-900">{ticker}</span>
      <span className="ml-2 text-slate-400">{name}</span>
    </button>
  )
}

function RelatedQuestionButton({ children, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-full border border-slate-200 bg-white/80 px-3 py-1.5 text-left text-xs font-medium text-slate-600 shadow-sm transition hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700"
    >
      {children}
    </button>
  )
}

function StockDetailsScreen({ data, onAddFavorite, onAddWatchlist, onAsk }) {
  const dailyChange = Number(data.change_pct)
  const recommendation = dailyChange < -2 ? 'Neutral' : 'Neutral'
  const sentiment = dailyChange > 0 ? 'Stable positive' : 'Stable'
  const riskLevel = data.ticker === 'KQ' ? 'High' : 'Moderate'
  const insight = buildInsight(data)
  const lastUpdated = formatLastUpdated(data.last_updated || data.updated_at)
  const source = data.source || 'NSE'
  const relatedQuestions = [
    `Is ${data.ticker} a risky stock?`,
    `Does ${data.ticker} pay dividends?`,
    `Compare ${data.ticker} and Safaricom`,
    `What sector does ${data.ticker} belong to?`,
    `How has ${data.ticker} performed recently?`,
  ]

  return (
    <div className="w-full max-w-6xl rounded-[1.75rem] border border-slate-200 bg-white/95 p-5 shadow-[0_18px_50px_rgba(96,126,203,0.12)] sm:p-7">
      <section className="grid gap-8 lg:grid-cols-[minmax(0,1.15fr)_minmax(18rem,0.85fr)]">
        <div className="min-w-0 space-y-6">
          <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-2xl font-semibold text-slate-950">
                  {data.name}
                </h2>
                <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
                  {data.ticker}
                </span>
                <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
                  {data.market_status === 'CLOSED' ? 'Market Closed' : 'Market Open'}
                </span>
              </div>
              <p className="mt-2 max-w-xl text-sm leading-6 text-slate-500">
                Simplified stock view for beginner-friendly NSE research.
              </p>
              <p className="mt-3 text-[11px] text-slate-400">
                Last updated: {lastUpdated} &middot; Source: {source}
              </p>
            </div>
            <div className="rounded-3xl bg-blue-600 px-6 py-5 text-white shadow-[0_14px_28px_rgba(37,99,235,0.2)] sm:min-w-48">
              <p className="text-xs text-blue-100">Current price</p>
              <p className="mt-2 text-3xl font-semibold">
                {formatCurrency(data.price)}
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => onAddFavorite?.(data.ticker)}
                  className="rounded-full bg-white/15 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-white/25"
                >
                  ♡ Favorite
                </button>
                <button
                  type="button"
                  onClick={() => onAddWatchlist?.(data.ticker)}
                  className="rounded-full bg-white/15 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-white/25"
                >
                  + Watchlist
                </button>
              </div>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <MetricCard label="Dividend yield" value={formatYield(data.dividend_yield)} tone="positive" />
            <MetricCard label="P/E ratio" value={formatRatio(data.pe_ratio)} />
          </div>

          <div className="rounded-3xl border border-blue-100 bg-blue-50/70 p-6">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">
              AI insights
            </p>
            <p className="mt-4 text-[15px] leading-8 text-slate-700">
              {insight}
            </p>
            <p className="mt-4 text-[11px] leading-5 text-slate-500">
              Last updated: {lastUpdated} &middot; Source: {source}
              <span className="block text-slate-400">This is not financial advice.</span>
            </p>
          </div>

          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
              Related Questions
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {relatedQuestions.map((question) => (
                <RelatedQuestionButton
                  key={question}
                  onClick={() => onAsk?.(question)}
                >
                  {question}
                </RelatedQuestionButton>
              ))}
            </div>
          </div>

          <div>
            <p className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
              Related companies
            </p>
            <div className="flex flex-wrap gap-2">
              <RelatedCompanyCard ticker="KCB" name="KCB Group PLC" onAsk={onAsk} />
              <RelatedCompanyCard ticker="EQTY" name="Equity Group" onAsk={onAsk} />
              <RelatedCompanyCard ticker="COOP" name="Co-op Bank" onAsk={onAsk} />
            </div>
          </div>
        </div>

        <aside className="min-w-0">
          <div className="rounded-3xl border border-slate-100 bg-slate-50/70 p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
              AI analysis
            </p>
            <div className="mt-4 space-y-3">
              <AnalysisPill
                label="Market sentiment"
                value={sentiment}
                tone={dailyChange > 0 ? 'positive' : 'default'}
              />
              <AnalysisPill
                label="Recommendation"
                value={recommendation}
              />
              <AnalysisPill
                label="Risk level"
                value={riskLevel}
                tone={riskLevel === 'High' ? 'warning' : 'default'}
              />
            </div>
            <div className="mt-5 rounded-2xl bg-white p-4 text-sm text-slate-600 shadow-sm">
              <p className="text-xs font-medium uppercase tracking-[0.14em] text-slate-400">
                Financial highlights
              </p>
              <div className="mt-3 space-y-2">
                <p className="flex justify-between gap-4">
                  <span>P/E ratio</span>
                  <span className="font-semibold text-slate-900">{formatRatio(data.pe_ratio)}</span>
                </p>
                <p className="flex justify-between gap-4">
                  <span>Dividend yield</span>
                  <span className="font-semibold text-emerald-600">{formatYield(data.dividend_yield)}</span>
                </p>
                <p className="pt-2 text-[11px] leading-5 text-slate-400">
                  Updated {lastUpdated}. Source: {source}.
                </p>
              </div>
            </div>
          </div>
        </aside>
      </section>
    </div>
  )
}

export default StockDetailsScreen
