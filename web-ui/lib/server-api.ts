const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function getProjects() {
  try {
    const res = await fetch(`${API_URL}/api/projects`, { 
      cache: 'no-store',
      headers: {
        'Content-Type': 'application/json',
      }
    })
    if (!res.ok) {
      console.error('[Server] Failed to fetch projects:', res.status)
      return []
    }
    return res.json()
  } catch (e) {
    console.error('[Server] Error fetching projects:', e)
    return []
  }
}
