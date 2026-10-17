import { request } from './axios'
import { getApiBase } from './base'

const API_BASE = getApiBase()

export const uploadEvidence = async (token, file) => {
  const body = new FormData()
  body.set('file', file)
  const response = await fetch(`${API_BASE}/student/evidence`, {
    method: 'POST',
    headers: { Authorization: `******` },
    body,
  })
  const result = await response.json().catch(() => null)
  if (!response.ok) {
    throw new Error(result?.detail || `Upload failed (${response.status})`)
  }
  return result
}

export const downloadEvidence = async (token, id) => {
  const response = await fetch(`${API_BASE}/student/evidence/${encodeURIComponent(id)}`, {
    headers: { Authorization: `******` },
  })
  if (!response.ok) {
    const result = await response.json().catch(() => null)
    throw new Error(result?.detail || `Download failed (${response.status})`)
  }
  const disposition = response.headers.get('content-disposition') || ''
  const filenameMatch = disposition.match(
    /filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i,
  )
  const encodedFilename = filenameMatch?.[1]
  const filename = encodedFilename
    ? decodeURIComponent(encodedFilename)
    : filenameMatch?.[2] || 'verified-student-evidence'
  return { blob: await response.blob(), filename }
}

export const getStudentActivities = (token) =>
  request('/student/activities', { token })

export const submitStudentActivity = (token, activity) =>
  request('/student/activities', { token, method: 'POST', body: activity })

export const updateStudentActivity = (token, id, activity) =>
  request(`/student/activities/${id}`, { token, method: 'PUT', body: activity })

export const getPendingActivities = (token) =>
  request('/teacher/activities', { token })

export const reviewActivity = (token, id, review) =>
  request(`/teacher/activities/${id}/review`, {
    token,
    method: 'POST',
    body: review,
  })

export const getStudentPortfolio = (token) =>
  request('/student/portfolio', { token })

export const enablePortfolioSharing = (token) =>
  request('/student/portfolio/share', { token, method: 'POST' })

export const disablePortfolioSharing = (token) =>
  request('/student/portfolio/share', { token, method: 'DELETE' })

export const getSharedPortfolio = (shareToken) =>
  request(`/portfolios/${encodeURIComponent(shareToken)}`)

export const getSharedEvidenceUrl = (shareToken, evidenceId) =>
  `${API_BASE}/student/evidence/shared/${encodeURIComponent(shareToken)}/${encodeURIComponent(evidenceId)}`

export const getActivityReport = (token) =>
  request('/admin/reports/activities', { token })
