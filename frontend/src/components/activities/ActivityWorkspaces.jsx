import { useEffect, useState } from 'react'
import { Globe } from 'lucide-react'
import {
  disablePortfolioSharing,
  downloadActivityReportWorkbook,
  enablePortfolioSharing,
  getActivityReport,
  getGithubProfile,
  getLinkedInAuthorizationUrl,
  getLinkedInProfile,
  getPendingActivities,
  getSharedPortfolio,
  getStudentActivities,
  getStudentPortfolio,
  getStudentResume,
  reviewActivity,
  submitStudentActivity,
  updateStudentActivity,
  uploadEvidence,
  getSharedEvidenceUrl,
} from '../../api/activities'
import { ActionButton } from '../ui/ActionButton'
import { downloadAcademicReportWorkbook, getAcademicReport } from '../../api/records'
import { EvidenceLink } from '../evidence/EvidenceLink'

const categories = [
  ['certification', 'Certification'],
  ['course', 'Course or MOOC'],
  ['event', 'Seminar or conference'],
  ['internship', 'Internship'],
  ['project', 'Project or open-source work'],
  ['club', 'Club activity'],
  ['volunteering', 'Volunteering'],
  ['leadership', 'Leadership'],
  ['competition', 'Competition'],
  ['community_service', 'Community service'],
  ['other', 'Other'],
]

const labels = Object.fromEntries(categories)

function csvCell(value) {
  const text = String(value)
  const safeText = /^[\s]*[=+\-@]/.test(text) ? `'${text}` : text
  return `"${safeText.replaceAll('"', '""')}"`
}

function saveBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}

function ErrorMessage({ message }) {
  return message ? <div className="alert alert-error" role="alert">{message}</div> : null
}

function RecordCard({ activity, onEdit, onReview, token, publicShareToken }) {
  const state = activity.status || 'verified'
  return (
    <article className="record-card">
      <div className="record-card-heading">
        <div>
          <span className="eyebrow">{labels[activity.category] || activity.category}</span>
          <h2>{activity.title}</h2>
        </div>
        <span className={`status-pill status-${state === 'verified' ? 'verified' : state === 'pending_verification' ? 'pending' : 'progress'}`}>
          {state.replaceAll('_', ' ')}
        </span>
      </div>
      <p>{activity.description}</p>
      <div className="record-meta">
        {activity.issuer && <span>{activity.issuer}</span>}
        {activity.achieved_on && <span>{activity.achieved_on}</span>}
        {activity.proof_url && <a href={activity.proof_url} target="_blank" rel="noreferrer">View evidence link</a>}
        {activity.evidence_file_id && publicShareToken && (
          <a href={getSharedEvidenceUrl(publicShareToken, activity.evidence_file_id)} target="_blank" rel="noreferrer">View verified file</a>
        )}
        {activity.evidence_file_id && token && <EvidenceLink token={token} evidenceId={activity.evidence_file_id} />}
        {activity.student && <span>Submitted by {activity.student}</span>}
      </div>
      {activity.review_feedback && <p className="record-feedback">Review note: {activity.review_feedback}</p>}
      {onEdit && activity.status === 'needs_revision' && (
        <button className="text-button" onClick={() => onEdit(activity)}>Edit and resubmit</button>
      )}
      {onReview && (
        <div className="record-actions">
          <button className="button button-secondary" onClick={() => onReview(activity, 'verified')}>Verify</button>
          <button className="button button-quiet" onClick={() => onReview(activity, 'needs_revision')}>Request changes</button>
        </div>
      )}
    </article>
  )
}

export function ActivityWorkspace({ token, staff = false }) {
  const [activities, setActivities] = useState([])
  const [editing, setEditing] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    const loadActivities = async () => {
      try {
        const data = staff ? await getPendingActivities(token) : await getStudentActivities(token)
        if (!cancelled) {
          setActivities(data)
          setError('')
        }
      } catch (requestError) {
        if (!cancelled) setError(requestError.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void loadActivities()
    return () => {
      cancelled = true
    }
  }, [staff, token])

  const refresh = async () => {
    setError('')
    try {
      setActivities(staff ? await getPendingActivities(token) : await getStudentActivities(token))
    } catch (requestError) {
      setError(requestError.message)
      throw requestError
    }
  }

  const save = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    const formElement = event.currentTarget
    const form = new FormData(formElement)
    const activity = {
      category: form.get('category'),
      title: form.get('title'),
      description: form.get('description'),
      issuer: form.get('issuer') || null,
      achieved_on: form.get('achieved_on') || null,
    }
    try {
      const proofUrl = form.get('proof_url')
      const evidenceFile = form.get('evidence_file')
      if (proofUrl && evidenceFile?.size) {
        throw new Error('Choose either an evidence link or a file, not both.')
      }
      if (evidenceFile?.size > 10 * 1024 * 1024) {
        throw new Error('Evidence files must be 10 MB or smaller.')
      }
      activity.proof_url = proofUrl || null
      activity.evidence_file_id = evidenceFile?.size
        ? (await uploadEvidence(token, evidenceFile)).id
        : proofUrl
          ? null
          : editing?.evidence_file_id || null
      if (editing) await updateStudentActivity(token, editing.id, activity)
      else await submitStudentActivity(token, activity)
      setEditing(null)
      formElement.reset()
      await refresh()
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusy(false)
    }
  }

  const review = async (activity, decision) => {
    const feedback = decision === 'needs_revision'
      ? window.prompt('What should the student update?', '')
      : ''
    if (feedback === null) return
    setError('')
    try {
      await reviewActivity(token, activity.id, { decision, feedback })
      await refresh()
    } catch (requestError) {
      setError(requestError.message)
    }
  }

  return (
    <section>
      <div className="page-heading">
        <div>
          <span className="eyebrow">{staff ? 'FACULTY REVIEW' : 'YOUR VERIFIED RECORD'}</span>
          <h1>{staff ? 'Activity reviews' : 'Achievements'}</h1>
          <p className="muted">{staff ? 'Review evidence for student activities and achievements.' : 'Add achievements beyond your curriculum and submit evidence for faculty verification.'}</p>
        </div>
      </div>
      <ErrorMessage message={error} />
      {!staff && (
        <form className="panel activity-form" onSubmit={save}>
          <h2>{editing ? 'Update activity' : 'Add an achievement'}</h2>
          <div className="field-row">
            <label>Activity type
              <select name="category" defaultValue={editing?.category || 'certification'} key={editing?.id || 'new'}>
                {categories.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </label>
            <label>Title
              <input name="title" required minLength="2" maxLength="255" defaultValue={editing?.title || ''} key={`title-${editing?.id || 'new'}`} />
            </label>
          </div>
          <div className="field-row">
            <label>Issuing organization <span className="optional">(optional)</span>
              <input name="issuer" maxLength="255" defaultValue={editing?.issuer || ''} key={`issuer-${editing?.id || 'new'}`} />
            </label>
            <label>Date achieved <span className="optional">(optional)</span>
              <input name="achieved_on" type="date" defaultValue={editing?.achieved_on || ''} key={`date-${editing?.id || 'new'}`} />
            </label>
          </div>
          <label>Description
            <textarea name="description" rows="3" required minLength="10" maxLength="4000" defaultValue={editing?.description || ''} key={`description-${editing?.id || 'new'}`} />
          </label>
          <div className="field-row">
            <label>Evidence link <span className="optional">(or attach a PDF, PNG, JPEG)</span>
              <input name="proof_url" type="url" placeholder="https://…" defaultValue={editing?.proof_url || ''} key={`proof-${editing?.id || 'new'}`} />
            </label>
            <label>Evidence file <span className="optional">(max 10 MB)</span>
              <input name="evidence_file" type="file" accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg" />
            </label>
          </div>
          {editing?.evidence_file_id && <p className="muted">The existing uploaded file will remain attached unless replaced with another evidence source.</p>}
          <div className="record-actions">
            {editing && <button type="button" className="button button-quiet" onClick={() => setEditing(null)}>Cancel edit</button>}
            <ActionButton type="submit" disabled={busy}>{busy ? 'Submitting…' : editing ? 'Resubmit for verification' : 'Submit for verification'}</ActionButton>
          </div>
        </form>
      )}
      <div className="record-list">
        <h2>{staff ? 'Awaiting review' : 'Your submissions'}</h2>
        {loading ? <p className="muted">Loading activities…</p> : activities.length
          ? activities.map((activity) => (
              <RecordCard
                key={activity.id}
                activity={activity}
                onEdit={staff ? undefined : setEditing}
                onReview={staff ? review : undefined}
                token={token}
              />
            ))
          : <p className="muted">{staff ? 'No student activities are waiting for review.' : 'No activities yet. Add a verified achievement to start your broader student record.'}</p>}
      </div>
    </section>
  )
}

export function PortfolioWorkspace({ token }) {
  const [portfolio, setPortfolio] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [resumeBusy, setResumeBusy] = useState(false)
  const [githubBusy, setGithubBusy] = useState(false)
  const [githubProfile, setGithubProfile] = useState(null)
  const [linkedInBusy, setLinkedInBusy] = useState(false)
  const [linkedInProfile, setLinkedInProfile] = useState(null)

  useEffect(() => {
    let cancelled = false
    getStudentPortfolio(token)
      .then((data) => {
        if (!cancelled) {
          setPortfolio(data)
          setError('')
        }
      })
      .catch((requestError) => {
        if (!cancelled) setError(requestError.message)
      })
    return () => {
      cancelled = true
    }
  }, [token])

  useEffect(() => {
    let cancelled = false
    getLinkedInProfile(token)
      .then((data) => {
        if (!cancelled) setLinkedInProfile(data)
      })
      .catch((requestError) => {
        if (!cancelled) setError(requestError.message)
      })
    return () => {
      cancelled = true
    }
  }, [token])

  const refresh = async () => {
    const data = await getStudentPortfolio(token)
    setPortfolio(data)
    setError('')
  }

  const toggleSharing = async () => {
    setBusy(true)
    setError('')
    try {
      if (portfolio?.share_enabled) await disablePortfolioSharing(token)
      else await enablePortfolioSharing(token)
      await refresh()
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusy(false)
    }
  }

  const shareUrl = portfolio?.share_url
    ? new URL(portfolio.share_url, window.location.origin).toString()
    : ''
  const shareToken = portfolio?.share_url?.split('/').at(-1) || ''

  const copyShareUrl = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl)
      setError('')
    } catch {
      setError('Could not copy the link. Select and copy the displayed URL instead.')
    }
  }

  const downloadResume = async () => {
    setResumeBusy(true)
    setError('')
    try {
      saveBlob(await getStudentResume(token), 'verisphere-resume.html')
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setResumeBusy(false)
    }
  }

  const loadGithubProfile = async (event) => {
    event.preventDefault()
    const username = new FormData(event.currentTarget).get('github_username')?.toString().trim()
    if (!username || githubBusy) return
    setGithubBusy(true)
    setError('')
    try {
      setGithubProfile(await getGithubProfile(token, username))
    } catch (requestError) {
      setGithubProfile(null)
      setError(requestError.message)
    } finally {
      setGithubBusy(false)
    }
  }

  const connectLinkedIn = async () => {
    setLinkedInBusy(true)
    setError('')
    try {
      const { authorization_url: authorizationUrl } =
        await getLinkedInAuthorizationUrl(token)
      window.location.assign(authorizationUrl)
    } catch (requestError) {
      setError(requestError.message)
      setLinkedInBusy(false)
    }
  }

  return (
    <section>
      <div className="page-heading">
        <div>
          <span className="eyebrow">VERIFIED, READY TO SHARE</span>
          <h1>My portfolio</h1>
          <p className="muted">Only faculty-verified milestones and activities appear in this portfolio.</p>
        </div>
      </div>
      <ErrorMessage message={error} />
      {portfolio && (
        <>
          <div className="panel portfolio-share">
            <div><strong>{portfolio.share_enabled ? 'Public link is enabled' : 'Your portfolio is private'}</strong><p className="muted">{portfolio.share_enabled ? 'Anyone with this link can see verified items. You can revoke access at any time.' : 'Enable a secure link to share verified achievements with employers or admissions teams.'}</p></div>
            <ActionButton onClick={toggleSharing} disabled={busy}>{busy ? 'Updating…' : portfolio.share_enabled ? 'Revoke link' : 'Create share link'}</ActionButton>
            <button className="button button-secondary" onClick={downloadResume} disabled={resumeBusy}>
              {resumeBusy ? 'Preparing resume…' : 'Download resume'}
            </button>
            {shareUrl && <div className="share-url"><a href={shareUrl} target="_blank" rel="noreferrer">{shareUrl}</a><button className="text-button" onClick={copyShareUrl}>Copy link</button></div>}
          </div>
          <form className="panel portfolio-share" onSubmit={loadGithubProfile}>
            <div>
              <strong>Optional GitHub profile stats</strong>
              <p className="muted">Fetch public profile counts from GitHub. Your username is not added to your profile; the public result may be temporarily cached for 15 minutes and is not verified evidence.</p>
            </div>
            <label>
              GitHub username
              <input name="github_username" maxLength="39" autoComplete="off" placeholder="your-github-username" />
            </label>
            <button className="button button-secondary" type="submit" disabled={githubBusy}>
              {githubBusy ? 'Loading…' : 'Fetch public stats'}
            </button>
            {githubProfile && (
              <div className="share-url">
                <strong>{githubProfile.name || githubProfile.login}</strong>
                <span>{githubProfile.public_repos} public repositories</span>
                <span>{githubProfile.followers} followers</span>
                <a href={githubProfile.html_url} target="_blank" rel="noreferrer">View GitHub profile</a>
              </div>
            )}
          </form>
          <div className="panel portfolio-share">
            <div>
              <strong>LinkedIn profile</strong>
              <p className="muted">Connect your LinkedIn account with consent. VeriSphere stores your display name and profile photo only; OAuth tokens are not retained.</p>
            </div>
            {linkedInProfile?.connected && (
              <div className="share-url">
                {linkedInProfile.picture_url && <img className="linkedin-avatar" src={linkedInProfile.picture_url} alt="" width="40" height="40" referrerPolicy="no-referrer" />}
                <span>{linkedInProfile.name || 'Profile connected'}</span>
              </div>
            )}
            <button className="button button-secondary" type="button" onClick={connectLinkedIn} disabled={linkedInBusy}>
              <Globe size={16} />{linkedInBusy ? 'Connecting…' : linkedInProfile?.connected ? 'Reconnect LinkedIn' : 'Connect LinkedIn'}
            </button>
          </div>
          <PortfolioContents portfolio={portfolio} token={token} shareToken={shareToken} />
        </>
      )}
    </section>
  )
}

function PortfolioContents({ portfolio, publicView = false, token, shareToken }) {
  return (
    <div className={`portfolio-document${publicView ? ' portfolio-public' : ''}`}>
      {publicView && <div className="portfolio-print-action"><button className="button button-secondary" onClick={() => window.print()}>Print / Save as PDF</button></div>}
      <header className="portfolio-header">
        <span className="eyebrow">VERISPHERE · VERIFIED STUDENT PORTFOLIO</span>
        <h1>{portfolio.student.name}</h1>
        <p>{portfolio.student.course || 'Student'}{portfolio.student.semester ? ` · Semester ${portfolio.student.semester}` : ''}</p>
      </header>
      <section>
        <h2>Verified academic milestones <span className="soft-chip">{portfolio.academic_milestones.length}</span></h2>
        {portfolio.academic_milestones.length ? <div className="record-list">{portfolio.academic_milestones.map((milestone, index) => <article className="record-card" key={`${milestone.subject}-${milestone.title}-${index}`}><span className="eyebrow">{milestone.subject} · Semester {milestone.semester}</span><h3>{milestone.title}</h3><p>Verified milestone</p>{milestone.evidence_file_id && (publicView ? <a href={getSharedEvidenceUrl(shareToken, milestone.evidence_file_id)} target="_blank" rel="noreferrer">View verified file</a> : <EvidenceLink token={token} evidenceId={milestone.evidence_file_id} />)}</article>)}</div> : <p className="muted">No academic milestones have been verified yet.</p>}
      </section>
      <section>
        <h2>Verified activities <span className="soft-chip">{portfolio.activities.length}</span></h2>
        {portfolio.activities.length ? <div className="record-list">{portfolio.activities.map((activity) => <RecordCard key={activity.title + activity.achieved_on} activity={activity} token={publicView ? undefined : token} publicShareToken={publicView ? shareToken : undefined} />)}</div> : <p className="muted">No activities have been verified yet.</p>}
      </section>
      <footer className="portfolio-footer">This portfolio displays records verified by faculty in VeriSphere.</footer>
    </div>
  )
}

export function SharedPortfolioPage({ shareToken }) {
  const [portfolio, setPortfolio] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    getSharedPortfolio(shareToken).then(setPortfolio).catch((requestError) => setError(requestError.message))
  }, [shareToken])

  if (error) return <main className="shared-portfolio-error"><h1>Portfolio unavailable</h1><p>{error}</p><a href="/">Go to VeriSphere</a></main>
  if (!portfolio) return <main className="shared-portfolio-error">Loading verified portfolio…</main>
  return <main className="shared-portfolio"><PortfolioContents portfolio={portfolio} publicView shareToken={shareToken} /></main>
}

export function ActivityReports({ token }) {
  const [report, setReport] = useState(null)
  const [academicReport, setAcademicReport] = useState(null)
  const [error, setError] = useState('')
  const [downloading, setDownloading] = useState(false)

  useEffect(() => {
    Promise.all([getActivityReport(token), getAcademicReport(token)])
      .then(([activityData, academicData]) => {
        setReport(activityData)
        setAcademicReport(academicData)
      })
      .catch((requestError) => setError(requestError.message))
  }, [token])

  const downloadCsv = () => {
    if (!report || !academicReport) return
    const rows = [
      ['Metric', 'Category or status', 'Count'],
      ['Activities by category', '', ''],
      ...report.by_category.map((item) => ['Category', labels[item.category] || item.category, item.count]),
      ['Activities by status', '', ''],
      ...report.by_status.map((item) => ['Status', item.status.replaceAll('_', ' '), item.count]),
      ['Total activities', '', report.total_activities],
      ['Attendance and assessment records', '', ''],
      ...academicReport.attendance.map((row) => [
        'Attendance',
        `${row.course} · ${row.subject_code} ${row.subject}`,
        `present ${row.present}; absent ${row.absent}; excused ${row.excused}; attendance ${row.attendance_percentage ?? 'not available'}%`,
      ]),
      ...academicReport.assessments.map((row) => [
        'Assessments',
        `${row.course} · ${row.subject_code} ${row.subject}`,
        `${row.assessments_recorded} records; average ${row.average_percentage ?? 'not available'}%`,
      ]),
    ]
    const csv = rows.map((row) => row.map(csvCell).join(',')).join('\r\n')
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = url
    link.download = 'verisphere-activity-report.csv'
    link.click()
    window.setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  const downloadWorkbook = async (type) => {
    setDownloading(true)
    setError('')
    try {
      const blob = type === 'activities'
        ? await downloadActivityReportWorkbook(token)
        : await downloadAcademicReportWorkbook(token)
      saveBlob(blob, `verisphere-${type}.xlsx`)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setDownloading(false)
    }
  }

  return (
    <section>
      <div className="page-heading">
        <div><span className="eyebrow">INSTITUTIONAL REPORTING</span><h1>Activity analytics</h1><p className="muted">A consolidated view of recorded achievements and verification status for internal review and accreditation preparation.</p></div>
        {report && academicReport && (
          <div className="report-download-actions">
            <button className="button button-secondary" onClick={downloadCsv}>Download CSV</button>
            <button className="button button-secondary" disabled={downloading} onClick={() => downloadWorkbook('activities')}>
              {downloading ? 'Preparing…' : 'Download activities XLSX'}
            </button>
            <button className="button button-secondary" disabled={downloading} onClick={() => downloadWorkbook('academics')}>
              {downloading ? 'Preparing…' : 'Download academics XLSX'}
            </button>
          </div>
        )}
      </div>
      <ErrorMessage message={error} />
      {report && (
        <>
          <div className="metric-grid report-metrics">
            <article className="metric-card"><div className="metric-card-top">Activities recorded</div><strong className="metric-value">{report.total_activities}</strong></article>
            <article className="metric-card"><div className="metric-card-top">Verified</div><strong className="metric-value">{report.verified_activities}</strong></article>
            <article className="metric-card"><div className="metric-card-top">Awaiting review</div><strong className="metric-value">{report.pending_verification}</strong></article>
          </div>
          <div className="report-tables">
            <ReportTable title="Achievements by category" rows={report.by_category.map(({ category, count }) => [labels[category] || category, count])} />
            <ReportTable title="Verification status" rows={report.by_status.map(({ status, count }) => [status.replaceAll('_', ' '), count])} />
          </div>
          {academicReport && (
            <div className="report-tables academic-report-tables">
              <AcademicReportTable
                title="Attendance by subject"
                rows={academicReport.attendance.map((row) => [
                  `${row.course} · ${row.subject_code} ${row.subject}`,
                  `${row.present} present · ${row.absent} absent · ${row.excused} excused`,
                  row.attendance_percentage === null ? '—' : `${row.attendance_percentage}%`,
                ])}
              />
              <AcademicReportTable
                title="Assessment averages"
                rows={academicReport.assessments.map((row) => [
                  `${row.course} · ${row.subject_code} ${row.subject}`,
                  `${row.assessments_recorded} records`,
                  row.average_percentage === null ? '—' : `${row.average_percentage}%`,
                ])}
              />
            </div>
          )}
        </>
      )}
    </section>
  )
}

function ReportTable({ title, rows }) {
  return <section className="panel report-table"><h2>{title}</h2>{rows.length ? rows.map(([label, value]) => <div className="report-row" key={label}><span>{label}</span><strong>{value}</strong></div>) : <p className="muted">No records yet.</p>}</section>
}

function AcademicReportTable({ title, rows }) {
  return <section className="panel report-table"><h2>{title}</h2>{rows.length ? <div className="table-scroll"><table><thead><tr><th>Course &amp; subject</th><th>Summary</th><th>Rate</th></tr></thead><tbody>{rows.map(([subject, summary, rate]) => <tr key={subject}><td>{subject}</td><td>{summary}</td><td>{rate}</td></tr>)}</tbody></table></div> : <p className="muted">No records yet.</p>}</section>
}
