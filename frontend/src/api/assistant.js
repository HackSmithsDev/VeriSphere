import { request } from './axios'

export const chatWithAssistant = (token, messages) =>
  request('/assistant/chat', {
    token,
    method: 'POST',
    body: { messages },
  })

export const submitAssistantFeedback = (token, provider, helpful) =>
  request('/assistant/feedback', {
    token,
    method: 'POST',
    body: { provider, helpful },
  })
