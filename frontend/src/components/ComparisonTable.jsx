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

function ComparisonTable({ data }) {
  const rows = [
    {
      label: 'Price',
      stock1: formatCurrency(data.stock1.price),
      stock2: formatCurrency(data.stock2.price),
    },
    {
      label: 'P/E Ratio',
      stock1: formatRatio(data.stock1.pe_ratio),
      stock2: formatRatio(data.stock2.pe_ratio),
    },
    {
      label: 'Dividend Yield',
      stock1: formatPercent(data.stock1.dividend_yield),
      stock2: formatPercent(data.stock2.dividend_yield),
    },
  ]

  return (
    <div className="space-y-4">
      <div className="overflow-hidden rounded-2xl border border-slate-200 shadow-sm">
        <table className="min-w-full divide-y divide-slate-200 text-left">
          <thead className="bg-slate-950 text-white">
            <tr>
              <th className="px-4 py-3 text-xs font-semibold uppercase tracking-[0.22em]">
                Metric
              </th>
              <th className="px-4 py-3 text-xs font-semibold uppercase tracking-[0.22em]">
                {data.stock1.name}
              </th>
              <th className="px-4 py-3 text-xs font-semibold uppercase tracking-[0.22em]">
                {data.stock2.name}
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 bg-white">
            {rows.map((row) => (
              <tr key={row.label}>
                <td className="px-4 py-3 text-sm font-medium text-slate-700">
                  {row.label}
                </td>
                <td className="px-4 py-3 text-sm text-slate-900">{row.stock1}</td>
                <td className="px-4 py-3 text-sm text-slate-900">{row.stock2}</td>
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
