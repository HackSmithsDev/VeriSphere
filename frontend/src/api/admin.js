import { request } from './axios'

export const getAdminOverview = (token) =>
  request('/admin/overview', { token })
export const getAdminUsers = (token) => request('/admin/users', { token })
export const createTeacher = (token, teacher) =>
  request('/admin/teachers', { token, method: 'POST', body: teacher })