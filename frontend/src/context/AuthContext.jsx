/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import {
  authApi,
  clearStoredToken,
  extractToken,
  extractUser,
  getStoredToken,
  storeToken,
} from '../services/api.js'

const AuthContext = createContext(null)

function normalizeUser(user) {
  if (!user) {
    return null
  }

  return {
    id: user.id,
    fullName: user.full_name || user.fullName || user.name || user.email || 'User',
    email: user.email,
    role: user.role,
  }
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => getStoredToken())
  const [user, setUser] = useState(null)
  const [isAuthLoading, setIsAuthLoading] = useState(Boolean(getStoredToken()))

  useEffect(() => {
    let isMounted = true

    async function restoreSession() {
      const storedToken = getStoredToken()
      if (!storedToken) {
        setIsAuthLoading(false)
        return
      }

      try {
        // Validate saved tokens on refresh before trusting any local user state.
        const payload = await authApi.me()
        if (!isMounted) {
          return
        }
        setToken(storedToken)
        setUser(normalizeUser(extractUser(payload)))
      } catch {
        clearStoredToken()
        if (isMounted) {
          setToken(null)
          setUser(null)
        }
      } finally {
        if (isMounted) {
          setIsAuthLoading(false)
        }
      }
    }

    restoreSession()

    return () => {
      isMounted = false
    }
  }, [])

  const login = async ({ email, password }) => {
    const payload = await authApi.login({ email, password })
    const nextToken = extractToken(payload)

    if (!nextToken) {
      throw new Error('Login succeeded, but no token was returned by the backend.')
    }

    storeToken(nextToken)
    setToken(nextToken)

    const userFromLogin = normalizeUser(extractUser(payload))
    if (userFromLogin?.email) {
      setUser(userFromLogin)
      return userFromLogin
    }

    const profilePayload = await authApi.me()
    const profileUser = normalizeUser(extractUser(profilePayload))
    setUser(profileUser)
    return profileUser
  }

  const register = async ({ fullName, email, password }) => {
    return authApi.register({ fullName, email, password })
  }

  const logout = async () => {
    try {
      if (getStoredToken()) {
        await authApi.logout()
      }
    } catch {
      // The client still owns clearing local auth state even if the server is unreachable.
    } finally {
      clearStoredToken()
      setToken(null)
      setUser(null)
    }
  }

  const value = useMemo(
    () => ({
      token,
      user,
      isAuthenticated: Boolean(token && user),
      isAuthLoading,
      login,
      register,
      logout,
    }),
    [token, user, isAuthLoading],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
