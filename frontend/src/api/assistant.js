import { request } from './axios'

export const chatWithAssistant = (token, messages) =>
  request('/assistant/chat', {
    token,
    method: 'POST',
    body: { messages },
  })
