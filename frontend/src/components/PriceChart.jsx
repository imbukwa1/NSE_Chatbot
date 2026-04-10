import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

function formatCurrency(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return 'N/A'
  }

  return `KES ${Number(value).toFixed(2)}`
}

function buildSingleSeries(history = [], label = 'Price') {
  return history.map((point) => ({
    date: point.date,
    [label]: point.price,
  }))
}

function buildComparisonSeries(stock1, stock2) {
  const combinedMap = new Map()

  for (const point of stock1.history || []) {
    combinedMap.set(point.date, {
      date: point.date,
      [stock1.name]: point.price,
    })
  }

  for (const point of stock2.history || []) {
    const currentPoint = combinedMap.get(point.date) || { date: point.date }
    combinedMap.set(point.date, {
      ...currentPoint,
      [stock2.name]: point.price,
    })
  }

  return [...combinedMap.values()].sort((left, right) =>
    left.date.localeCompare(right.date),
  )
}

function PriceChart({ stock, stock1, stock2 }) {
  const isComparison = Boolean(stock1 && stock2)
  const chartData = isComparison
    ? buildComparisonSeries(stock1, stock2)
    : buildSingleSeries(stock?.history, stock?.name || 'Price')

  if (!chartData.length) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-5 py-8 text-sm text-slate-500">
        Historical price data is currently unavailable.
      </div>
    )
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-4">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-emerald-700">
          Price Trend
        </p>
        <h3 className="mt-2 text-lg font-semibold text-slate-950">
          {isComparison
            ? `${stock1.name} vs ${stock2.name} | Last 30 Days`
            : `${stock.name} | Last 30 Days`}
        </h3>
      </div>

      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis
              dataKey="date"
              tick={{ fill: '#64748b', fontSize: 12 }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              tickFormatter={formatCurrency}
              tick={{ fill: '#64748b', fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              width={88}
            />
            <Tooltip
              formatter={(value) => formatCurrency(value)}
              labelClassName="text-slate-600"
              contentStyle={{
                borderRadius: '16px',
                borderColor: '#e2e8f0',
                boxShadow: '0 12px 30px rgba(15, 23, 42, 0.08)',
              }}
            />
            <Legend />
            {isComparison ? (
              <>
                <Line
                  type="monotone"
                  dataKey={stock1.name}
                  stroke="#059669"
                  strokeWidth={2.5}
                  dot={false}
                  activeDot={{ r: 5 }}
                />
                <Line
                  type="monotone"
                  dataKey={stock2.name}
                  stroke="#0f172a"
                  strokeWidth={2.5}
                  dot={false}
                  activeDot={{ r: 5 }}
                />
              </>
            ) : (
              <Line
                type="monotone"
                dataKey={stock.name}
                stroke="#059669"
                strokeWidth={2.5}
                dot={false}
                activeDot={{ r: 5 }}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

export default PriceChart
