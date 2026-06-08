import assert from 'node:assert/strict'

function validateRegisterForm({ fullName, email, password, confirmPassword }) {
  if (!fullName.trim()) return 'Please enter your full name.'
  if (!email.trim()) return 'Please enter your email address.'
  if (password.length < 6) return 'Password must be at least 6 characters.'
  if (password !== confirmPassword) return 'Passwords do not match.'
  return ''
}

async function submitRegistration(form, registerFn) {
  const validationError = validateRegisterForm(form)
  if (validationError) return { ok: false, message: validationError }
  await registerFn({
    fullName: form.fullName.trim(),
    email: form.email.trim(),
    password: form.password,
  })
  return { ok: true, message: 'Account created successfully. Please login.' }
}

async function run() {
  assert.equal(validateRegisterForm({ fullName: '', email: 'a@b.com', password: 'secret1', confirmPassword: 'secret1' }), 'Please enter your full name.')
  assert.equal(validateRegisterForm({ fullName: 'Bakhoya', email: '', password: 'secret1', confirmPassword: 'secret1' }), 'Please enter your email address.')
  assert.equal(validateRegisterForm({ fullName: 'Bakhoya', email: 'a@b.com', password: '123', confirmPassword: '123' }), 'Password must be at least 6 characters.')
  assert.equal(validateRegisterForm({ fullName: 'Bakhoya', email: 'a@b.com', password: 'secret1', confirmPassword: 'secret2' }), 'Passwords do not match.')
  assert.equal(validateRegisterForm({ fullName: 'Bakhoya', email: 'a@b.com', password: 'secret1', confirmPassword: 'secret1' }), '')

  let received = null
  const result = await submitRegistration(
    { fullName: '  Bakhoya  ', email: '  bakhoya@example.test  ', password: 'secret1', confirmPassword: 'secret1' },
    async (payload) => {
      received = payload
    },
  )

  assert.equal(result.ok, true)
  assert.equal(received.fullName, 'Bakhoya')
  assert.equal(received.email, 'bakhoya@example.test')
}

try {
  await run()
  console.log('PASS register-functions')
} catch (error) {
  console.error('FAIL register-functions')
  console.error(error)
  process.exit(1)
}
