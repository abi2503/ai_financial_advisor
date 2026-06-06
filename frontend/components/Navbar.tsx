'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { UserButton } from '@clerk/nextjs'
import { Brain, LayoutDashboard, MessageSquare, PieChart, History } from 'lucide-react'

const navItems = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/research',  label: 'Research',  icon: MessageSquare },
  { href: '/portfolio', label: 'Portfolio', icon: PieChart },
  { href: '/history',   label: 'History',   icon: History },
]

export default function Navbar() {
  const pathname = usePathname()
  return (
    <nav className="border-b border-gray-800 bg-gray-950 px-6 py-4 flex justify-between items-center sticky top-0 z-50">
      <Link href="/dashboard" className="flex items-center gap-2">
        <Brain className="text-blue-400" size={24} />
        <span className="font-bold text-white">Alex AI</span>
      </Link>
      <div className="flex items-center gap-1">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active = pathname === href
          return (
            <Link key={href} href={href} className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition ${active ? 'bg-blue-600/20 text-blue-400' : 'text-gray-400 hover:text-white hover:bg-gray-800'}`}>
              <Icon size={16} />
              {label}
            </Link>
          )
        })}
      </div>
      <UserButton appearance={{ elements: { avatarBox: 'w-8 h-8' } }} />
    </nav>
  )
}