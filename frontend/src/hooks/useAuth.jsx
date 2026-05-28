import { createContext, useContext, useState, useEffect } from 'react'
import { getMe, login as apiLogin, logout as apiLogout } from '../api/auth'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [tenant, setTenant] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) { setLoading(false); return }
    getMe()
      .then((data) => { setUser(data.user); setTenant(data.tenant) })
      .catch(() => localStorage.removeItem('token'))
      .finally(() => setLoading(false))
  }, [])

  const login = async (username, password) => {
    const data = await apiLogin(username, password)
    localStorage.setItem('token', data.token)
    setUser(data.user)
    const me = await getMe()
    setTenant(me.tenant)
    return data
  }

  const logout = async () => {
    await apiLogout().catch(() => {})
    localStorage.removeItem('token')
    setUser(null)
    setTenant(null)
  }

  return (
    <AuthContext.Provider value={{ user, tenant, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
