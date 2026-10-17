import { useState } from 'react'
import { downloadEvidence } from '../../api/activities'

export function EvidenceLink({ token, evidenceId, label = 'Download evidence' }) {
  const [error, setError] = useState('')

  const openEvidence = async () => {
    setError('')
    try {
      const { blob, filename } = await downloadEvidence(token, evidenceId)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      link.click()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (requestError) {
      setError(requestError.message)
    }
  }

  return (
    <span className="evidence-link">
      <button className="text-button" onClick={openEvidence}>{label}</button>
      {error && <span className="evidence-link-error" role="alert">{error}</span>}
    </span>
  )
}
