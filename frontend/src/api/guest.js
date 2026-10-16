import { request } from './axios'

export const getCourses = () => request('/courses')
export const getAnnouncements = () => request('/announcements')