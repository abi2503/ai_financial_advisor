'use client'

import { Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import Navbar from '@/components/Navbar'
import AlexChat from '@/components/AlexChat'
import { Brain } from 'lucide-react'

function ResearchContent() {
  const searchParams = useSearchParams()
  const initialQ     = searchParams.get('q') || ''

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-4xl mx-auto w-full px-6 py-6 flex flex-col">
        <div className="flex items-center gap-2 mb-4">
          <Brain className="text-blue-400" size={20} />
          <h1 className="text-lg font-semibold text-white">Alex Research</h1>
          <span className="text-xs text-gray-500 ml-2">Unified chat — auto-routed</span>
        </div>
        <AlexChat initialQuery={initialQ} />
      </main>
    </div>
  )
}

export default function ResearchPageWrapper() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-gray-400 text-sm">Loading...</div>
      </div>
    }>
      <ResearchContent />
    </Suspense>
  )
}
