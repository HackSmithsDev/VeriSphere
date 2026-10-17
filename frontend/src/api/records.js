import { request } from './axios'

export const getAcademicOptions = (token) =>
  request('/teacher/academic-options', { token })

export const getAcademicRecords = (token) =>
  request('/student/academic-records', { token })

export const saveAttendance = (token, entry) =>
  request('/teacher/attendance', { token, method: 'POST', body: entry })

export const saveAssessmentMark = (token, entry) =>
  request('/teacher/marks', { token, method: 'POST', body: entry })

export const getAcademicReport = (token) =>
  request('/admin/reports/academics', { token })
