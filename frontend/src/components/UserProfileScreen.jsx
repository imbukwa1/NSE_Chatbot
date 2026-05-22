function FavoriteStockCard({ change, name, price, ticker }) {
  const isPositive = change.startsWith('+')

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-900">{name}</p>
          <p className="mt-1 text-xs text-slate-400">{ticker}</p>
        </div>
        <span
          className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
            isPositive ? 'bg-emerald-50 text-emerald-600' : 'bg-rose-50 text-rose-500'
          }`}
        >
          {change}
        </span>
      </div>
      <p className="mt-4 text-lg font-semibold text-blue-600">{price}</p>
    </div>
  )
}

function HistoryItem({ preview, time, title }) {
  return (
    <button
      type="button"
      className="w-full rounded-2xl border border-slate-200 bg-white p-4 text-left shadow-sm transition hover:border-blue-200"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="line-clamp-1 text-sm font-semibold text-slate-900">
            {title}
          </p>
          <p className="mt-1 line-clamp-2 text-xs leading-5 text-slate-500">
            {preview}
          </p>
        </div>
        <span className="shrink-0 text-xs text-slate-400">{time}</span>
      </div>
    </button>
  )
}

function WatchlistRow({ change, name, ticker }) {
  const isPositive = change.startsWith('+')

  return (
    <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
      <div>
        <p className="text-sm font-semibold text-slate-900">{name}</p>
        <p className="mt-1 text-xs text-slate-400">{ticker}</p>
      </div>
      <span
        className={`rounded-full px-3 py-1 text-xs font-semibold ${
          isPositive ? 'bg-emerald-50 text-emerald-600' : 'bg-rose-50 text-rose-500'
        }`}
      >
        {change}
      </span>
    </div>
  )
}

function UserProfileScreen({ onBackToChat }) {
  const favoriteStocks = [
    { name: 'Safaricom', ticker: 'SCOM', price: 'KES 22.80', change: '+0.44%' },
    { name: 'KCB Group', ticker: 'KCB', price: 'KES 38.75', change: '-0.39%' },
    { name: 'Equity Bank', ticker: 'EQTY', price: 'KES 47.50', change: '+0.21%' },
    { name: 'Co-operative Bank', ticker: 'COOP', price: 'KES 15.20', change: '+0.18%' },
  ]

  const recentSearches = [
    'Safaricom valuation',
    'Best dividend stocks',
    'Top gainers today',
    'Compare Equity and KCB',
  ]

  return (
    <main className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl space-y-6">
        <section className="rounded-[1.75rem] border border-slate-200 bg-white p-5 shadow-[0_18px_50px_rgba(96,126,203,0.12)] sm:p-6">
          <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-4">
              <div className="flex h-20 w-20 items-center justify-center rounded-3xl bg-blue-600 text-2xl font-semibold text-white shadow-[0_14px_28px_rgba(37,99,235,0.2)]">
                UI
              </div>
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-2xl font-semibold text-slate-950">
                    User Investor
                  </h2>
                  <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
                    Investor Explorer
                  </span>
                </div>
                <p className="mt-1 text-sm text-slate-500">
                  user.investor@example.com
                </p>
                <p className="mt-2 text-xs text-slate-400">
                  Joined May 2026
                </p>
              </div>
            </div>

            <div className="flex gap-3">
              <button
                type="button"
                className="rounded-full bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-[0_12px_24px_rgba(37,99,235,0.18)] transition hover:bg-blue-700"
              >
                Edit Profile
              </button>
              <button
                type="button"
                onClick={onBackToChat}
                className="rounded-full border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-600 transition hover:border-blue-200 hover:text-blue-700"
              >
                Logout
              </button>
            </div>
          </div>
        </section>

        <section className="grid gap-6 xl:grid-cols-[1fr_22rem]">
          <div className="space-y-6">
            <section className="rounded-[1.75rem] border border-slate-200 bg-white/95 p-5 shadow-sm">
              <div className="mb-4 flex items-center justify-between">
                <h3 className="text-lg font-semibold text-slate-950">
                  Favorite stocks
                </h3>
                <span className="text-xs font-medium text-slate-400">Saved NSE counters</span>
              </div>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                {favoriteStocks.map((stock) => (
                  <FavoriteStockCard key={stock.ticker} {...stock} />
                ))}
              </div>
            </section>

            <section className="grid gap-6 lg:grid-cols-2">
              <div className="rounded-[1.75rem] border border-slate-200 bg-white/95 p-5 shadow-sm">
                <h3 className="text-lg font-semibold text-slate-950">
                  Recent searches
                </h3>
                <div className="mt-4 flex flex-wrap gap-2">
                  {recentSearches.map((search) => (
                    <button
                      key={search}
                      type="button"
                      className="rounded-full border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-medium text-slate-600 transition hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700"
                    >
                      {search}
                    </button>
                  ))}
                </div>
              </div>

              <div className="rounded-[1.75rem] border border-blue-100 bg-blue-50/70 p-5 shadow-sm">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">
                  AI personal insights
                </p>
                <p className="mt-3 text-sm leading-7 text-slate-700">
                  You frequently search banking stocks and dividend-related investments.
                  Your watchlist is balanced between telecom and banking counters.
                </p>
                <p className="mt-4 text-xs text-slate-400">
                  This is not financial advice.
                </p>
              </div>
            </section>

            <section className="rounded-[1.75rem] border border-slate-200 bg-white/95 p-5 shadow-sm">
              <h3 className="text-lg font-semibold text-slate-950">
                Chat history
              </h3>
              <div className="mt-4 space-y-3">
                <HistoryItem
                  title="Safaricom analysis"
                  preview="Tell me about Safaricom dividends, price trend, and valuation..."
                  time="Today"
                />
                <HistoryItem
                  title="Dividend investing"
                  preview="Best NSE dividend-paying stocks for beginner investors..."
                  time="Yesterday"
                />
                <HistoryItem
                  title="Banking stocks"
                  preview="Tell me about NSE banking stocks and compare Equity with KCB..."
                  time="May 2026"
                />
              </div>
            </section>
          </div>

          <aside className="space-y-6">
            <section className="rounded-[1.75rem] border border-slate-200 bg-white/95 p-5 shadow-sm">
              <h3 className="text-lg font-semibold text-slate-950">
                Watchlist
              </h3>
              <div className="mt-4 space-y-3">
                <WatchlistRow name="Safaricom" ticker="SCOM" change="+0.44%" />
                <WatchlistRow name="KCB Group" ticker="KCB" change="-0.39%" />
                <WatchlistRow name="Equity Bank" ticker="EQTY" change="+0.21%" />
                <WatchlistRow name="Co-op Bank" ticker="COOP" change="+0.18%" />
              </div>
            </section>

            <section className="rounded-[1.75rem] border border-slate-200 bg-white/95 p-5 shadow-sm">
              <h3 className="text-lg font-semibold text-slate-950">
                Saved searches
              </h3>
              <div className="mt-4 space-y-2">
                {['NSE market overview', 'Top gainers today', 'Dividend leaders'].map(
                  (item) => (
                    <button
                      key={item}
                      type="button"
                      className="w-full rounded-2xl bg-slate-50 px-4 py-3 text-left text-sm text-slate-600 transition hover:bg-blue-50 hover:text-blue-700"
                    >
                      {item}
                    </button>
                  ),
                )}
              </div>
            </section>
          </aside>
        </section>
      </div>
    </main>
  )
}

export default UserProfileScreen
