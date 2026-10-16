import { request } from './axios'

export const getTeacherDashboard = (token) =>
  request('/teacher/dashboard', { token })
export const getSubmissions = (token) => request('/teacher/submissions', { token })
export const reviewSubmission = (token, id, review) =>
  request(`/teacher/submissions/${id}/review`, {
    token,
    method: 'POST',
    body: review,
  })