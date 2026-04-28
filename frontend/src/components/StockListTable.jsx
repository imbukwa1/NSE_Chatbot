function formatCurrency(value) {
  return typeof value === 'number' ? `KES ${value.toFixed(2)}` : 'N/A'
}

function formatPercent(value) {
  return typeof value === 'number' ? `${value.toFixed(2)}%` : 'N/A'
}

function formatYield(value) {
  return typeof value === 'number' ? `${(value * 100).toFixed(2)}%` : 'N/A'
}

function formatRatio(value) {
  return typeof value === 'number' ? value.toFixed(2) : 'N/A'
}

function StockListTable({ data }) {
  const stocks = data.stocks || data.top_gainers || []

  if (!stocks.length) {
    return <p className="text-sm text-slate-500">No stock prices available.</p>
  }

  return (
    <div className="space-y-4">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-emerald-700">
          NSE Prices
        </p>
        <h3 className="mt-2 text-lg font-semibold text-slate-950">
          {data.title || 'Supported counters today'}
        </h3>
      </div>

      <div className="overflow-x-auto rounded-lg border border-slate-200 shadow-sm">
        <table className="min-w-[760px] w-full divide-y divide-slate-200 text-left">
          <thead className="bg-slate-950 text-white">
            <tr>
              <th className="px-4 py-3 text-xs font-semibold uppercase tracking-[0.18em]">
                Ticker
              </th>
              <th className="px-4 py-3 text-xs font-semibold uppercase tracking-[0.18em]">
                Company
              </th>
              <th className="px-4 py-3 text-xs font-semibold uppercase tracking-[0.18em]">
                Price
              </th>
              <th className="px-4 py-3 text-xs font-semibold uppercase tracking-[0.18em]">
                Change
              </th>
              <th className="px-4 py-3 text-xs font-semibold uppercase tracking-[0.18em]">
                P/E
              </th>
              <th className="px-4 py-3 text-xs font-semibold uppercase tracking-[0.18em]">
                Yield
              </th>
              <th className="px-4 py-3 text-xs font-semibold uppercase tracking-[0.18em]">
                Source
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 bg-white">
            {stocks.map((stock) => (
              <tr key={stock.ticker} className="hover:bg-slate-50">
                <td className="whitespace-nowrap px-4 py-3 text-sm font-semibold text-slate-950">
                  {stock.ticker}
                </td>
                <td className="px-4 py-3 text-sm text-slate-700">
                  {stock.name}
                </td>
                <td className="whitespace-nowrap px-4 py-3 text-sm font-medium text-slate-950">
                  {formatCurrency(stock.price)}
                </td>
                <td className="whitespace-nowrap px-4 py-3 text-sm text-slate-700">
                  {formatPercent(stock.change_pct)}
                </td>
                <td className="whitespace-nowrap px-4 py-3 text-sm text-slate-700">
                  {formatRatio(stock.pe_ratio)}
                </td>
                <td className="whitespace-nowrap px-4 py-3 text-sm text-slate-700">
                  {formatYield(stock.dividend_yield)}
                </td>
                <td className="whitespace-nowrap px-4 py-3 text-xs uppercase tracking-[0.12em] text-slate-400">
                  {stock.source || 'fallback'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-xs leading-5 text-slate-400">
        Disclaimer: {data.disclaimer}
      </p>
    </div>
  )
}

export default StockListTable
