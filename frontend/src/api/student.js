import { request } from './axios'

export const getStudentDashboard = (token) =>
  request('/student/dashboard', { token })
export const getMilestones = (token) => request('/student/milestones', { token })
export const submitMilestone = (token, id, submission) =>
  request(`/student/milestones/${id}/submit`, {
    token,
    method: 'POST',
    body: submission,
  })