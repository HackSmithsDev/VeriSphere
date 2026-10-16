const API_BASE = (import.meta.env.VITE_API_URL || '/api/v1').replace(/\/$/, '')

export async function request(path, { token, method = 'GET', body } = {}) {
  const headers = new Headers({ Accept: 'application/json' })
  if (body !== undefined) headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  })

  if (response.status === 204) return null
  const result = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = result?.detail
    throw new Error(
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map((item) => item.msg).join(', ')
          : `Request failed (${response.status})`,
    )
  }
  return result
}