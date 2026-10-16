import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  Bell,
  BookOpen,
  Check,
  CheckCircle2,
  CircleHelp,
  Clock3,
  FileCheck2,
  FileText,
  GraduationCap,
  LayoutDashboard,
  LogOut,
  Menu,
  Plus,
  Search,
  ShieldCheck,
  Sparkles,
  Users,
  X,
} from 'lucide-react'
import { getAdminOverview, getAdminUsers, createTeacher } from './api/admin'
import { AssistantChat } from './components/assistant/AssistantChat'
import { getCurrentUser, login, logout, register } from './api/auth'
import { getAnnouncements, getCourses } from './api/guest'
import { getStudentDashboard, getMilestones, submitMilestone } from './api/student'
import { getTeacherDashboard, getSubmissions, reviewSubmission } from './api/teacher'
import { ActionButton } from './components/ui/ActionButton'
import { Badge } from './components/ui/Badge'
import { Card } from './components/ui/Card'
import HeroScene from './components/visual/HeroScene'
import './App.css'

const TOKEN_KEY = 'verisphere_token'

async function loadWorkspace(token, role) {
  if (role === 'student') {
    const [dashboard, milestones] = await Promise.all([
      getStudentDashboard(token),
      getMilestones(token),
    ])
    return { dashboard, milestones }
  }
  if (role === 'teacher') {
    const [dashboard, submissions] = await Promise.all([
      getTeacherDashboard(token),
      getSubmissions(token),
    ])
    return { dashboard, submissions }
  }
  const [dashboard, users] = await Promise.all([
    getAdminOverview(token),
    getAdminUsers(token),
  ])
  return { dashboard, users }
}

function App() {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY))
  const [user, setUser] = useState(null)
  const [workspace, setWorkspace] = useState({})
  const [page, setPage] = useState('overview')
  const [authMode, setAuthMode] = useState(null)
  const [authBusy, setAuthBusy] = useState(false)
  const [loading, setLoading] = useState(Boolean(token))
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [courses, setCourses] = useState([])
  const [activeMilestone, setActiveMilestone] = useState(null)
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')

  const refreshWorkspace = useCallback(async (activeToken, role) => {
    const result = await loadWorkspace(activeToken, role)
    setWorkspace(result)
    return result
  }, [])

  useEffect(() => {
    if (!token) return
    let cancelled = false
    getCurrentUser(token)
      .then(async (currentUser) => {
        const result = await loadWorkspace(token, currentUser.role)
        if (!cancelled) {
          setUser(currentUser)
          setWorkspace(result)
          setPage('overview')
          setError('')
        }
      })
      .catch((requestError) => {
        if (!cancelled) {
          logout()
          setToken(null)
          setUser(null)
          setError(requestError.message)
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [token])

  useEffect(() => {
    if (authMode !== 'register') return
    getCourses()
      .then(setCourses)
      .catch((requestError) => setError(requestError.message))
  }, [authMode])

  const navItems = useMemo(() => {
    if (user?.role === 'teacher') {
      return [
        ['overview', 'Overview', LayoutDashboard],
        ['reviews', 'Review submissions', FileCheck2],
        ['assistant', 'AI assistant', Sparkles],
        ['announcements', 'Announcements', Bell],
      ]
    }
    if (user?.role === 'admin') {
      return [
        ['overview', 'Overview', LayoutDashboard],
        ['accounts', 'Accounts', Users],
        ['announcements', 'Announcements', Bell],
      ]
    }
    return [
      ['overview', 'Overview', LayoutDashboard],
      ['learning', 'Learning path', BookOpen],
      ['assistant', 'AI assistant', Sparkles],
      ['announcements', 'Announcements', Bell],
      ['profile', 'My profile', GraduationCap],
    ]
  }, [user?.role])

  const handleAuth = async (event) => {
    event.preventDefault()
    setAuthBusy(true)
    setError('')
    const form = new FormData(event.currentTarget)
    const details = Object.fromEntries(form.entries())
    try {
      const result =
        authMode === 'register'
          ? await register({
              ...details,
              course_id: Number(details.course_id),
            })
          : await login({ email: details.email, password: details.password })
      localStorage.setItem(TOKEN_KEY, result.access_token)
      setLoading(true)
      setUser(result.user)
      setToken(result.access_token)
      setAuthMode(null)
      setNotice(authMode === 'register' ? 'Your account is ready.' : 'Welcome back.')
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setAuthBusy(false)
    }
  }

  const signOut = () => {
    logout()
    setLoading(false)
    setToken(null)
    setUser(null)
    setWorkspace({})
    setPage('overview')
    setNotice('You have signed out.')
  }

  const sendSubmission = async (event) => {
    event.preventDefault()
    if (!activeMilestone) return
    const form = new FormData(event.currentTarget)
    try {
      await submitMilestone(token, activeMilestone.id, {
        summary: form.get('summary'),
        proof_url: form.get('proof_url') || null,
      })
      await refreshWorkspace(token, user.role)
      setActiveMilestone(null)
      setNotice('Evidence sent to your teacher for review.')
    } catch (requestError) {
      setError(requestError.message)
    }
  }

  const approveSubmission = async (submission, decision) => {
    const feedback =
      decision === 'needs_revision'
        ? window.prompt('What should the student improve?', '') ?? null
        : ''
    if (feedback === null) return
    try {
      await reviewSubmission(token, submission.id, { decision, feedback })
      await refreshWorkspace(token, user.role)
      setNotice(
        decision === 'verified'
          ? 'Submission verified.'
          : 'Submission returned with feedback.',
      )
    } catch (requestError) {
      setError(requestError.message)
    }
  }

  const createFaculty = async (event) => {
    event.preventDefault()
    const formElement = event.currentTarget
    const form = new FormData(formElement)
    const values = Object.fromEntries(form.entries())
    try {
      await createTeacher(token, values)
      await refreshWorkspace(token, user.role)
      formElement.reset()
      setNotice('Faculty account created.')
    } catch (requestError) {
      setError(requestError.message)
    }
  }

  const navigate = (nextPage) => {
    setPage(nextPage)
    setMobileNavOpen(false)
    setError('')
  }

  if (loading) {
    return (
      <div className="boot-screen">
        <div className="brand-mark"><ShieldCheck size={23} /></div>
        <span>Preparing your workspace</span>
      </div>
    )
  }

  if (!user) {
    if (authMode) {
      return (
        <main className="auth-screen">
          <div className="auth-aside">
            <a className="brand brand-light" href="#" onClick={(event) => { event.preventDefault(); setAuthMode(null); setError('') }}>
              <span className="brand-mark"><ShieldCheck size={22} /></span>
              <span>VeriSphere</span>
            </a>
            <div className="auth-aside-copy">
              <span className="eyebrow">PROGRESS, WITH PROOF</span>
              <h1>Every milestone tells a story.</h1>
              <p>Keep your learning, evidence, and feedback connected from day one.</p>
            </div>
            <div className="auth-aside-foot">A clearer view of the work behind the result.</div>
          </div>
          <section className="auth-main">
            <button className="icon-button auth-close" aria-label="Close sign in" onClick={() => { setAuthMode(null); setError('') }}>
              <X size={19} />
            </button>
            <div className="auth-form-wrap">
              <div className="mobile-auth-brand">
                <span className="brand-mark"><ShieldCheck size={22} /></span>
                <strong>VeriSphere</strong>
              </div>
              <span className="eyebrow">{authMode === 'register' ? 'GET STARTED' : 'YOUR CAMPUS, IN SYNC'}</span>
              <h2>{authMode === 'register' ? 'Create your account' : 'Welcome back'}</h2>
              <p className="muted">
                {authMode === 'register'
                  ? 'Start tracking your academic progress today.'
                  : 'Sign in to pick up where you left off.'}
              </p>
              {error && <div className="alert alert-error" role="alert">{error}</div>}
              <form className="auth-form" onSubmit={handleAuth}>
                {authMode === 'register' && (
                  <>
                    <div className="field-row">
                      <label>First name<input name="first_name" autoComplete="given-name" required maxLength="100" /></label>
                      <label>Last name<input name="last_name" autoComplete="family-name" required maxLength="100" /></label>
                    </div>
                    <label>Course
                      <select name="course_id" required defaultValue="">
                        <option value="" disabled>Select your course</option>
                        {courses.map((course) => (
                          <option key={course.id} value={course.id}>{course.name}</option>
                        ))}
                      </select>
                    </label>
                  </>
                )}
                <label>Email address<input name="email" type="email" autoComplete="email" required maxLength="255" /></label>
                <label>Password<input name="password" type="password" autoComplete={authMode === 'register' ? 'new-password' : 'current-password'} required minLength={authMode === 'register' ? 8 : 1} maxLength="128" /></label>
                {authMode === 'register' && <p className="field-hint">Use at least 8 characters. Faculty accounts are provided by your administrator.</p>}
                <ActionButton className="button-full" type="submit" disabled={authBusy || (authMode === 'register' && courses.length === 0)}>
                  {authBusy ? 'Please wait…' : authMode === 'register' ? 'Create account' : 'Sign in'}
                  {!authBusy && <ArrowRight size={17} />}
                </ActionButton>
              </form>
              <p className="auth-switch">
                {authMode === 'register' ? 'Already have an account?' : 'New to VeriSphere?'}{' '}
                <button onClick={() => { setAuthMode(authMode === 'register' ? 'login' : 'register'); setError('') }}>
                  {authMode === 'register' ? 'Sign in' : 'Create an account'}
                </button>
              </p>
            </div>
          </section>
        </main>
      )
    }
    return <Landing onSignIn={() => { setAuthMode('login'); setError('') }} onSignUp={() => { setAuthMode('register'); setError('') }} error={error} />
  }

  const fullName = [user.first_name, user.last_name].filter(Boolean).join(' ') || user.email
  const initials = fullName.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase()
  const roleLabel = user.role === 'admin' ? 'Administrator' : user.role === 'teacher' ? 'Faculty' : 'Student'

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileNavOpen ? 'sidebar-open' : ''}`}>
        <a className="brand" href="#" onClick={(event) => { event.preventDefault(); navigate('overview') }}>
          <span className="brand-mark"><ShieldCheck size={22} /></span>
          <span>VeriSphere</span>
        </a>
        <div className="workspace-label">WORKSPACE</div>
        <nav className="side-nav" aria-label="Main navigation">
          {navItems.map(([id, label, Icon]) => (
            <button key={id} className={`nav-item ${page === id ? 'active' : ''}`} onClick={() => navigate(id)}>
              <Icon size={18} strokeWidth={1.8} />
              <span>{label}</span>
              {id === 'reviews' && workspace.submissions?.length > 0 && <span className="nav-count">{workspace.submissions.length}</span>}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="help-card">
            <div className="help-icon"><CircleHelp size={17} /></div>
            <div><strong>Need a hand?</strong><span>We’re here to help.</span></div>
            <ArrowUpRight size={15} />
          </div>
          <div className="sidebar-user">
            <div className="avatar">{initials}</div>
            <div className="sidebar-user-copy"><strong>{fullName}</strong><span>{roleLabel}</span></div>
            <button className="icon-button signout-button" onClick={signOut} title="Sign out" aria-label="Sign out"><LogOut size={17} /></button>
          </div>
        </div>
      </aside>

      {mobileNavOpen && <button className="mobile-scrim" aria-label="Close navigation" onClick={() => setMobileNavOpen(false)} />}
      <main className="main-area">
        <header className="topbar">
          <div className="topbar-left">
            <button className="icon-button mobile-menu" aria-label="Open navigation" onClick={() => setMobileNavOpen(true)}><Menu size={20} /></button>
            <div className="breadcrumb">Workspace <span>/</span> <strong>{navItems.find(([id]) => id === page)?.[1] || 'Overview'}</strong></div>
          </div>
          <div className="topbar-actions">
            <label className="search-box">
              <Search size={16} />
              <input aria-label="Search this page" placeholder="Search…" value={searchTerm} onChange={(event) => setSearchTerm(event.target.value)} />
              <kbd>⌘ K</kbd>
            </label>
            <button className="icon-button notification-button" aria-label="Notifications"><Bell size={18} /><i /></button>
            <div className="topbar-avatar">{initials}</div>
          </div>
        </header>

        <div className="page-content">
          {notice && <div className="alert alert-success" role="status"><CheckCircle2 size={17} />{notice}<button aria-label="Dismiss" onClick={() => setNotice('')}><X size={15} /></button></div>}
          {error && <div className="alert alert-error" role="alert">{error}<button aria-label="Dismiss" onClick={() => setError('')}><X size={15} /></button></div>}
          {page === 'overview' && (
            <Overview
              user={user}
              fullName={fullName}
              workspace={workspace}
              onNavigate={navigate}
            />
          )}
          {page === 'learning' && (
            <LearningPath
              milestones={workspace.milestones || []}
              searchTerm={searchTerm}
              onSubmit={setActiveMilestone}
            />
          )}
          {page === 'reviews' && (
            <ReviewQueue
              submissions={workspace.submissions || []}
              searchTerm={searchTerm}
              onReview={approveSubmission}
            />
          )}
          {page === 'accounts' && (
            <Accounts
              users={workspace.users || []}
              searchTerm={searchTerm}
              onCreateTeacher={createFaculty}
            />
          )}
          {page === 'announcements' && <Announcements />}
          {page === 'profile' && <Profile user={user} fullName={fullName} />}
          {page === 'assistant' && <AssistantChat role={user.role} token={token} />}
        </div>
      </main>

      {activeMilestone && (
        <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setActiveMilestone(null) }}>
          <section className="modal-card" role="dialog" aria-modal="true" aria-labelledby="submission-title">
            <div className="modal-heading">
              <div><span className="eyebrow">MILESTONE EVIDENCE</span><h2 id="submission-title">Submit your work</h2></div>
              <button className="icon-button" aria-label="Close dialog" onClick={() => setActiveMilestone(null)}><X size={18} /></button>
            </div>
            <p className="muted modal-description">{activeMilestone.title} · {activeMilestone.subject}</p>
            <form className="auth-form" onSubmit={sendSubmission}>
              <label>What did you complete?<textarea name="summary" rows="4" minLength="10" maxLength="4000" placeholder="Describe your work and what you learned…" required /></label>
              <label>Link to evidence <span className="optional">(optional)</span><input name="proof_url" type="url" placeholder="https://…" maxLength="1000" /></label>
              <div className="modal-actions">
                <button type="button" className="button button-quiet" onClick={() => setActiveMilestone(null)}>Cancel</button>
                <button className="button button-primary" type="submit">Send for review <ArrowRight size={16} /></button>
              </div>
            </form>
          </section>
        </div>
      )}
    </div>
  )
}

function Landing({ onSignIn, onSignUp, error }) {
  return (
    <main className="landing">
      <header className="landing-nav">
        <a className="brand" href="#"><span className="brand-mark"><ShieldCheck size={22} /></span><span>VeriSphere</span></a>
        <div className="landing-links"><a href="#how-it-works">How it works</a><a href="#for-campus">For your campus</a></div>
        <div className="landing-actions"><ActionButton variant="quiet" onClick={onSignIn}>Sign in</ActionButton><ActionButton onClick={onSignUp}>Get started <ArrowRight size={16} /></ActionButton></div>
      </header>
      {error && <div className="landing-alert alert alert-error" role="alert">{error}</div>}
      <section className="hero-section">
        <div className="hero-copy">
          <span className="eyebrow"><span className="eyebrow-dot" /> A BETTER WAY TO SEE PROGRESS</span>
          <h1>Learning has a journey.<br /><em>Make it visible.</em></h1>
          <p>VeriSphere brings academic milestones, real evidence, and meaningful feedback together — so every step forward counts.</p>
          <div className="hero-actions"><ActionButton className="button-large" onClick={onSignUp}>Build your learning record <ArrowRight size={17} /></ActionButton><a className="text-link" href="#how-it-works">See how it works <ArrowDownRight size={16} /></a></div>
          <div className="hero-proof"><div className="proof-avatars"><span>AR</span><span>SM</span><span>JK</span></div><span>Built around progress, not just grades</span></div>
        </div>
        <div className="hero-visual" aria-label="Learning dashboard preview">
          <HeroScene />
          <div className="preview-card">
            <div className="preview-top"><div><span className="preview-label">YOUR LEARNING JOURNEY</span><strong>Semester overview</strong></div><span className="preview-menu">···</span></div>
            <div className="preview-chart"><div className="chart-ring"><div><strong>72%</strong><span>complete</span></div></div><div className="chart-legend"><span><i className="legend-dot purple" />Verified <b>18</b></span><span><i className="legend-dot orange" />In review <b>4</b></span><span><i className="legend-dot grey" />To explore <b>3</b></span></div></div>
            <div className="preview-divider" />
            <div className="preview-activity"><div className="activity-symbol symbol-green"><Check size={15} /></div><div><strong>Python Fundamentals</strong><span>Evidence verified · just now</span></div><span className="preview-check"><CheckCircle2 size={17} /></span></div>
            <div className="preview-activity"><div className="activity-symbol symbol-lilac"><FileText size={15} /></div><div><strong>Data Structures Portfolio</strong><span>Submitted for review · 2h ago</span></div><span className="preview-pending"><Clock3 size={15} /></span></div>
            <div className="preview-activity"><div className="activity-symbol symbol-peach"><Sparkles size={15} /></div><div><strong>Web Application Project</strong><span>Ready when you are</span></div><span className="preview-arrow"><ArrowUpRight size={15} /></span></div>
          </div>
          <div className="float-note"><span className="float-icon"><ShieldCheck size={17} /></span><span><strong>Verified progress</strong><small>Evidence, not just marks</small></span><CheckCircle2 className="float-check" size={17} /></div>
          <div className="hero-sparkle sparkle-one">✳</div><div className="hero-sparkle sparkle-two">✳</div>
        </div>
      </section>
      <section className="trust-strip" id="for-campus"><span>ONE SHARED SPACE FOR</span><div><span><GraduationCap size={17} /> Student growth</span><span><BookOpen size={16} /> Faculty feedback</span><span><ShieldCheck size={16} /> Verified learning</span><span><Users size={17} /> Campus alignment</span></div></section>
      <section className="how-section" id="how-it-works"><div className="section-intro"><span className="eyebrow">A MORE COMPLETE PICTURE</span><h2>Good work deserves<br />to be seen.</h2><p>Turn the work between exams into a clear, trusted record of what students can do.</p></div><div className="feature-grid"><article className="feature-card"><span className="feature-number">01</span><div className="feature-icon feature-violet"><BookOpen size={19} /></div><h3>Follow the learning path</h3><p>See curriculum milestones and know exactly what comes next.</p></article><article className="feature-card"><span className="feature-number">02</span><div className="feature-icon feature-orange"><FileCheck2 size={19} /></div><h3>Share real evidence</h3><p>Attach projects and explain your work, not only the outcome.</p></article><article className="feature-card"><span className="feature-number">03</span><div className="feature-icon feature-green"><ShieldCheck size={19} /></div><h3>Get meaningful feedback</h3><p>Faculty review turns effort into progress you can build on.</p></article></div></section>
      <footer className="landing-footer"><a className="brand" href="#"><span className="brand-mark"><ShieldCheck size={20} /></span><span>VeriSphere</span></a><span>Make every step count.</span><span>© 2026 VeriSphere</span></footer>
    </main>
  )
}

function Overview({ user, fullName, workspace, onNavigate }) {
  const greeting = new Date().getHours() < 12 ? 'Good morning' : new Date().getHours() < 18 ? 'Good afternoon' : 'Good evening'
  const student = user.role === 'student'
  const teacher = user.role === 'teacher'
  const stats = workspace.dashboard?.stats || {}
  const activity = workspace.dashboard?.recent_activity || []
  const metricCards = student
    ? [
        { label: 'Milestones completed', value: stats.verified_milestones ?? '—', icon: CheckCircle2, tone: 'green', hint: 'Verified by faculty' },
        { label: 'Awaiting review', value: stats.pending_reviews ?? '—', icon: Clock3, tone: 'orange', hint: 'Your work is in the queue' },
        { label: 'Learning progress', value: `${stats.completion_percent ?? 0}%`, icon: ArrowUpRight, tone: 'purple', hint: 'Keep moving forward' },
      ]
    : teacher
      ? [
          { label: 'Needs your review', value: stats.pending_reviews ?? '—', icon: FileCheck2, tone: 'orange', hint: 'Student submissions' },
          { label: 'Students supported', value: stats.students ?? '—', icon: Users, tone: 'purple', hint: 'Across your campus' },
          { label: 'Review queue', value: workspace.submissions?.length ?? '—', icon: Clock3, tone: 'green', hint: 'Ready for your feedback' },
        ]
      : [
          { label: 'Total accounts', value: stats.users ?? '—', icon: Users, tone: 'purple', hint: 'Across your campus' },
          { label: 'Student community', value: stats.students ?? '—', icon: GraduationCap, tone: 'green', hint: 'Enrolled learners' },
          { label: 'Reviews pending', value: stats.pending_reviews ?? '—', icon: FileCheck2, tone: 'orange', hint: `${stats.teachers ?? 0} faculty accounts` },
        ]

  return (
    <section>
      <div className="welcome-row">
        <div><span className="eyebrow">{greeting.toUpperCase()}</span><h1>{fullName.split(' ')[0]}<span className="welcome-period">.</span></h1><p className="muted">{student ? workspace.dashboard?.student?.course || 'Your academic workspace is ready.' : teacher ? 'Here’s what is happening with your students.' : 'A snapshot of your academic community.'}</p></div>
        <div className="welcome-date"><span className="date-dot" />{new Intl.DateTimeFormat('en', { weekday: 'long', month: 'long', day: 'numeric' }).format(new Date())}</div>
      </div>
      <div className="metric-grid">
        {metricCards.map(({ label, value, icon: Icon, tone, hint }) => (
          <article className="metric-card" key={label}><div className="metric-card-top"><span>{label}</span><span className={`metric-icon ${tone}`}><Icon size={17} /></span></div><strong className="metric-value">{value}</strong><span className="metric-hint">{hint}</span></article>
        ))}
      </div>
      <div className="dashboard-grid">
        <Card className="activity-panel">
          <div className="panel-heading"><div><span className="eyebrow">THE LATEST</span><h2>{student ? 'Your recent activity' : teacher ? 'Submissions to review' : 'Campus snapshot'}</h2></div><button className="text-button" onClick={() => onNavigate(student ? 'learning' : teacher ? 'reviews' : 'accounts')}>View all <ArrowRight size={15} /></button></div>
          {student ? activity.length > 0 ? <div className="activity-list">{activity.map((item) => <ActivityRow key={item.id} item={item} />)}</div> : <EmptyPanel icon={BookOpen} title="Your learning path is ready" text="Explore your milestones and submit evidence as you complete them." action="View learning path" onClick={() => onNavigate('learning')} /> : teacher ? workspace.submissions?.length ? <div className="activity-list">{workspace.submissions.slice(0, 4).map((item) => <div className="review-row" key={item.id}><div className="avatar avatar-small">{item.student.split(' ').map((part) => part[0]).join('').slice(0, 2)}</div><div className="activity-copy"><strong>{item.student}</strong><span>{item.title} · {item.subject}</span></div><span className="status-pill status-pending">Awaiting review</span></div>)}</div> : <EmptyPanel icon={CheckCircle2} title="You’re all caught up" text="New student work submitted for review will appear here." /> : <AdminSnapshot stats={stats} onNavigate={onNavigate} />}
        </Card>
        <Card className="side-panel">
          <div className="panel-heading"><div><span className="eyebrow">{student ? 'A GOOD NEXT STEP' : teacher ? 'REVIEW WORKFLOW' : 'GETTING STARTED'}</span><h2>{student ? 'Keep your momentum' : teacher ? 'Make feedback count' : 'Build your campus'}</h2></div><span className="panel-heading-icon"><Sparkles size={17} /></span></div>
          <p className="side-panel-copy">{student ? 'Small, consistent steps add up. Pick a milestone, share what you have built, and let your progress speak for itself.' : teacher ? 'A thoughtful review helps students understand what went well and where to focus next.' : 'Invite faculty and keep your academic community connected with verified learning.'}</p>
          <ActionButton className="button-full" onClick={() => onNavigate(student ? 'learning' : teacher ? 'reviews' : 'accounts')}>{student ? 'Explore milestones' : teacher ? 'Open review queue' : 'Manage accounts'} <ArrowRight size={16} /></ActionButton>
          <div className="side-panel-note"><ShieldCheck size={16} /><span>Your progress and evidence stay connected.</span></div>
        </Card>
      </div>
      <div className="bottom-note"><Sparkles size={15} /> Every step forward is worth documenting.</div>
    </section>
  )
}

function ActivityRow({ item }) {
  const isVerified = item.status === 'verified'
  const isPending = item.status === 'pending_verification'
  return <div className="activity-row"><div className={`activity-symbol ${isVerified ? 'symbol-green' : isPending ? 'symbol-orange' : 'symbol-lilac'}`}>{isVerified ? <Check size={15} /> : isPending ? <Clock3 size={15} /> : <FileText size={15} />}</div><div className="activity-copy"><strong>{item.title}</strong><span>{item.subject} · {new Date(item.updated_at).toLocaleDateString()}</span></div><Badge variant={isVerified ? 'success' : isPending ? 'warning' : 'default'} className={`status-pill ${isVerified ? 'status-verified' : isPending ? 'status-pending' : 'status-progress'}`}>{isVerified ? 'Verified' : isPending ? 'In review' : 'In progress'}</Badge></div>
}

function AdminSnapshot({ stats, onNavigate }) {
  return <div className="admin-snapshot"><div><span className="snapshot-value">{stats.courses ?? '—'}</span><span className="snapshot-label">courses</span></div><div><span className="snapshot-value">{stats.teachers ?? '—'}</span><span className="snapshot-label">faculty</span></div><div><span className="snapshot-value">{stats.students ?? '—'}</span><span className="snapshot-label">students</span></div><button className="button button-secondary button-full" onClick={() => onNavigate('accounts')}>Manage accounts <ArrowRight size={15} /></button></div>
}

function LearningPath({ milestones, searchTerm, onSubmit }) {
  const filtered = milestones.filter((item) => `${item.title} ${item.subject}`.toLowerCase().includes(searchTerm.toLowerCase()))
  return <section><div className="page-heading"><div><span className="eyebrow">YOUR CURRICULUM</span><h1>Learning path</h1><p className="muted">Build skills one verified milestone at a time.</p></div><span className="soft-chip"><BookOpen size={15} />{milestones.length} milestones</span></div>
    {filtered.length ? <div className="milestone-list">{filtered.map((item, index) => <article className="milestone-card" key={item.id}><div className={`milestone-marker ${item.status}`}><span>{item.status === 'verified' ? <Check size={16} /> : String(index + 1).padStart(2, '0')}</span></div><div className="milestone-body"><div className="milestone-meta"><span>{item.subject_code} · SEMESTER {item.semester}</span><span className={`status-pill ${item.status === 'verified' ? 'status-verified' : item.status === 'pending_verification' ? 'status-pending' : item.status === 'locked' ? 'status-locked' : 'status-progress'}`}>{item.status.replaceAll('_', ' ')}</span></div><h2>{item.title}</h2><p>{item.description || 'A chance to show what you have learned.'}</p>{item.feedback && <div className="feedback-note"><strong>Faculty feedback</strong><span>{item.feedback}</span></div>}{item.submission && <div className="submission-summary"><FileText size={15} /><span>{item.submission.summary}</span>{item.submission.proof_url && <a href={item.submission.proof_url} target="_blank" rel="noreferrer">View evidence <ArrowUpRight size={13} /></a>}</div>}{item.status !== 'locked' && item.status !== 'verified' && item.status !== 'pending_verification' && <button className="button button-secondary milestone-action" onClick={() => onSubmit(item)}>{item.submission ? 'Resubmit evidence' : 'Submit evidence'} <ArrowRight size={15} /></button>}</div></article>)}</div> : <EmptyPanel icon={Search} title="No milestones found" text="Try another search term." />}</section>
}

function ReviewQueue({ submissions, searchTerm, onReview }) {
  const filtered = submissions.filter((item) => `${item.student} ${item.title} ${item.subject}`.toLowerCase().includes(searchTerm.toLowerCase()))
  return <section><div className="page-heading"><div><span className="eyebrow">FACULTY WORKSPACE</span><h1>Review submissions</h1><p className="muted">Give every piece of student work thoughtful, timely feedback.</p></div><span className="soft-chip"><Clock3 size={15} />{submissions.length} awaiting review</span></div>
    {filtered.length ? <div className="submission-list">{filtered.map((item) => <article className="submission-card" key={item.id}><div className="submission-card-top"><div className="avatar">{item.student.split(' ').map((part) => part[0]).join('').slice(0, 2)}</div><div><strong>{item.student}</strong><span>{item.email}</span></div><span className="status-pill status-pending">Awaiting review</span></div><div className="submission-content"><span className="eyebrow">{item.subject}</span><h2>{item.title}</h2><p>{item.submission.summary}</p>{item.submission.proof_url && <a className="evidence-link" href={item.submission.proof_url} target="_blank" rel="noreferrer"><FileText size={15} />Open submitted evidence <ArrowUpRight size={14} /></a>}<span className="submitted-date">Submitted {new Date(item.updated_at).toLocaleString()}</span></div><div className="submission-actions"><button className="button button-quiet" onClick={() => onReview(item, 'needs_revision')}>Request changes</button><button className="button button-primary" onClick={() => onReview(item, 'verified')}><Check size={16} /> Verify work</button></div></article>)}</div> : <EmptyPanel icon={CheckCircle2} title="Nothing to review right now" text="Student evidence will appear here when it is ready." />}</section>
}

function Accounts({ users, searchTerm, onCreateTeacher }) {
  const filtered = users.filter((item) => `${item.email} ${item.role}`.toLowerCase().includes(searchTerm.toLowerCase()))
  return <section><div className="page-heading"><div><span className="eyebrow">CAMPUS ADMINISTRATION</span><h1>Accounts</h1><p className="muted">Manage the people who make your campus community.</p></div></div><div className="accounts-layout"><div className="panel accounts-panel"><div className="panel-heading"><div><span className="eyebrow">DIRECTORY</span><h2>Campus accounts</h2></div><span className="soft-chip">{users.length} accounts</span></div>{filtered.length ? <div className="account-list">{filtered.map((item) => <div className="account-row" key={item.id}><div className="avatar avatar-small">{item.email.slice(0, 2).toUpperCase()}</div><div className="activity-copy"><strong>{item.email}</strong><span>Joined {new Date(item.created_at).toLocaleDateString()}</span></div><span className="role-pill">{item.role}</span><span className={`account-state ${item.active ? 'is-active' : ''}`}>{item.active ? 'Active' : 'Disabled'}</span></div>)}</div> : <p className="muted empty-copy">No accounts match your search.</p>}</div><div className="panel faculty-panel"><div className="feature-icon feature-violet"><Users size={18} /></div><h2>Invite faculty</h2><p>Create faculty access for teachers who need to review student evidence.</p><form className="auth-form compact-form" onSubmit={onCreateTeacher}><div className="field-row"><label>First name<input name="first_name" required maxLength="100" /></label><label>Last name<input name="last_name" required maxLength="100" /></label></div><label>Work email<input name="email" type="email" required maxLength="255" /></label><label>Department<input name="department" required minLength="2" maxLength="255" /></label><label>Temporary password<input name="password" type="password" required minLength="8" maxLength="128" /></label><button className="button button-primary button-full" type="submit"><Plus size={16} /> Create faculty account</button></form></div></div></section>
}

function Announcements() {
  const [items, setItems] = useState([])
  const [error, setError] = useState('')
  useEffect(() => {
    getAnnouncements().then(setItems).catch((requestError) => setError(requestError.message))
  }, [])
  return <section><div className="page-heading"><div><span className="eyebrow">CAMPUS UPDATES</span><h1>Announcements</h1><p className="muted">The latest from your academic community.</p></div></div>{error && <div className="alert alert-error">{error}</div>}{items.length ? <div className="announcement-list">{items.map((item) => <article className="panel announcement-card" key={item.id}><div className="announcement-icon"><Bell size={18} /></div><div><span className="eyebrow">{new Date(item.published_at).toLocaleDateString()}</span><h2>{item.title}</h2><p>{item.body}</p></div></article>)}</div> : !error && <EmptyPanel icon={Bell} title="No announcements yet" text="Campus updates will show up here." />}</section>
}

function Profile({ user, fullName }) {
  return <section><div className="page-heading"><div><span className="eyebrow">YOUR ACCOUNT</span><h1>My profile</h1><p className="muted">Your account details and workspace access.</p></div></div><div className="panel profile-card"><div className="profile-cover"><div className="profile-avatar">{fullName.split(' ').map((part) => part[0]).join('').slice(0, 2).toUpperCase()}</div></div><div className="profile-info"><h2>{fullName}</h2><p>{user.email}</p><span className="role-pill">{user.role}</span></div><div className="profile-details"><div><span>Account role</span><strong>{user.role[0].toUpperCase() + user.role.slice(1)}</strong></div><div><span>Member since</span><strong>VeriSphere community</strong></div><div><span>Account status</span><strong className="profile-status"><i /> Active</strong></div></div></div></section>
}

function EmptyPanel({ icon: Icon, title, text, action, onClick }) {
  return <div className="empty-panel"><span className="empty-icon"><Icon size={21} /></span><strong>{title}</strong><p>{text}</p>{action && <button className="text-button" onClick={onClick}>{action} <ArrowRight size={15} /></button>}</div>
}

export default App
