import assert from 'node:assert/strict'

function formatCurrency(value) {
  return typeof value === 'number' ? `KES ${value.toLocaleString()}` : 'N/A'
}

function getPortfolioViewState(data) {
  const holdings = data.holdings || []
  const summary = data.summary || {}

  if (!holdings.length) {
    return { empty: true, message: 'No portfolio holdings found.' }
  }

  return {
    empty: false,
    totalValue: formatCurrency(summary.total_value),
    estimatedDividends: formatCurrency(summary.estimated_annual_dividends),
    hasConcentrationWarning: Boolean(summary.concentration_warning),
  }
}

function run() {
  assert.equal(formatCurrency(12500), 'KES 12,500')
  assert.equal(formatCurrency(undefined), 'N/A')

  assert.deepEqual(getPortfolioViewState({ holdings: [] }), {
    empty: true,
    message: 'No portfolio holdings found.',
  })

  const state = getPortfolioViewState({
    holdings: [{ ticker: 'SCOM', quantity: 100 }],
    summary: {
      total_value: 2280,
      estimated_annual_dividends: 150,
      concentration_warning: 'High telecom concentration.',
    },
  })

  assert.equal(state.empty, false)
  assert.equal(state.totalValue, 'KES 2,280')
  assert.equal(state.estimatedDividends, 'KES 150')
  assert.equal(state.hasConcentrationWarning, true)
}

try {
  run()
  console.log('PASS portfolio-functions')
} catch (error) {
  console.error('FAIL portfolio-functions')
  console.error(error)
  process.exit(1)
}
