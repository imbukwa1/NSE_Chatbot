function ComparisonTable({ data }) {
  // Handle both old (stock1/stock2) and new (stocks) data structures
  const stocks = data.stocks || (data.stock1 && data.stock2 ? [data.stock1, data.stock2] : [])
  
  if (!stocks || stocks.length === 0) {
    return <div className="text-slate-500">No stocks to compare.</div>
  }

  // Build rows with metrics
  const rows = [
    { label: 'Price' },
    { label: 'P/E Ratio' },
    { label: 'Dividend Yield' },
  ]

  // Add stock values to each row
  rows.forEach((row) => {
    stocks.forEach((stock, idx) => {
      const ticker = stock.ticker.toUpperCase()
      if (row.label === 'Price') {
        row[`stock${idx + 1}`] = formatCurrency(stock.price)
      } else if (row.label === 'P/E Ratio') {
        row[`stock${idx + 1}`] = formatRatio(stock.pe_ratio)
      } else if (row.label === 'Dividend Yield') {
        row[`stock${idx + 1}`] = formatPercent(stock.dividend_yield)
      }
    })
  })

  return (
    <div className="space-y-4">
      <div className="overflow-hidden rounded-2xl border border-slate-200 shadow-sm">
        <table className="min-w-full divide-y divide-slate-200 text-left">
          <thead className="bg-slate-950 text-white">
            <tr>
              <th className="px-4 py-3 text-xs font-semibold uppercase tracking-[0.22em]">
                Metric
              </th>
              {stocks.map((stock, idx) => (
                <th
                  key={idx}
                  className="px-4 py-3 text-xs font-semibold uppercase tracking-[0.22em]"
                >
                  {stock.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 bg-white">
            {rows.map((row) => (
              <tr key={row.label}>
                <td className="px-4 py-3 text-sm font-medium text-slate-700">
                  {row.label}
                </td>
                {stocks.map((stock, idx) => {
                  const cellKey = `stock${idx + 1}`
                  return (
                    <td
                      key={idx}
                      className="px-4 py-3 text-sm text-slate-900"
                    >
                      {row[cellKey] || 'N/A'}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="rounded-2xl border border-emerald-100 bg-emerald-50/70 p-5 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-emerald-700">
          Balanced Analysis
        </p>
        <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-700">
          {data.analysis}
        </p>
        <p className="mt-4 text-xs text-slate-400">
          Disclaimer: {data.disclaimer}
        </p>
      </div>
    </div>
  )
}

export default ComparisonTable

