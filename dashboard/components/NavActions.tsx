'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'

export function NavActions() {
  const router = useRouter()
  const [loggedIn, setLoggedIn] = useState(false)

  useEffect(() => {
    setLoggedIn(!!localStorage.getItem('token'))
  }, [])

  function handleLogout() {
    localStorage.removeItem('token')
    localStorage.removeItem('user_email')
    setLoggedIn(false)
    router.push('/login')
  }

  if (loggedIn) {
    return (
      <button
        onClick={handleLogout}
        className="text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        Logout
      </button>
    )
  }

  return (
    <Link href="/login" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
      Login
    </Link>
  )
}
