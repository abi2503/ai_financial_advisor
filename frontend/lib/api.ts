import axios from 'axios'

const ALEX_API = process.env.NEXT_PUBLIC_ALEX_API

export async function runResearch(question: string) {
  const response = await axios.post(
    `${ALEX_API}/ingest`,
    { topic: question },
    {
      headers: { 'Content-Type': 'application/json' },
      timeout: 120000
    }
  )
  return response.data
}

export async function searchResearch(query: string) {
  const response = await axios.post('/api/search', { query }, { timeout: 30000 })
  return response.data
}
