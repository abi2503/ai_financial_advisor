import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

export const markdownComponents = {
  h1: ({ children }: { children?: React.ReactNode }) => (
    <h1 className="text-lg font-bold text-white mb-2 mt-1">{children}</h1>
  ),
  h2: ({ children }: { children?: React.ReactNode }) => (
    <h2 className="text-base font-bold text-white mb-2 mt-3 pb-1 border-b border-gray-700">{children}</h2>
  ),
  h3: ({ children }: { children?: React.ReactNode }) => (
    <h3 className="text-sm font-semibold text-blue-400 mb-1 mt-2">{children}</h3>
  ),
  p: ({ children }: { children?: React.ReactNode }) => (
    <p className="mb-2 text-gray-200 leading-relaxed">{children}</p>
  ),
  ul: ({ children }: { children?: React.ReactNode }) => (
    <ul className="mb-3 space-y-1.5">{children}</ul>
  ),
  ol: ({ children }: { children?: React.ReactNode }) => (
    <ol className="mb-3 space-y-1.5 list-decimal list-inside text-gray-300">{children}</ol>
  ),
  li: ({ children }: { children?: React.ReactNode }) => (
    <li className="flex gap-2 text-gray-300 text-sm">
      <span className="text-blue-400 mt-0.5 flex-shrink-0">•</span>
      <span>{children}</span>
    </li>
  ),
  strong: ({ children }: { children?: React.ReactNode }) => (
    <strong className="text-white font-semibold">{children}</strong>
  ),
  em: ({ children }: { children?: React.ReactNode }) => (
    <em className="text-gray-300 italic">{children}</em>
  ),
  hr: () => <hr className="border-gray-700 my-4" />,
  code: ({ children }: { children?: React.ReactNode }) => (
    <code className="bg-gray-800 text-blue-300 px-1.5 py-0.5 rounded text-xs font-mono">{children}</code>
  ),
  blockquote: ({ children }: { children?: React.ReactNode }) => (
    <blockquote className="border-l-2 border-blue-400 pl-3 text-gray-400 italic my-3 bg-blue-500/5 py-2 rounded-r">
      {children}
    </blockquote>
  ),
  table: ({ children }: { children?: React.ReactNode }) => (
    <div className="overflow-x-auto my-3 rounded-lg border border-gray-700">
      <table className="w-full text-sm border-collapse">{children}</table>
    </div>
  ),
  thead: ({ children }: { children?: React.ReactNode }) => (
    <thead className="bg-gray-800/80">{children}</thead>
  ),
  tbody: ({ children }: { children?: React.ReactNode }) => (
    <tbody className="divide-y divide-gray-800">{children}</tbody>
  ),
  tr: ({ children }: { children?: React.ReactNode }) => (
    <tr className="hover:bg-gray-800/40 transition">{children}</tr>
  ),
  th: ({ children }: { children?: React.ReactNode }) => (
    <th className="px-4 py-2.5 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">{children}</th>
  ),
  td: ({ children }: { children?: React.ReactNode }) => (
    <td className="px-4 py-2.5 text-gray-200">{children}</td>
  ),
  a: ({ children, href }: { children?: React.ReactNode; href?: string }) => (
    <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300 underline">
      {children}
    </a>
  ),
}

function formatInlineMarkdown(text: string): string {
  return text
    // [date] [title] (url) — legacy get_stock_data news format
    .replace(
      /\[([^\]]+)\]\s+\[([^\]]+)\]\s+\(([^)]+)\)/g,
      '<span class="text-gray-500">[$1]</span> <a href="$3" target="_blank" rel="noopener noreferrer" style="color:#60a5fa;text-decoration:underline">$2</a>',
    )
    // Standard [text](url)
    .replace(
      /\[([^\]]+)\]\(([^)]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener noreferrer" style="color:#60a5fa;text-decoration:underline">$1</a>',
    )
    .replace(/\*\*(.*?)\*\*/g, '<strong style="color:white;font-weight:600">$1</strong>')
}

/** Incremental markdown renderer for SSE streaming (matches old research page UX). */
export function renderMarkdownStreaming(text: string): string {
  const lines = text.split('\n')
  let html = ''
  let inTable = false
  let tableHtml = ''

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    if (line.startsWith('|')) {
      if (line.match(/^\|[-: |]+\|$/)) continue
      const cells = line.split('|').filter(c => c.trim()).map(c => formatInlineMarkdown(c.trim()))
      if (!inTable) {
        inTable = true
        tableHtml = '<div style="overflow-x:auto;margin:12px 0;border-radius:8px;border:1px solid #374151"><table style="width:100%;font-size:12px"><thead><tr style="background:#1f2937;border-bottom:1px solid #374151">'
        tableHtml += cells.map(c => `<th style="padding:8px 12px;text-align:left;color:#d1d5db;font-weight:500">${c}</th>`).join('')
        tableHtml += '</tr></thead><tbody>'
      } else {
        tableHtml += '<tr style="border-bottom:1px solid #1f2937">'
        tableHtml += cells.map(c => `<td style="padding:8px 12px;color:#d1d5db">${c}</td>`).join('')
        tableHtml += '</tr>'
      }
      const next = lines[i + 1] || ''
      if (!next.startsWith('|')) {
        tableHtml += '</tbody></table></div>'
        html += tableHtml
        tableHtml = ''
        inTable = false
      }
      continue
    }
    if (inTable) {
      tableHtml += '</tbody></table></div>'
      html += tableHtml
      tableHtml = ''
      inTable = false
    }
    if (line.startsWith('### ') || line.startsWith('## ')) {
      html += `<div style="font-weight:700;color:white;font-size:15px;margin-top:12px;margin-bottom:4px">${formatInlineMarkdown(line.replace(/^#+\s/, ''))}</div>`
    } else if (line.startsWith('# ')) {
      html += `<div style="font-weight:700;color:white;font-size:17px;margin-top:16px;margin-bottom:8px">${formatInlineMarkdown(line.replace(/^#\s/, ''))}</div>`
    } else if (line.startsWith('- ') || line.startsWith('* ')) {
      const t = formatInlineMarkdown(line.slice(2))
      html += `<div style="display:flex;gap:8px;color:#e5e7eb;margin-left:8px"><span style="color:#60a5fa;flex-shrink:0">•</span><span>${t}</span></div>`
    } else if (/^\d+\.\s/.test(line)) {
      const num = line.match(/^(\d+)/)?.[1]
      const t = formatInlineMarkdown(line.replace(/^\d+\.\s/, ''))
      html += `<div style="display:flex;gap:8px;color:#e5e7eb;margin-left:8px"><span style="color:#60a5fa;width:16px;flex-shrink:0">${num}.</span><span>${t}</span></div>`
    } else if (line.startsWith('---')) {
      html += '<div style="border-top:1px solid #374151;margin:8px 0"></div>'
    } else if (!line.trim()) {
      html += '<div style="height:4px"></div>'
    } else if (line.startsWith('**') && line.endsWith('**') && line.length > 4) {
      html += `<div style="font-weight:600;color:white;margin-top:8px">${line.slice(2, -2)}</div>`
    } else {
      html += `<div style="color:#e5e7eb">${formatInlineMarkdown(line)}</div>`
    }
  }
  if (inTable) {
    tableHtml += '</tbody></table></div>'
    html += tableHtml
  }
  return html
}

export default function AlexMarkdown({
  content,
  className = '',
}: {
  content: string
  className?: string
}) {
  if (!content) return null
  return (
    <div className={`alex-markdown ${className}`}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
        {content}
      </ReactMarkdown>
    </div>
  )
}
