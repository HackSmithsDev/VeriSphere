import { useEffect, useMemo, useState } from 'react'
import {
  getAcademicOptions,
  getAcademicRecords,
  saveAssessmentMark,
  saveAttendance,
} from '../../api/records'
import { ActionButton } from '../ui/ActionButton'

function localDate() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
}

export function AcademicWorkspace({ token, staff = false }) {
  const [options, setOptions] = useState({ students: [], subjects: [] })
  const [records, setRecords] = useState({ attendance: [], marks: [] })
  const [studentId, setStudentId] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        if (staff) {
          const data = await getAcademicOptions(token)
          if (!cancelled) {
            setOptions(data)
            setStudentId(data.students[0] ? String(data.students[0].id) : '')
          }
        } else {
          const data = await getAcademicRecords(token)
          if (!cancelled) setRecords(data)
        }
      } catch (requestError) {
        if (!cancelled) setError(requestError.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [staff, token])

  const selectedStudent = options.students.find((student) => String(student.id) === studentId)
  const subjects = useMemo(
    () => selectedStudent
      ? options.subjects.filter((subject) => subject.course_id === selectedStudent.course_id)
      : [],
    [options.subjects, selectedStudent],
  )

  const handleEntry = async (event, kind) => {
    event.preventDefault()
    const formElement = event.currentTarget
    const form = new FormData(formElement)
    setBusy(true)
    setError('')
    setNotice('')
    try {
      if (kind === 'attendance') {
        await saveAttendance(token, {
          student_id: Number(form.get('student_id')),
          subject_id: Number(form.get('subject_id')),
          attendance_date: form.get('record_date'),
          status: form.get('status'),
        })
        setNotice('Attendance saved. An existing record for that student, subject, and date was updated.')
      } else {
        await saveAssessmentMark(token, {
          student_id: Number(form.get('student_id')),
          subject_id: Number(form.get('subject_id')),
          title: form.get('title'),
          score: Number(form.get('score')),
          maximum_score: Number(form.get('maximum_score')),
          assessment_date: form.get('record_date'),
        })
        setNotice('Assessment mark saved.')
        formElement.reset()
      }
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusy(false)
    }
  }

  if (staff) {
    return (
      <section>
        <div className="page-heading">
          <div><span className="eyebrow">CONTINUOUS ASSESSMENT</span><h1>Attendance &amp; marks</h1><p className="muted">Record per-student, per-subject attendance and assessment results.</p></div>
        </div>
        {error && <div className="alert alert-error" role="alert">{error}</div>}
        {notice && <div className="alert alert-success" role="status">{notice}</div>}
        {loading ? <p className="muted">Loading course and student records…</p> : !options.students.length || !options.subjects.length ? <p className="muted">Add students and subjects to the curriculum before recording academic data.</p> : (
          <>
            <div className="panel activity-form">
              <h2>Record attendance</h2>
              <form className="academic-entry-form" onSubmit={(event) => handleEntry(event, 'attendance')}>
                <label>Student<select name="student_id" value={studentId} onChange={(event) => setStudentId(event.target.value)} required>{options.students.map((student) => <option key={student.id} value={student.id}>{student.name}</option>)}</select></label>
                <label>Subject<select name="subject_id" required>{subjects.map((subject) => <option key={subject.id} value={subject.id}>{subject.code} · {subject.name}</option>)}</select></label>
                <label>Date<input name="record_date" type="date" defaultValue={localDate()} required /></label>
                <label>Status<select name="status" defaultValue="present"><option value="present">Present</option><option value="absent">Absent</option><option value="excused">Excused</option></select></label>
                <ActionButton type="submit" disabled={busy}>Save attendance</ActionButton>
              </form>
            </div>
            <div className="panel activity-form">
              <h2>Record assessment mark</h2>
              <form className="academic-entry-form" onSubmit={(event) => handleEntry(event, 'marks')}>
                <label>Student<select name="student_id" value={studentId} onChange={(event) => setStudentId(event.target.value)} required>{options.students.map((student) => <option key={student.id} value={student.id}>{student.name}</option>)}</select></label>
                <label>Subject<select name="subject_id" required>{subjects.map((subject) => <option key={subject.id} value={subject.id}>{subject.code} · {subject.name}</option>)}</select></label>
                <label>Assessment<input name="title" required minLength="2" maxLength="255" placeholder="Quiz 1, lab practical…" /></label>
                <label>Date<input name="record_date" type="date" defaultValue={localDate()} required /></label>
                <label>Score<input name="score" type="number" min="0" step="0.01" required /></label>
                <label>Maximum score<input name="maximum_score" type="number" min="0.01" step="0.01" required /></label>
                <ActionButton type="submit" disabled={busy}>Save mark</ActionButton>
              </form>
            </div>
          </>
        )}
      </section>
    )
  }

  return (
    <section>
      <div className="page-heading">
        <div><span className="eyebrow">ACADEMIC RECORD</span><h1>Attendance &amp; marks</h1><p className="muted">Review your recorded attendance and continuous assessment results by subject.</p></div>
      </div>
      {error && <div className="alert alert-error" role="alert">{error}</div>}
      {loading ? <p className="muted">Loading your academic record…</p> : (
        <div className="academic-record-grid">
          <section className="panel report-table">
            <h2>Attendance</h2>
            {records.attendance.length ? <div className="table-scroll"><table><thead><tr><th>Subject</th><th>Present</th><th>Absent</th><th>Excused</th><th>Attendance</th></tr></thead><tbody>{records.attendance.map((row) => <tr key={row.subject_id}><td>{row.subject_code} · {row.subject}</td><td>{row.present}</td><td>{row.absent}</td><td>{row.excused}</td><td>{row.percentage === null ? '—' : `${row.percentage}%`}</td></tr>)}</tbody></table></div> : <p className="muted">No attendance has been recorded yet.</p>}
          </section>
          <section className="panel report-table">
            <h2>Continuous assessment</h2>
            {records.marks.length ? <div className="table-scroll"><table><thead><tr><th>Assessment</th><th>Subject</th><th>Score</th><th>Date</th></tr></thead><tbody>{records.marks.map((mark) => <tr key={mark.id}><td>{mark.title}</td><td>{mark.subject_code} · {mark.subject}</td><td>{mark.score} / {mark.maximum_score} ({mark.percentage}%)</td><td>{mark.assessment_date}</td></tr>)}</tbody></table></div> : <p className="muted">No assessment marks have been recorded yet.</p>}
          </section>
        </div>
      )}
    </section>
  )
}
