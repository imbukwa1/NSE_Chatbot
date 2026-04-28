function formatCurrency(value) {
  return typeof value === 'number' ? `KES ${value.toLocaleString()}` : 'N/A'
}

function PortfolioTable({ data }) {
  const holdings = data.holdings || []
  const summary = data.summary || {}

  if (!holdings.length) {
    return <p className="text-sm text-slate-500">No portfolio holdings found.</p>
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
            Portfolio Value
          </p>
          <p className="mt-2 text-lg font-semibold text-slate-950">
            {formatCurrency(summary.total_value)}
          </p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
            Est. Dividends
          </p>
          <p className="mt-2 text-lg font-semibold text-slate-950">
            {formatCurrency(summary.estimated_annual_dividends)}
          </p>
        </div>
      </div>

      {summary.concentration_warning && (
        <p className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          {summary.concentration_warning}
        </p>
      )}

      <div className="overflow-x-auto rounded-lg border border-slate-200 shadow-sm">
        <table className="min-w-[720px] w-full divide-y divide-slate-200 text-left">
          <thead className="bg-slate-950 text-white">
            <tr>
              {['Ticker', 'Company', 'Qty', 'Price', 'Value', 'Gain/Loss', 'Sector'].map((label) => (
                <th
                  key={label}
                  className="px-4 py-3 text-xs font-semibold uppercase tracking-[0.18em]"
                >
                  {label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 bg-white">
            {holdings.map((holding) => (
              <tr key={holding.ticker} className="hover:bg-slate-50">
                <td className="px-4 py-3 text-sm font-semibold text-slate-950">
                  {holding.ticker}
                </td>
                <td className="px-4 py-3 text-sm text-slate-700">
                  {holding.name}
                </td>
                <td className="px-4 py-3 text-sm text-slate-700">
                  {holding.quantity.toLocaleString()}
                </td>
                <td className="px-4 py-3 text-sm text-slate-700">
                  {formatCurrency(holding.price)}
                </td>
                <td className="px-4 py-3 text-sm font-medium text-slate-950">
                  {formatCurrency(holding.current_value)}
                </td>
                <td className="px-4 py-3 text-sm text-slate-700">
                  {formatCurrency(holding.gain_loss)}
                </td>
                <td className="px-4 py-3 text-sm text-slate-700">
                  {holding.sector}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default PortfolioTable
