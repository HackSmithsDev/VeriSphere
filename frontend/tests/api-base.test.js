import assert from 'node:assert/strict'
import test from 'node:test'

import { normalizeApiBase } from '../src/api/base.js'

test('defaults to the same-origin versioned API path', () => {
  assert.equal(
    normalizeApiBase(undefined, 'https://verisphere.hacksmiths.dev/'),
    '/api/v1',
  )
})

test('upgrades an insecure external API and adds the API prefix', () => {
  assert.equal(
    normalizeApiBase(
      'http://verisphere-api.hacksmiths.dev/',
      'https://verisphere.hacksmiths.dev/',
    ),
    'https://verisphere-api.hacksmiths.dev/api/v1',
  )
})

test('preserves an explicitly configured HTTPS API path', () => {
  assert.equal(
    normalizeApiBase(
      'https://verisphere-api.hacksmiths.dev/api/v1/',
      'https://verisphere.hacksmiths.dev/',
    ),
    'https://verisphere-api.hacksmiths.dev/api/v1',
  )
})

test('preserves same-origin relative API paths', () => {
  assert.equal(
    normalizeApiBase('/api/v1/', 'http://localhost:5176/'),
    '/api/v1',
  )
})
