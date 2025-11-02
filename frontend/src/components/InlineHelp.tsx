'use client'

import { useState } from 'react'
import { Info, X, BookOpen } from 'lucide-react'
import Link from 'next/link'

interface InlineHelpProps {
  title: string
  content: string | React.ReactNode
  learnMoreLink?: string
  variant?: 'info' | 'warning' | 'tip'
  defaultOpen?: boolean
}

export default function InlineHelp({
  title,
  content,
  learnMoreLink,
  variant = 'info',
  defaultOpen = false,
}: InlineHelpProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen)

  const variantStyles = {
    info: {
      border: 'border-blue-200',
      bg: 'bg-blue-50',
      icon: 'text-blue-600',
      text: 'text-blue-900',
      button: 'text-blue-700 hover:text-blue-900',
    },
    warning: {
      border: 'border-yellow-200',
      bg: 'bg-yellow-50',
      icon: 'text-yellow-600',
      text: 'text-yellow-900',
      button: 'text-yellow-700 hover:text-yellow-900',
    },
    tip: {
      border: 'border-green-200',
      bg: 'bg-green-50',
      icon: 'text-green-600',
      text: 'text-green-900',
      button: 'text-green-700 hover:text-green-900',
    },
  }

  const styles = variantStyles[variant]

  return (
    <div className={`border ${styles.border} ${styles.bg} rounded-lg mb-4`}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`w-full px-4 py-3 flex items-center justify-between ${styles.button} transition-colors`}
      >
        <div className="flex items-center gap-2">
          <Info className={`w-5 h-5 ${styles.icon}`} />
          <span className="font-medium text-sm">{title}</span>
        </div>
        {isOpen ? <X className="w-4 h-4" /> : <span className="text-xs">Show</span>}
      </button>

      {isOpen && (
        <div className={`px-4 pb-4 text-sm ${styles.text}`}>
          <div className="mb-3">{content}</div>
          {learnMoreLink && (
            <Link
              href={learnMoreLink}
              className={`inline-flex items-center gap-1 ${styles.button} text-xs font-medium`}
            >
              <BookOpen className="w-3 h-3" />
              Learn more in documentation
            </Link>
          )}
        </div>
      )}
    </div>
  )
}
