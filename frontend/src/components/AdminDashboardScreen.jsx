import {
  Bar,
  BarChart,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

const conversationData = [
  { day: 'Mon', chats: 42 },
  { day: 'Tue', chats: 58 },
  { day: 'Wed', chats: 50 },
  { day: 'Thu', chats: 74 },
  { day: 'Fri', chats: 68 },
  { day: 'Sat', chats: 36 },
]

const searchedStocks = [
  { ticker: 'SCOM', searches: 82 },
  { ticker: 'KCB', searches: 58 },
  { ticker: 'EQTY', searches: 54 },
  { ticker: 'COOP', searches: 31 },
]

function SummaryCard({ label, value, note }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium text-slate-400">{label}</p>
          <p className="mt-2 text-2xl font-semibold text-slate-950">{value}</p>
        </div>
        <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-blue-50 text-sm font-semibold text-blue-700">
          {label.slice(0, 1)}
        </span>
      </div>
      {note && <p className="mt-3 text-xs text-slate-500">{note}</p>}
    </div>
  )
}

function StatusCard({ label, status = 'Online' }) {
  const isOnline = status === 'Online' || status === 'Connected' || status === 'Healthy'

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-900">{label}</p>
          <p className="mt-1 text-xs text-slate-400">{status}</p>
        </div>
        <span
          className={`h-3 w-3 rounded-full ${
            isOnline ? 'bg-emerald-500' : 'bg-rose-500'
          }`}
        />
      </div>
    </div>
  )
}

function ActionButton({ children, tone = 'default' }) {
  return (
    <button
      type="button"
      className={`rounded-full px-3 py-1.5 text-xs font-semibold transition ${
        tone === 'danger'
          ? 'bg-rose-50 text-rose-600 hover:bg-rose-100'
          : 'bg-blue-50 text-blue-700 hover:bg-blue-100'
      }`}
    >
      {children}
    </button>
  )
}

function AdminTable({ columns, rows }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[720px] text-left">
        <thead>
          <tr className="border-b border-slate-200 text-xs font-semibold uppercase tracking-[0.14em] text-slate-400">
            {columns.map((column) => (
              <th key={column} className="px-3 py-3">
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows}
        </tbody>
      </table>
    </div>
  )
}

function AdminDashboardScreen() {
  return (
    <main className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <section className="rounded-[1.75rem] border border-slate-200 bg-white p-5 shadow-[0_18px_50px_rgba(96,126,203,0.12)] sm:p-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-600">
                Admin dashboard
              </p>
              <h2 className="mt-2 text-2xl font-semibold text-slate-950">
                NSE AI Advisor management
              </h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
                Manage users, NSE company records, chatbot knowledge, and basic activity in one simple workspace.
              </p>
            </div>
            <div className="flex rounded-full border border-slate-200 bg-slate-50 px-4 py-2.5 text-slate-400 shadow-inner">
              <input
                type="search"
                placeholder="Search admin records"
                className="w-60 bg-transparent text-sm text-slate-700 outline-none placeholder:text-slate-400"
              />
            </div>
          </div>

          <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <SummaryCard label="Total Users" value="128" note="12 new this month" />
            <SummaryCard label="Total Conversations" value="2,430" note="Across chatbot sessions" />
            <SummaryCard label="Total NSE Companies" value="64" note="Company records tracked" />
            <SummaryCard label="Active Users Today" value="37" note="Simple daily usage count" />
          </div>
        </section>

        <section className="grid gap-6 xl:grid-cols-[1fr_22rem]">
          <div className="space-y-6">
            <section className="rounded-[1.75rem] border border-slate-200 bg-white/95 p-5 shadow-sm">
              <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <h3 className="text-lg font-semibold text-slate-950">
                  User management
                </h3>
                <div className="flex gap-2">
                  <input
                    type="search"
                    placeholder="Search users"
                    className="rounded-full border border-slate-200 bg-slate-50 px-4 py-2 text-sm outline-none placeholder:text-slate-400"
                  />
                  <select className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm text-slate-600 outline-none">
                    <option>All roles</option>
                    <option>Admin</option>
                    <option>User</option>
                  </select>
                </div>
              </div>

              <AdminTable
                columns={['User name', 'Email', 'Role', 'Status', 'Actions']}
                rows={[
                  ['Grace Wanjiku', 'grace@example.com', 'User', 'Active'],
                  ['Brian Otieno', 'brian@example.com', 'Admin', 'Active'],
                  ['Amina Ali', 'amina@example.com', 'User', 'Inactive'],
                ].map(([name, email, role, status]) => (
                  <tr key={email}>
                    <td className="px-3 py-4 text-sm font-semibold text-slate-900">{name}</td>
                    <td className="px-3 py-4 text-sm text-slate-500">{email}</td>
                    <td className="px-3 py-4 text-sm text-slate-600">{role}</td>
                    <td className="px-3 py-4">
                      <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-600">
                        {status}
                      </span>
                    </td>
                    <td className="px-3 py-4">
                      <div className="flex gap-2">
                        <ActionButton>Edit</ActionButton>
                        <ActionButton>Disable</ActionButton>
                        <ActionButton tone="danger">Delete</ActionButton>
                      </div>
                    </td>
                  </tr>
                ))}
              />
            </section>

            <section className="rounded-[1.75rem] border border-slate-200 bg-white/95 p-5 shadow-sm">
              <div className="mb-4 flex items-center justify-between">
                <h3 className="text-lg font-semibold text-slate-950">
                  Knowledge base management
                </h3>
                <button
                  type="button"
                  className="rounded-full bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-[0_10px_20px_rgba(37,99,235,0.18)]"
                >
                  Add New
                </button>
              </div>

              <div className="space-y-3">
                {[
                  ['What are dividends?', 'Explains dividends using simple NSE examples.', 'Education', 'May 2026'],
                  ['How do I compare stocks?', 'Shows price, P/E ratio, yield, and risk basics.', 'Investing basics', 'May 2026'],
                  ['What affects stock prices?', 'Covers news, earnings, rates, and demand.', 'Market learning', 'Apr 2026'],
                ].map(([question, preview, category, date]) => (
                  <div
                    key={question}
                    className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4"
                  >
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                      <div>
                        <p className="text-sm font-semibold text-slate-900">{question}</p>
                        <p className="mt-1 text-xs leading-5 text-slate-500">{preview}</p>
                        <p className="mt-2 text-xs text-slate-400">
                          {category} | Last updated {date}
                        </p>
                      </div>
                      <div className="flex gap-2">
                        <ActionButton>Edit</ActionButton>
                        <ActionButton tone="danger">Delete</ActionButton>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <section className="rounded-[1.75rem] border border-slate-200 bg-white/95 p-5 shadow-sm">
              <h3 className="mb-4 text-lg font-semibold text-slate-950">
                Company data management
              </h3>
              <AdminTable
                columns={['Company', 'Ticker', 'Sector', 'Current price', 'Last updated', 'Actions']}
                rows={[
                  ['Safaricom PLC', 'SCOM', 'Telecommunications', 'KES 22.80', 'Today'],
                  ['KCB Group', 'KCB', 'Banking', 'KES 38.75', 'Today'],
                  ['Equity Group', 'EQTY', 'Banking', 'KES 47.50', 'Today'],
                ].map(([company, ticker, sector, price, updated]) => (
                  <tr key={ticker}>
                    <td className="px-3 py-4 text-sm font-semibold text-slate-900">{company}</td>
                    <td className="px-3 py-4 text-sm text-blue-600">{ticker}</td>
                    <td className="px-3 py-4 text-sm text-slate-500">{sector}</td>
                    <td className="px-3 py-4 text-sm text-slate-700">{price}</td>
                    <td className="px-3 py-4 text-sm text-slate-400">{updated}</td>
                    <td className="px-3 py-4">
                      <div className="flex gap-2">
                        <ActionButton>Update information</ActionButton>
                        <ActionButton>Edit profile</ActionButton>
                      </div>
                    </td>
                  </tr>
                ))}
              />
            </section>
          </div>

          <aside className="space-y-6">
            <section className="rounded-[1.75rem] border border-slate-200 bg-white/95 p-5 shadow-sm">
              <h3 className="text-lg font-semibold text-slate-950">
                System status
              </h3>
              <div className="mt-4 space-y-3">
                <StatusCard label="AI chatbot" status="Online" />
                <StatusCard label="Database" status="Healthy" />
                <StatusCard label="API connection" status="Connected" />
              </div>
            </section>

            <section className="rounded-[1.75rem] border border-slate-200 bg-white/95 p-5 shadow-sm">
              <h3 className="text-lg font-semibold text-slate-950">
                Daily conversations
              </h3>
              <div className="mt-4 h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={conversationData} margin={{ top: 8, right: 8, left: -24, bottom: 0 }}>
                    <XAxis dataKey="day" tick={{ fill: '#94a3b8', fontSize: 11 }} tickLine={false} axisLine={false} />
                    <YAxis hide />
                    <Tooltip />
                    <Line type="monotone" dataKey="chats" stroke="#2563eb" strokeWidth={2.5} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </section>

            <section className="rounded-[1.75rem] border border-slate-200 bg-white/95 p-5 shadow-sm">
              <h3 className="text-lg font-semibold text-slate-950">
                Most searched stocks
              </h3>
              <div className="mt-4 h-44">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={searchedStocks} margin={{ top: 8, right: 8, left: -24, bottom: 0 }}>
                    <XAxis dataKey="ticker" tick={{ fill: '#94a3b8', fontSize: 11 }} tickLine={false} axisLine={false} />
                    <YAxis hide />
                    <Tooltip />
                    <Bar dataKey="searches" fill="#93c5fd" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </section>

            <section className="rounded-[1.75rem] border border-blue-100 bg-blue-50/70 p-5 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">
                Most asked questions
              </p>
              <div className="mt-4 space-y-2">
                {['What is Safaricom price?', 'Which stocks pay dividends?', 'Compare KCB and Equity'].map((question) => (
                  <div key={question} className="rounded-2xl bg-white px-4 py-3 text-sm text-slate-600 shadow-sm">
                    {question}
                  </div>
                ))}
              </div>
            </section>
          </aside>
        </section>
      </div>
    </main>
  )
}

export default AdminDashboardScreen
