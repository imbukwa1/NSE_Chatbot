function formatCurrency(value) {
  return typeof value === 'number' ? `KES ${value.toFixed(2)}` : 'N/A'
}

function formatRatio(value) {
  return typeof value === 'number' ? value.toFixed(2) : 'N/A'
}

function formatPercent(value) {
  return typeof value === 'number' ? `${(value * 100).toFixed(2)}%` : 'N/A'
}

function splitAnalysisText(text = '') {
  return text
    .split(/(?<=\.)\s+/)
    .map((item) => item.trim())
    .filter(Boolean)
}

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
  const analysisRows = splitAnalysisText(data.analysis || data.message)

  // Add stock values to each row
  rows.forEach((row) => {
    stocks.forEach((stock, idx) => {
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

      <div className="overflow-hidden rounded-2xl border border-emerald-100 bg-white shadow-sm">
        <div className="border-b border-emerald-100 bg-emerald-50/80 px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-700">
            Balanced Analysis
          </p>
        </div>
        <table className="min-w-full divide-y divide-slate-100 text-left">
          <tbody className="divide-y divide-slate-100">
            {analysisRows.length ? (
              analysisRows.map((item, index) => {
                const [label, ...rest] = item.split(':')
                const hasLabel = rest.length > 0 && label.length <= 28
                return (
                  <tr key={`${item}-${index}`}>
                    <td className="w-40 bg-slate-50 px-4 py-3 text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
                      {hasLabel ? label : `Point ${index + 1}`}
                    </td>
                    <td className="px-4 py-3 text-sm leading-6 text-slate-700">
                      {hasLabel ? rest.join(':').trim() : item}
                    </td>
                  </tr>
                )
              })
            ) : (
              <tr>
                <td className="px-4 py-3 text-sm text-slate-500">
                  No additional analysis is available.
                </td>
              </tr>
            )}
          </tbody>
        </table>
        <p className="border-t border-slate-100 px-4 py-3 text-xs text-slate-400">
          Disclaimer: {data.disclaimer}
        </p>
      </div>
    </div>
  )
}

export default ComparisonTable
