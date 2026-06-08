import { spawnSync } from 'node:child_process'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = dirname(fileURLToPath(import.meta.url))
const tests = [
  'test-app-functions.mjs',
  'test-api-functions.mjs',
  'test-register-functions.mjs',
  'test-price-chart-functions.mjs',
  'test-portfolio-functions.mjs',
]

let failed = 0

for (const test of tests) {
  const result = spawnSync(process.execPath, [join(root, test)], {
    encoding: 'utf8',
  })

  process.stdout.write(result.stdout)
  process.stderr.write(result.stderr)

  if (result.status !== 0) {
    failed += 1
  }
}

if (failed) {
  console.error(`FAIL ${failed} function test file(s) failed`)
  process.exit(1)
}

console.log('PASS all function tests')
