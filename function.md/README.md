# Function Tests

This folder contains lightweight function-by-function test scripts for NSE AI Advisor frontend helpers.

These tests intentionally use only mocked/local data:

- no backend API calls
- no SQLite writes
- no real user accounts
- no real JWT tokens

Run all tests:

```powershell
node function.md/run-all.mjs
```

Each script prints `PASS` or `FAIL` in the terminal.
