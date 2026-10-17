export function normalizeApiBase(configuredApiUrl, pageUrl) {
  if (!configuredApiUrl?.trim()) return '/api/v1'

  const configuredUrl = configuredApiUrl.trim()
  const usesAbsoluteUrl = /^https?:\/\//i.test(configuredUrl)
  const page = new URL(pageUrl)
  const apiUrl = new URL(configuredUrl, page.origin)

  if (
    page.protocol === 'https:' &&
    apiUrl.protocol === 'http:'
  ) {
    apiUrl.protocol = 'https:'
  }

  if (!apiUrl.pathname || apiUrl.pathname === '/') {
    apiUrl.pathname = '/api/v1'
  }

  return usesAbsoluteUrl
    ? `${apiUrl.origin}${apiUrl.pathname.replace(/\/$/, '')}`
    : apiUrl.pathname.replace(/\/$/, '')
}

export function getApiBase() {
  return normalizeApiBase(
    import.meta.env?.VITE_API_URL,
    window.location.href,
  )
}
