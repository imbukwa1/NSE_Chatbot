import { useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'

function firstInitial(user) {
  return (user?.fullName || user?.email || 'U').trim().charAt(0).toUpperCase()
}

function firstName(user) {
  return (user?.fullName || user?.email || 'User').split(' ')[0]
}

function NavbarAuthControls({ onLogin, onRegister, onProfile }) {
  const { user, isAuthenticated, isAuthLoading, logout } = useAuth()
  const [isOpen, setIsOpen] = useState(false)

  if (isAuthLoading) {
    return (
      <div className="h-10 w-28 animate-pulse rounded-full bg-white/70 shadow-sm" />
    )
  }

  if (!isAuthenticated) {
    return (
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onLogin}
          className="hidden rounded-full bg-white px-4 py-2 text-sm font-medium text-slate-600 shadow-sm transition hover:bg-slate-50 sm:inline-flex"
        >
          Login
        </button>
        <button
          type="button"
          onClick={onRegister}
          className="rounded-full bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-[0_12px_26px_rgba(37,99,235,0.22)] transition hover:bg-blue-700"
        >
          Register
        </button>
      </div>
    )
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setIsOpen((current) => !current)}
        className="flex items-center gap-2 rounded-full bg-white px-2 py-1.5 pr-3 text-sm font-semibold text-slate-700 shadow-[0_12px_26px_rgba(96,126,203,0.14)] ring-1 ring-slate-200 transition hover:text-blue-700"
        aria-label="Open user menu"
      >
        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-600 text-sm font-semibold text-white">
          {firstInitial(user)}
        </span>
        <span className="hidden max-w-24 truncate sm:inline">{firstName(user)}</span>
      </button>

      {isOpen && (
        <div className="absolute right-0 z-40 mt-3 w-56 rounded-3xl border border-slate-200 bg-white p-2 shadow-[0_22px_60px_rgba(15,23,42,0.16)]">
          <div className="px-3 py-3">
            <p className="truncate text-sm font-semibold text-slate-900">
              {user.fullName}
            </p>
            <p className="truncate text-xs text-slate-500">{user.email}</p>
          </div>
          {onProfile && (
            <button
              type="button"
              onClick={() => {
                setIsOpen(false)
                onProfile()
              }}
              className="w-full rounded-2xl px-3 py-2 text-left text-sm font-medium text-slate-600 transition hover:bg-slate-50 hover:text-blue-700"
            >
              Profile
            </button>
          )}
          <button
            type="button"
            onClick={() => {
              setIsOpen(false)
              logout()
            }}
            className="w-full rounded-2xl px-3 py-2 text-left text-sm font-medium text-rose-600 transition hover:bg-rose-50"
          >
            Logout
          </button>
        </div>
      )}
    </div>
  )
}

export default NavbarAuthControls
