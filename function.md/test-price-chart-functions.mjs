import assert from 'node:assert/strict'

function formatCurrency(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return 'N/A'
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
    combinedMap.set(point.date, { date: point.date, [stock1.name]: point.price })
  }

  for (const point of stock2.history || []) {
    const currentPoint = combinedMap.get(point.date) || { date: point.date }
    combinedMap.set(point.date, { ...currentPoint, [stock2.name]: point.price })
  }

  return [...combinedMap.values()].sort((left, right) => left.date.localeCompare(right.date))
}

function formatDateRange(history = []) {
  if (!history.length) return 'Available History'
  const firstDate = history[0]?.date
  const latestDate = history[history.length - 1]?.date
  if (!firstDate || !latestDate || firstDate === latestDate) return firstDate || 'Available History'
  return `${firstDate} to ${latestDate}`
}

function run() {
  assert.equal(formatCurrency(22.8), 'KES 22.80')
  assert.equal(formatCurrency(null), 'N/A')

  const single = buildSingleSeries([{ date: '2026-01-01', price: 10 }], 'Safaricom')
  assert.deepEqual(single, [{ date: '2026-01-01', Safaricom: 10 }])

  const comparison = buildComparisonSeries(
    { name: 'KCB', history: [{ date: '2026-01-02', price: 39 }, { date: '2026-01-01', price: 38 }] },
    { name: 'Equity', history: [{ date: '2026-01-01', price: 47 }] },
  )
  assert.deepEqual(comparison, [
    { date: '2026-01-01', KCB: 38, Equity: 47 },
    { date: '2026-01-02', KCB: 39 },
  ])

  assert.equal(formatDateRange([{ date: '2026-01-01' }, { date: '2026-02-01' }]), '2026-01-01 to 2026-02-01')
  assert.equal(formatDateRange([]), 'Available History')
}

try {
  run()
  console.log('PASS price-chart-functions')
} catch (error) {
  console.error('FAIL price-chart-functions')
  console.error(error)
  process.exit(1)
}
