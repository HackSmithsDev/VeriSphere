import { getApiBase } from './base'

const API_BASE = getApiBase()

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

export async function requestBlob(path, { token } = {}) {
  const headers = new Headers()
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const response = await fetch(`${API_BASE}${path}`, { headers })
  if (!response.ok) {
    const result = await response.json().catch(() => null)
    throw new Error(result?.detail || `Request failed (${response.status})`)
  }
  return response.blob()
}

export async function requestFile(path, { token, file, field = 'file' } = {}) {
  const headers = new Headers({ Accept: 'application/json' })
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const body = new FormData()
  body.set(field, file)
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers,
    body,
  })
  const result = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = result?.detail
    throw new Error(
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map((item) => typeof item === 'string' ? item : item.msg).join(', ')
          : `Request failed (${response.status})`,
    )
  }
  return result
}