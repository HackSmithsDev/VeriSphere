import { request, requestBlob, requestFile } from './axios'

export const getAdminOverview = (token) =>
  request('/admin/overview', { token })
export const getAdminUsers = (token) => request('/admin/users', { token })
export const createTeacher = (token, teacher) =>
  request('/admin/teachers', { token, method: 'POST', body: teacher })
export const saveTeacherCourses = (token, teacherId, courseIds) =>
  request(`/admin/teachers/${teacherId}/courses`, {
    token,
    method: 'PUT',
    body: { course_ids: courseIds },
  })

export const importStudents = (token, workbook) =>
  requestFile('/admin/students/import', { token, file: workbook })

export const downloadStudentImportTemplate = (token) =>
  requestBlob('/admin/students/import-template.xlsx', { token })