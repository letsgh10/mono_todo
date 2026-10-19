import React, { useState, useEffect, useCallback, useRef, createContext, useContext } from 'react'
import { api } from './api'

// ── Icons ─────────────────────────────────────────────────────────────────────
// Stroke icons ported from the Figma design; rendered inline so they inherit `color`.
const ICON_PATHS = {
  alert: (
    <>
      <path d="M12 9v4" />
      <path d="M12 17h.01" />
      <path d="M10.3 3.8 2.2 18a2 2 0 0 0 1.7 3h16.2a2 2 0 0 0 1.7-3L13.7 3.8a2 2 0 0 0-3.4 0Z" />
    </>
  ),
  calendar: (
    <>
      <path d="M8 2v4M16 2v4M3 10h18" />
      <rect x="3" y="4" width="18" height="18" rx="3" />
    </>
  ),
  check: <path d="m5 12 4 4L19 6" />,
  chevron: <path d="m9 18 6-6-6-6" />,
  clock: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </>
  ),
  folder: <path d="M3 7.5A2.5 2.5 0 0 1 5.5 5H9l2 2h7.5A2.5 2.5 0 0 1 21 9.5v7a2.5 2.5 0 0 1-2.5 2.5h-13A2.5 2.5 0 0 1 3 16.5Z" />,
  logout: (
    <>
      <path d="M10 17l5-5-5-5M15 12H3" />
      <path d="M14 4h4a3 3 0 0 1 3 3v10a3 3 0 0 1-3 3h-4" />
    </>
  ),
  menu: <path d="M4 7h16M4 12h16M4 17h16" />,
  pencil: (
    <>
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" />
    </>
  ),
  plus: <path d="M12 5v14M5 12h14" />,
  search: (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-4-4" />
    </>
  ),
  sparkles: (
    <>
      <path d="m12 3 1.2 3.8L17 8l-3.8 1.2L12 13l-1.2-3.8L7 8l3.8-1.2Z" />
      <path d="m18.5 14 .7 2.3 2.3.7-2.3.7-.7 2.3-.7-2.3-2.3-.7 2.3-.7Z" />
      <path d="m5 14 .6 1.9 1.9.6-1.9.6L5 19l-.6-1.9-1.9-.6 1.9-.6Z" />
    </>
  ),
  tag: (
    <>
      <path d="M20 13 13 20a2 2 0 0 1-2.8 0L4 13.8V4h9.8L20 10.2a2 2 0 0 1 0 2.8Z" />
      <circle cx="9" cy="9" r="1" />
    </>
  ),
  tasks: (
    <>
      <rect x="4" y="3" width="16" height="18" rx="3" />
      <path d="m8 9 1.5 1.5L12 8M14 10h3M8 15h9" />
    </>
  ),
  trash: (
    <>
      <path d="M3 6h18M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
      <path d="M10 11v6M14 11v6" />
    </>
  ),
  users: (
    <>
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
    </>
  ),
  x: <path d="m6 6 12 12M18 6 6 18" />,
}

function Icon({ name, size = 18 }) {
  return (
    <svg
      aria-hidden="true"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {ICON_PATHS[name]}
    </svg>
  )
}

// ── Toast context ──────────────────────────────────────────────────────────────
const ToastCtx = createContext(null)

function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const push = useCallback((msg, type = 'success') => {
    const id = Date.now()
    setToasts(t => [...t, { id, msg, type }])
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 3500)
  }, [])
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="toast-stack">
        {toasts.map(t => (
          <div key={t.id} className={`toast toast-${t.type}`}>{t.msg}</div>
        ))}
      </div>
    </ToastCtx.Provider>
  )
}

function useToast() { return useContext(ToastCtx) }

// ── Auth page ─────────────────────────────────────────────────────────────────
function AuthPage({ onLogin }) {
  const [tab, setTab] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const toast = useToast()

  async function submit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      if (tab === 'login') {
        await api.login(email, password)
        onLogin(email)
      } else {
        await api.register(email, password)
        toast('Konto utworzone — zaloguj się!', 'success')
        setTab('login')
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-wrapper grid-paper">
      <div className="auth-card">
        <div className="auth-logo">
          <div className="logo-mark"><Icon name="check" size={19} /></div>
          <div>
            <h1>
              TodoAI
              <span className="brand-spark"><Icon name="sparkles" size={16} /></span>
            </h1>
            <p>Zarządzaj zadaniami z pomocą AI</p>
          </div>
        </div>
        <div className="auth-tabs">
          <button className={`auth-tab ${tab === 'login' ? 'active' : ''}`} onClick={() => { setTab('login'); setError('') }}>Logowanie</button>
          <button className={`auth-tab ${tab === 'register' ? 'active' : ''}`} onClick={() => { setTab('register'); setError('') }}>Rejestracja</button>
        </div>
        {error && <div className="alert alert-error">{error}</div>}
        <form onSubmit={submit}>
          <div className="form-group">
            <label>Email</label>
            <input type="email" placeholder="you@example.com" value={email} onChange={e => setEmail(e.target.value)} required />
          </div>
          <div className="form-group">
            <label>Hasło</label>
            <input type="password" placeholder="••••••••" value={password} onChange={e => setPassword(e.target.value)} required minLength={6} />
          </div>
          <button className="btn btn-primary btn-full" type="submit" disabled={loading}>
            {loading ? <span className="spinner" /> : (tab === 'login' ? 'Zaloguj się' : 'Utwórz konto')}
          </button>
        </form>
      </div>
    </div>
  )
}

// ── Task modal ────────────────────────────────────────────────────────────────
function TaskModal({ task, categories, projects = [], onSave, onClose }) {
  const isEdit = !!task?.id
  const [title, setTitle] = useState(task?.title ?? '')
  const [description, setDescription] = useState(task?.description ?? '')
  const [priority, setPriority] = useState(task?.priority ?? 'medium')
  const [status, setStatus] = useState(task?.status ?? 'todo')
  const [categoryId, setCategoryId] = useState(task?.category?.id ?? '')
  const [projectId, setProjectId] = useState(task?.project_id ?? '')
  const [tagInput, setTagInput] = useState('')
  const [tags, setTags] = useState(task?.tags ?? [])
  const dueDateRef = React.useRef(null)
  const [useAI, setUseAI] = useState(false)
  const [loading, setLoading] = useState(false)
  const [aiLoading, setAiLoading] = useState(false)
  const [error, setError] = useState('')
  const [aiReason, setAiReason] = useState(task?.priority_reason ?? '')
  const toast = useToast()

  async function analyzeAI() {
    if (!title.trim()) return
    setAiLoading(true)
    try {
      const res = await api.reanalyzePriority
        ? null
        : null
      // Use analyze endpoint
      const r = await fetch('/tasks/priority/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem('token')}` },
        body: JSON.stringify({ title, description, due_date: dueDateRef.current?.value || null }),
      })
      const data = await r.json()
      setPriority(data.priority)
      setAiReason(data.priority_reason)
      toast('AI zasugerowało priorytet: ' + data.priority, 'success')
    } catch {
      toast('Błąd AI', 'error')
    } finally {
      setAiLoading(false)
    }
  }

  function handleTagKey(e) {
    if ((e.key === 'Enter' || e.key === ',') && tagInput.trim()) {
      e.preventDefault()
      const t = tagInput.trim().replace(/,$/, '')
      if (t && !tags.includes(t)) setTags([...tags, t])
      setTagInput('')
    }
    if (e.key === 'Backspace' && !tagInput && tags.length) {
      setTags(tags.slice(0, -1))
    }
  }

  async function submit(e) {
    e.preventDefault()
    if (!title.trim()) return
    setError('')
    setLoading(true)
    try {
      const payload = {
        title: title.trim(),
        description: description.trim() || null,
        priority,
        status,
        category_id: categoryId ? parseInt(categoryId) : null,
        project_id: projectId ? parseInt(projectId) : null,
        tags,
        due_date: dueDateRef.current?.value || null,
      }
      if (isEdit) {
        await onSave(task.id, payload, tags)
      } else {
        await onSave(null, payload, tags, useAI)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-header">
          <h2>{isEdit ? 'Edytuj zadanie' : 'Nowe zadanie'}</h2>
          <button className="icon-btn" onClick={onClose} aria-label="Zamknij"><Icon name="x" size={16} /></button>
        </div>
        <div className="modal-body">
          {error && <div className="alert alert-error">{error}</div>}
          <div className="form-group">
            <label>Tytuł *</label>
            <input value={title} onChange={e => setTitle(e.target.value)} placeholder="Co chcesz zrobić?" autoFocus />
          </div>
          <div className="form-group">
            <label>Opis</label>
            <textarea value={description} onChange={e => setDescription(e.target.value)} placeholder="Opcjonalny opis…" />
          </div>
          <div className="modal-grid">
            <div className="form-group">
              <label>Priorytet</label>
              <select value={priority} onChange={e => setPriority(e.target.value)}>
                <option value="low">Niski</option>
                <option value="medium">Średni</option>
                <option value="high">Wysoki</option>
              </select>
            </div>
            <div className="form-group">
              <label>Status</label>
              <select value={status} onChange={e => setStatus(e.target.value)}>
                <option value="todo">Do zrobienia</option>
                <option value="done">Zrobione</option>
              </select>
            </div>
          </div>
          <div className="form-group">
            <label>Termin wykonania</label>
            <input type="date" ref={dueDateRef} defaultValue={task?.due_date?.slice(0, 10) ?? ''} />
          </div>
          <div className="form-group">
            <label>Kategoria</label>
            <select value={categoryId} onChange={e => setCategoryId(e.target.value)}>
              <option value="">Brak kategorii</option>
              {categories.map(c => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label>Projekt</label>
            {isEdit ? (
              <div className="project-static">{projects.find(p => p.id === task.project_id)?.name ?? 'Brak projektu'}</div>
            ) : (
              <select value={projectId} onChange={e => setProjectId(e.target.value)}>
                <option value="">Brak projektu</option>
                {projects.map(p => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            )}
          </div>
          <div className="form-group">
            <label>Tagi (Enter aby dodać)</label>
            <div className="tags-container" onClick={e => e.currentTarget.querySelector('input').focus()}>
              {tags.map(t => (
                <span key={t} className="tag-chip">
                  #{t}
                  <button type="button" onClick={() => setTags(tags.filter(x => x !== t))}>×</button>
                </span>
              ))}
              <input
                className="tag-input"
                value={tagInput}
                onChange={e => setTagInput(e.target.value)}
                onKeyDown={handleTagKey}
                placeholder={tags.length ? '' : 'np. praca, dom…'}
              />
            </div>
          </div>
          {aiReason && (
            <div className="priority-reason">
              <span className="ai-badge"><Icon name="sparkles" size={11} />AI</span>
              <span>{aiReason}</span>
            </div>
          )}
          <div className="form-actions">
            <button type="button" className="btn btn-secondary btn-sm" onClick={analyzeAI} disabled={!title.trim() || aiLoading}>
              {aiLoading ? <span className="spinner spinner-sm" /> : <Icon name="sparkles" size={14} />}
              Sugestia AI
            </button>
            {!isEdit && (
              <label className="form-check">
                <input type="checkbox" checked={useAI} onChange={e => setUseAI(e.target.checked)} />
                Użyj AI przy zapisie
              </label>
            )}
          </div>
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>Anuluj</button>
          <button className="btn btn-primary" onClick={submit} disabled={loading || !title.trim()}>
            {loading ? <span className="spinner spinner-sm" /> : (isEdit ? 'Zapisz' : 'Dodaj zadanie')}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Category modal ────────────────────────────────────────────────────────────
const COLORS = ['#3c46e8','#c8ff3d','#22c55e','#f59e0b','#ff715b','#ec4899','#8b5cf6','#14b8a6','#f97316','#64748b']

function CategoryModal({ onSave, onClose }) {
  const [name, setName] = useState('')
  const [color, setColor] = useState(COLORS[0])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function submit(e) {
    e.preventDefault()
    if (!name.trim()) return
    setLoading(true)
    setError('')
    try {
      await onSave(name.trim(), color)
      onClose()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal" style={{ maxWidth: 380 }}>
        <div className="modal-header">
          <h2>Nowa kategoria</h2>
          <button className="icon-btn" onClick={onClose} aria-label="Zamknij"><Icon name="x" size={16} /></button>
        </div>
        <div className="modal-body">
          {error && <div className="alert alert-error">{error}</div>}
          <div className="form-group">
            <label>Nazwa</label>
            <input value={name} onChange={e => setName(e.target.value)} placeholder="np. Praca" autoFocus />
          </div>
          <div className="form-group">
            <label>Kolor</label>
            <div className="color-row">
              {COLORS.map(c => (
                <div
                  key={c}
                  className={`color-swatch ${color === c ? 'selected' : ''}`}
                  style={{ background: c }}
                  onClick={() => setColor(c)}
                />
              ))}
            </div>
          </div>
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>Anuluj</button>
          <button className="btn btn-primary" onClick={submit} disabled={loading || !name.trim()}>
            {loading ? <span className="spinner spinner-sm" /> : 'Utwórz'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Project modals ────────────────────────────────────────────────────────────
// Splits "a@x.pl, b@y.pl" (commas, semicolons or whitespace) into unique non-empty emails.
function parseEmails(text) {
  return [...new Set(text.split(/[\s,;]+/).filter(Boolean))]
}

function ProjectModal({ onSave, onClose }) {
  const [name, setName] = useState('')
  const [emails, setEmails] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function submit(e) {
    e.preventDefault()
    if (!name.trim()) return
    setLoading(true)
    setError('')
    try {
      await onSave(name.trim(), parseEmails(emails))
      onClose()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal" style={{ maxWidth: 420 }}>
        <div className="modal-header">
          <h2>Nowy projekt</h2>
          <button className="icon-btn" onClick={onClose} aria-label="Zamknij"><Icon name="x" size={16} /></button>
        </div>
        <div className="modal-body">
          {error && <div className="alert alert-error">{error}</div>}
          <form onSubmit={submit}>
            <div className="form-group">
              <label>Nazwa</label>
              <input value={name} onChange={e => setName(e.target.value)} placeholder="np. Remont mieszkania" autoFocus />
            </div>
            <div className="form-group">
              <label>Zaproś użytkowników</label>
              <input value={emails} onChange={e => setEmails(e.target.value)} placeholder="emaile oddzielone przecinkami" />
              <small className="form-hint">Zarejestrowani użytkownicy zostaną od razu dodani jako członkowie.</small>
            </div>
          </form>
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>Anuluj</button>
          <button className="btn btn-primary" onClick={submit} disabled={loading || !name.trim()}>
            {loading ? <span className="spinner spinner-sm" /> : 'Utwórz'}
          </button>
        </div>
      </div>
    </div>
  )
}

const ROLE_LABEL = { owner: 'Właściciel', member: 'Członek' }

function MembersModal({ project, members, userEmail, connected, send, onClose }) {
  const [email, setEmail] = useState('')
  const [adding, setAdding] = useState(false)
  const [error, setError] = useState('')
  const toast = useToast()
  const loading = members === undefined
  const isOwner = !loading && members.some(m => m.role === 'owner' && m.email === userEmail)

  // Ask for the member list once the socket is up (and again after every reconnect);
  // later changes arrive as member_added / member_removed events.
  useEffect(() => {
    if (!connected) return
    send({ type: 'list_members', project_id: project.id }).catch(err => setError(err.message))
  }, [project.id, connected, send])

  async function addMember(e) {
    e.preventDefault()
    if (!email.trim()) return
    setAdding(true)
    setError('')
    try {
      await send({ type: 'add_member', project_id: project.id, email: email.trim() })
      setEmail('')
      toast('Dodano członka', 'success')
    } catch (err) {
      setError(err.message)
    } finally {
      setAdding(false)
    }
  }

  async function removeMember(member) {
    if (!confirm(`Usunąć ${member.email} z projektu?`)) return
    setError('')
    try {
      await send({ type: 'remove_member', project_id: project.id, user_id: member.user_id })
      toast('Usunięto członka', 'success')
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal" style={{ maxWidth: 440 }}>
        <div className="modal-header">
          <h2>Członkowie: {project.name}</h2>
          <button className="icon-btn" onClick={onClose} aria-label="Zamknij"><Icon name="x" size={16} /></button>
        </div>
        <div className="modal-body">
          {error && <div className="alert alert-error">{error}</div>}
          {loading ? (
            <div className="modal-loading"><span className="spinner" /></div>
          ) : (
            <div className="member-list">
              {members.map(m => (
                <div key={m.user_id} className="member-row">
                  <span className="member-email">{m.email}</span>
                  <span className={`member-role member-role-${m.role}`}>{ROLE_LABEL[m.role]}</span>
                  {isOwner && m.role !== 'owner' && (
                    <button className="icon-btn danger" title="Usuń z projektu" onClick={() => removeMember(m)}>
                      <Icon name="trash" size={15} />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
          {isOwner && (
            <form className="member-form" onSubmit={addMember}>
              <input type="email" placeholder="email użytkownika" value={email} onChange={e => setEmail(e.target.value)} />
              <button className="btn btn-primary btn-sm" type="submit" disabled={adding || !email.trim()}>
                {adding ? <span className="spinner spinner-sm" /> : 'Dodaj'}
              </button>
            </form>
          )}
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>Zamknij</button>
        </div>
      </div>
    </div>
  )
}

// ── History modal ─────────────────────────────────────────────────────────────
const PRIORITY_LABEL = { low: 'Niski', medium: 'Średni', high: 'Wysoki' }
const STATUS_LABEL = { todo: 'Do zrobienia', done: 'Zrobione' }
const HISTORY_FIELD_LABEL = {
  title: 'Tytuł',
  description: 'Opis',
  status: 'Status',
  priority: 'Priorytet',
  due_date: 'Termin',
  category_id: 'Kategoria',
  project_id: 'Projekt',
  tags: 'Tagi',
}

// The API returns naive UTC timestamps (no offset); append Z so the browser converts to local time.
function parseServerDate(value) {
  return new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(value) ? value : value + 'Z')
}

function formatHistoryValue(field, value, { categories, projects }) {
  if (value === null || value === undefined || value === '') return '—'
  switch (field) {
    case 'status': return STATUS_LABEL[value] ?? value
    case 'priority': return PRIORITY_LABEL[value] ?? value
    case 'due_date': {
      const d = new Date(value.replace(' ', 'T'))
      return isNaN(d) ? value : d.toLocaleDateString('pl-PL', { day: 'numeric', month: 'short', year: 'numeric' })
    }
    case 'category_id': return categories.find(c => String(c.id) === value)?.name ?? `#${value}`
    case 'project_id': return projects.find(p => String(p.id) === value)?.name ?? `#${value}`
    case 'tags':
      try {
        const tags = JSON.parse(value)
        return tags.length ? tags.map(t => `#${t}`).join(' ') : 'brak'
      } catch {
        return value
      }
    default: return value
  }
}

function HistoryModal({ task, categories, projects, members, onClose }) {
  const [entries, setEntries] = useState(undefined) // undefined = loading
  const [error, setError] = useState('')
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let cancelled = false
    setEntries(undefined)
    setError('')
    api.getTaskHistory(task.id)
      .then(data => { if (!cancelled) setEntries(data) })
      .catch(err => { if (!cancelled) setError(err.message) })
    return () => { cancelled = true }
  }, [task.id, reloadKey])

  function author(entry) {
    if (entry.changed_by_id == null) return null
    if (task.project_id == null) return 'Ty'
    return members?.find(m => m.user_id === entry.changed_by_id)?.email ?? `Użytkownik #${entry.changed_by_id}`
  }

  const lookups = { categories, projects }

  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal" style={{ maxWidth: 520 }}>
        <div className="modal-header">
          <h2>Historia: {task.title}</h2>
          <button className="icon-btn" onClick={onClose} aria-label="Zamknij"><Icon name="x" size={16} /></button>
        </div>
        <div className="modal-body">
          {error ? (
            <>
              <div className="alert alert-error">Nie udało się pobrać historii: {error}</div>
              <button className="btn btn-secondary btn-sm" onClick={() => setReloadKey(k => k + 1)}>Spróbuj ponownie</button>
            </>
          ) : entries === undefined ? (
            <div className="modal-loading"><span className="spinner" /></div>
          ) : entries.length === 0 ? (
            <div className="history-empty">Brak zmian dla tego zadania</div>
          ) : (
            <div className="history-list">
              {[...entries].reverse().map(e => (
                <div key={e.id} className="history-row">
                  <div className="history-field">{HISTORY_FIELD_LABEL[e.field] ?? e.field}</div>
                  <div className="history-change">
                    <span className="history-old">{formatHistoryValue(e.field, e.old_value, lookups)}</span>
                    <span aria-hidden="true"> → </span>
                    <span className="history-new">{formatHistoryValue(e.field, e.new_value, lookups)}</span>
                  </div>
                  <div className="history-meta">
                    {parseServerDate(e.changed_at).toLocaleString('pl-PL', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
                    {author(e) && ` · ${author(e)}`}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>Zamknij</button>
        </div>
      </div>
    </div>
  )
}

// ── Task card ─────────────────────────────────────────────────────────────────
function getDueDateStatus(dueDate) {
  if (!dueDate) return null
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const due = new Date(dueDate)
  due.setHours(0, 0, 0, 0)
  const diff = (due - today) / (1000 * 60 * 60 * 24)
  if (diff < 0) return 'overdue'
  if (diff <= 3) return 'soon'
  return 'ok'
}

function isDueToday(dueDate) {
  return !!dueDate && new Date(dueDate).toDateString() === new Date().toDateString()
}

function TaskCard({ task, projectName, onEdit, onDelete, onToggle, onHistory }) {
  const priorityLabel = PRIORITY_LABEL
  const date = new Date(task.created_at).toLocaleDateString('pl-PL', { day: 'numeric', month: 'short' })
  const dueDateStatus = getDueDateStatus(task.due_date)
  const dueDateLabel = task.due_date
    ? new Date(task.due_date).toLocaleDateString('pl-PL', { day: 'numeric', month: 'short', year: 'numeric' })
    : null
  const isDone = task.status === 'done'

  function toggle(e) {
    e.stopPropagation()
    onToggle(task)
  }

  return (
    <div className={`task-card ${isDone ? 'done' : ''} ${dueDateStatus === 'overdue' ? 'overdue' : ''}`} onClick={() => onEdit(task)}>
      <span
        role="checkbox"
        aria-checked={isDone}
        aria-label={isDone ? 'Oznacz jako do zrobienia' : 'Oznacz jako ukończone'}
        tabIndex={0}
        className={`task-check ${isDone ? 'checked' : ''}`}
        onClick={toggle}
        onKeyDown={e => { if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); toggle(e) } }}
      >
        {isDone && <Icon name="check" size={13} />}
      </span>
      <div className="task-body">
        <div className="task-title">{task.title}</div>
        {task.description && <div className="task-desc">{task.description}</div>}
        <div className="task-meta">
          <span className={`badge badge-priority-${task.priority}`}>{priorityLabel[task.priority]}</span>
          {task.category && (
            <span className="badge badge-cat" style={{ background: task.category.color ? task.category.color + '33' : undefined }}>
              {task.category.color && <span className="cat-dot" style={{ background: task.category.color }} />}
              {task.category.name}
            </span>
          )}
          {projectName && (
            <span className="badge badge-project">
              <Icon name="folder" size={11} />
              {projectName}
            </span>
          )}
          {task.tags?.map(t => <span key={t} className="badge badge-tag">#{t}</span>)}
          {task.ai_override && <span className="ai-badge"><Icon name="sparkles" size={11} />AI</span>}
          {dueDateLabel && (
            <span className={`due-date due-${dueDateStatus}`}>
              <Icon name={dueDateStatus === 'overdue' ? 'alert' : 'clock'} size={11} />
              {dueDateLabel}
            </span>
          )}
          <span className="task-date">{date}</span>
        </div>
      </div>
      <div className="task-actions">
        <button className="icon-btn" onClick={e => { e.stopPropagation(); onHistory(task) }} title="Historia" aria-label="Historia"><Icon name="clock" size={15} /></button>
        <button className="icon-btn" onClick={e => { e.stopPropagation(); onEdit(task) }} title="Edytuj"><Icon name="pencil" size={15} /></button>
        <button className="icon-btn danger" onClick={e => { e.stopPropagation(); onDelete(task.id) }} title="Usuń"><Icon name="trash" size={15} /></button>
      </div>
    </div>
  )
}

// ── Projects over WebSocket ───────────────────────────────────────────────────
const LIVE_STATUS_LABEL = { connecting: 'Łączenie…', online: 'System gotowy', offline: 'Offline' }

// Apply `update` to the cached member list of a project; lists not requested yet stay untouched.
function updateMembers(cache, projectId, update) {
  const list = cache[projectId]
  return list ? { ...cache, [projectId]: update(list) } : cache
}

/**
 * Keeps the project list (and every member list already requested) in sync with the server.
 * onMembershipChanged(removedProjectId?) fires when the user gains or loses a project.
 * onTasksChanged(event) fires when a task the user can see is created, updated or deleted.
 */
function useProjectsSocket({ onMembershipChanged, onTasksChanged, onUnauthorized }) {
  const [projects, setProjects] = useState([])
  const [membersByProject, setMembersByProject] = useState({})
  const [status, setStatus] = useState('connecting')
  const socketRef = useRef(null)
  const callbacks = useRef({ onMembershipChanged, onTasksChanged, onUnauthorized })
  callbacks.current = { onMembershipChanged, onTasksChanged, onUnauthorized }

  useEffect(() => {
    let hasSnapshot = false
    const socket = api.connectProjects({
      onStatus: next => {
        if (next === 'unauthorized') callbacks.current.onUnauthorized()
        else setStatus(next)
      },
      onMessage: msg => {
        switch (msg.type) {
          case 'projects':
            setProjects(msg.projects)
            // After a reconnect the membership may have changed while we were offline.
            if (hasSnapshot) callbacks.current.onMembershipChanged()
            hasSnapshot = true
            break
          case 'project_added':
            setProjects(prev => (prev.some(p => p.id === msg.project.id) ? prev : [...prev, msg.project]))
            callbacks.current.onMembershipChanged()
            break
          case 'project_removed':
            setProjects(prev => prev.filter(p => p.id !== msg.project_id))
            setMembersByProject(prev => {
              const next = { ...prev }
              delete next[msg.project_id]
              return next
            })
            callbacks.current.onMembershipChanged(msg.project_id)
            break
          case 'members':
            setMembersByProject(prev => ({ ...prev, [msg.project_id]: msg.members }))
            break
          case 'member_added':
            setMembersByProject(prev => updateMembers(prev, msg.project_id,
              list => [...list.filter(m => m.user_id !== msg.member.user_id), msg.member]))
            break
          case 'member_removed':
            setMembersByProject(prev => updateMembers(prev, msg.project_id,
              list => list.filter(m => m.user_id !== msg.user_id)))
            break
          case 'task_created':
          case 'task_updated':
          case 'task_deleted':
            callbacks.current.onTasksChanged(msg)
            break
          default:
            break
        }
      },
    })
    socketRef.current = socket
    return () => {
      socket.close()
      socketRef.current = null
    }
  }, [])

  const send = useCallback(command => {
    if (!socketRef.current) return Promise.reject(new Error('Brak połączenia z serwerem'))
    return socketRef.current.send(command)
  }, [])

  return { projects, membersByProject, status, send }
}

// ── Sidebar ───────────────────────────────────────────────────────────────────
// Each entry is a saved view: it maps onto the task filters / view in Dashboard.
const NAV_ITEMS = [
  { key: 'all', label: 'Wszystkie', icon: 'tasks' },
  { key: 'todo', label: 'Do zrobienia', icon: 'clock' },
  { key: 'done', label: 'Ukończone', icon: 'check' },
  { key: 'high', label: 'Pilne', icon: 'alert' },
  { key: 'overdue', label: 'Przeterminowane', icon: 'calendar' },
]
const NAV_LABEL = Object.fromEntries(NAV_ITEMS.map(item => [item.key, item.label]))

function Sidebar({
  open, onClose, counts, activeNav, onSelectNav,
  projects, selectedProjectId, onSelectProject, onOpenMembers, onNewProject,
  categories, selectedCategoryId, onSelectCategory, onDeleteCategory, onNewCategory,
  userEmail, onLogout,
}) {
  return (
    <>
      {open && <button className="sidebar-backdrop" aria-label="Zamknij menu" onClick={onClose} />}
      <aside className={`sidebar ${open ? 'is-open' : ''}`}>
        <div className="sidebar-head">
          <div className="brand">
            <div className="logo-mark"><Icon name="check" size={19} /></div>
            <div>
              <div className="brand-name">
                TodoAI
                <span className="brand-spark"><Icon name="sparkles" size={14} /></span>
              </div>
              <p className="brand-tagline">Twój inteligentny planer</p>
            </div>
          </div>
          <button className="icon-button sidebar-close" aria-label="Zamknij menu" onClick={onClose}><Icon name="x" /></button>
        </div>

        <nav className="sidebar-nav">
          <p className="section-label">Zadania</p>
          <div className="nav-list">
            {NAV_ITEMS.map(item => (
              <button
                key={item.key}
                className={`nav-item ${activeNav === item.key ? 'active' : ''}`}
                onClick={() => onSelectNav(item.key)}
              >
                <span className="nav-item-label">
                  <Icon name={item.icon} size={17} />
                  {item.label}
                </span>
                <span className="count-pill">{counts[item.key]}</span>
              </button>
            ))}
          </div>

          <section className="panel sidebar-section">
            <div className="sidebar-section-head">
              <h3 className="section-label">Projekty</h3>
              <button className="tiny-button" onClick={onNewProject}>
                <Icon name="plus" size={14} />
                Nowy projekt
              </button>
            </div>
            {projects.length === 0 ? (
              <div className="side-empty">
                <div className="side-empty-icon"><Icon name="folder" size={18} /></div>
                <p>Nie należysz jeszcze<br />do żadnego projektu.</p>
              </div>
            ) : (
              <div className="side-list">
                {projects.map(p => (
                  <div
                    key={p.id}
                    className={`side-chip project-chip ${selectedProjectId == p.id ? 'active' : ''}`}
                    onClick={() => onSelectProject(p.id)}
                  >
                    <span className="side-chip-icon"><Icon name="folder" size={16} /></span>
                    <span className="side-chip-name">{p.name}</span>
                    <button className="side-chip-action" title="Członkowie" onClick={e => { e.stopPropagation(); onOpenMembers(p) }}>
                      <Icon name="users" size={14} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="panel sidebar-section">
            <div className="sidebar-section-head">
              <h3 className="section-label">Kategorie</h3>
              <button className="tiny-button" onClick={onNewCategory}>
                <Icon name="plus" size={14} />
                Nowa kategoria
              </button>
            </div>
            {categories.length === 0 ? (
              <div className="side-empty side-empty-compact">
                <p>Brak kategorii.</p>
              </div>
            ) : (
              <div className="side-list">
                {categories.map(c => (
                  <div
                    key={c.id}
                    className={`side-chip cat-chip ${selectedCategoryId == c.id ? 'active' : ''}`}
                    onClick={() => onSelectCategory(c.id)}
                  >
                    <span className="cat-dot" style={{ background: c.color || '#8990a0' }} />
                    <span className="side-chip-name">{c.name}</span>
                    <button className="side-chip-action danger" title="Usuń kategorię" onClick={e => { e.stopPropagation(); onDeleteCategory(c.id) }}>
                      <Icon name="x" size={14} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>
        </nav>

        <div className="sidebar-profile">
          <div className="profile-row">
            <div className="profile-avatar">{(userEmail?.[0] ?? '?').toUpperCase()}</div>
            <div className="profile-info">
              <p className="profile-email">{userEmail}</p>
              <p className="profile-kind">Konto osobiste</p>
            </div>
            <button className="icon-button danger" onClick={onLogout}>
              <Icon name="logout" size={17} />
              <span className="sr-only">Wyloguj</span>
            </button>
          </div>
        </div>
      </aside>
    </>
  )
}

// ── Empty state ───────────────────────────────────────────────────────────────
function EmptyState({ filtered, onAdd }) {
  return (
    <div className="empty-state">
      <div className="empty-composition">
        <div className="empty-card empty-card-back" />
        <div className="empty-card empty-card-middle" />
        <div className="empty-card empty-card-front">
          <span className="empty-check"><Icon name="check" size={23} /></span>
          <span className="empty-line empty-line-long" />
          <span className="empty-line" />
          <span className="empty-line empty-line-short" />
        </div>
        <span className="empty-spark empty-spark-one"><Icon name="sparkles" size={16} /></span>
        <span className="empty-spark empty-spark-two" />
      </div>
      <p className="empty-index">00 / 00</p>
      <h3>Brak zadań</h3>
      <p className="empty-copy">
        {filtered
          ? 'Nie znaleziono zadań pasujących do tego filtra.'
          : 'Dodaj pierwsze zadanie klikając przycisk powyżej i zacznij organizować swój dzień.'}
      </p>
      {!filtered && (
        <button className="btn btn-secondary" onClick={onAdd}>
          <Icon name="plus" size={16} />
          Dodaj pierwsze zadanie
        </button>
      )}
    </div>
  )
}

// ── Dashboard ─────────────────────────────────────────────────────────────────
function pad2(n) { return String(n).padStart(2, '0') }

function pluralTasks(n) {
  if (n === 1) return 'zadanie'
  const m10 = n % 10
  const m100 = n % 100
  if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return 'zadania'
  return 'zadań'
}

function Dashboard({ userEmail, onLogout }) {
  const [tasks, setTasks] = useState([])
  const [categories, setCategories] = useState([])
  const [loading, setLoading] = useState(true)
  const [modal, setModal] = useState(null) // null | { type: 'task', task } | { type: 'category' } | { type: 'project' } | { type: 'members', project } | { type: 'history', task }
  const [filters, setFilters] = useState({ status: '', priority: '', category_id: '', project_id: '', tag: '' })
  const [tagSearch, setTagSearch] = useState('')
  const [view, setView] = useState('all') // 'all' | 'overdue' | 'upcoming'
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const toast = useToast()

  const loadTasks = useCallback(async () => {
    try {
      let data
      if (view === 'overdue') {
        data = await api.getTasks({ ...filters, overdue: true })
      } else if (view === 'upcoming') {
        data = await api.getUpcomingTasks(7)
        data = [...data].sort((a, b) => new Date(a.due_date) - new Date(b.due_date))
      } else {
        data = await api.getTasks(filters)
      }
      setTasks(data)
      // Extract categories from tasks
      const cats = {}
      data.forEach(t => { if (t.category) cats[t.category.id] = t.category })
      setCategories(prev => {
        const merged = { ...prev.reduce((a, c) => ({ ...a, [c.id]: c }), {}), ...cats }
        return Object.values(merged)
      })
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setLoading(false)
    }
  }, [filters, view])

  useEffect(() => { loadTasks() }, [loadTasks])

  // Projects live over WebSocket: a snapshot on connect, then push events.
  const { projects, membersByProject, status: projectsStatus, send: sendProjectCommand } = useProjectsSocket({
    // Another member (or another tab) changed a task we can see: refetch with the current filters.
    onTasksChanged: loadTasks,
    onMembershipChanged: removedProjectId => {
      // Losing the selected project: clearing the filter reloads the list by itself.
      if (removedProjectId !== undefined && filters.project_id == removedProjectId) {
        setFilter('project_id', '')
        return
      }
      loadTasks()
    },
    onUnauthorized: () => {
      toast('Sesja wygasła — zaloguj się ponownie', 'error')
      api.logout()
      onLogout()
    },
  })

  // Close the members modal when the user loses access to that project.
  useEffect(() => {
    if (modal?.type === 'members' && !projects.some(p => p.id === modal.project.id)) setModal(null)
  }, [projects, modal])

  async function handleSaveProject(name, memberEmails) {
    const member_emails = memberEmails.filter(email => email !== userEmail)
    await sendProjectCommand({ type: 'create_project', name, member_emails })
    const count = member_emails.length
    const suffix = count === 1 ? 'członka' : 'członków'
    toast(count ? `Projekt utworzony, dodano ${count} ${suffix}` : 'Projekt utworzony', 'success')
  }

  async function handleSaveTask(id, payload, tags, useAI) {
    try {
      if (id) {
        await api.updateTask(id, {
          title: payload.title,
          description: payload.description,
          priority: payload.priority,
          status: payload.status,
          category_id: payload.category_id,
          due_date: payload.due_date,
        })
        // Sync tags
        const task = tasks.find(t => t.id === id)
        const oldTags = task?.tags ?? []
        for (const t of tags) if (!oldTags.includes(t)) await api.addTag(id, t)
        for (const t of oldTags) if (!tags.includes(t)) await api.removeTag(id, t)
        toast('Zadanie zaktualizowane', 'success')
      } else {
        await api.createTask(payload, useAI)
        toast('Zadanie dodane', 'success')
      }
      setModal(null)
      loadTasks()
    } catch (err) {
      throw err
    }
  }

  async function handleDelete(id) {
    if (!confirm('Usunąć to zadanie?')) return
    try {
      await api.deleteTask(id)
      toast('Zadanie usunięte', 'success')
      loadTasks()
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  async function handleToggle(task) {
    try {
      await api.updateTask(task.id, { status: task.status === 'done' ? 'todo' : 'done' })
      loadTasks()
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  async function handleSaveCategory(name, color) {
    const cat = await api.createCategory(name, color)
    setCategories(prev => [...prev, cat])
    toast('Kategoria dodana', 'success')
  }

  async function handleDeleteCategory(id) {
    if (!confirm('Usunąć kategorię?')) return
    try {
      await api.deleteCategory(id)
      setCategories(prev => prev.filter(c => c.id !== id))
      toast('Kategoria usunięta', 'success')
      loadTasks()
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  const projectNames = Object.fromEntries(projects.map(p => [p.id, p.name]))
  const todo = tasks.filter(t => t.status === 'todo')
  const done = tasks.filter(t => t.status === 'done')
  const high = tasks.filter(t => t.priority === 'high' && t.status === 'todo')
  const overdue = tasks.filter(t => t.status === 'todo' && getDueDateStatus(t.due_date) === 'overdue')
  const dueToday = todo.filter(t => isDueToday(t.due_date))
  const counts = { all: tasks.length, todo: todo.length, done: done.length, high: high.length, overdue: overdue.length }

  // Which sidebar view the current filters correspond to (null while browsing "Nadchodzące").
  const activeNav = view === 'upcoming' ? null
    : view === 'overdue' ? 'overdue'
    : filters.status === 'done' ? 'done'
    : filters.status === 'todo' ? 'todo'
    : filters.priority === 'high' ? 'high'
    : 'all'
  const pageTitle = view === 'upcoming' ? 'Nadchodzące (7 dni)' : NAV_LABEL[activeNav]
  const selectedProject = projects.find(p => p.id == filters.project_id)
  const activeCategory = categories.find(c => c.id == filters.category_id)
  const eyebrow = selectedProject ? `Projekt / ${selectedProject.name}` : `Przestrzeń osobista / ${new Date().getFullYear()}`
  const hasActiveFilters = Boolean(
    view !== 'all' || tagSearch || filters.status || filters.priority || filters.category_id || filters.project_id,
  )

  function setFilter(key, val) {
    setFilters(f => ({ ...f, [key]: val }))
  }

  function selectNav(key) {
    setSidebarOpen(false)
    if (key === 'overdue') {
      setView('overdue')
      return
    }
    setView('all')
    setFilters(f => ({
      ...f,
      status: key === 'todo' ? 'todo' : key === 'done' ? 'done' : '',
      priority: key === 'high' ? 'high' : key === 'all' ? '' : f.priority,
    }))
  }

  function toggleProject(id) {
    setFilter('project_id', filters.project_id == id ? '' : id)
    setSidebarOpen(false)
  }

  function toggleCategory(id) {
    setFilter('category_id', filters.category_id == id ? '' : id)
    setSidebarOpen(false)
  }

  function openModal(next) {
    setSidebarOpen(false)
    setModal(next)
  }

  const renderTask = t => (
    <TaskCard
      key={t.id}
      task={t}
      projectName={projectNames[t.project_id]}
      onEdit={task => setModal({ type: 'task', task })}
      onDelete={handleDelete}
      onToggle={handleToggle}
      onHistory={task => setModal({ type: 'history', task })}
    />
  )

  return (
    <div className="app-shell grid-paper">
      <Sidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        counts={counts}
        activeNav={activeNav}
        onSelectNav={selectNav}
        projects={projects}
        selectedProjectId={filters.project_id}
        onSelectProject={toggleProject}
        onOpenMembers={project => openModal({ type: 'members', project })}
        onNewProject={() => openModal({ type: 'project' })}
        categories={categories}
        selectedCategoryId={filters.category_id}
        onSelectCategory={toggleCategory}
        onDeleteCategory={handleDeleteCategory}
        onNewCategory={() => openModal({ type: 'category' })}
        userEmail={userEmail}
        onLogout={() => { api.logout(); onLogout() }}
      />

      <div className="main">
        <header className="topbar">
          <div className="topbar-left">
            <button className="icon-button topbar-menu" aria-label="Otwórz menu" onClick={() => setSidebarOpen(true)}>
              <Icon name="menu" />
            </button>
            <div style={{ minWidth: 0 }}>
              <p className="eyebrow">{eyebrow}</p>
              <h1 className="page-title">{pageTitle}</h1>
            </div>
          </div>
          <span
            className="live-status"
            data-status={projectsStatus}
            title="Projekty aktualizują się na żywo przez WebSocket"
          >
            {LIVE_STATUS_LABEL[projectsStatus]}
          </span>
        </header>

        <div className="content">
          {/* Hero */}
          <section className="hero-panel">
            <div className="hero-grid">
              <div>
                <div className="hero-kicker">
                  <span className="hero-kicker-line" />
                  Twój dzisiejszy plan
                </div>
                <p className="hero-title">
                  Mniej chaosu.
                  <br />
                  <span>Więcej zrobione.</span>
                </p>
                <p className="hero-description">
                  Wszystkie zadania, terminy i priorytety w jednym spokojnym miejscu.
                </p>
              </div>
              <div className="hero-score">
                <div className="score-orbit">
                  <span className="score-number">{dueToday.length}</span>
                  <span className="score-label">{pluralTasks(dueToday.length)} dziś</span>
                </div>
                <div className="score-note">
                  <Icon name="sparkles" size={15} />
                  {dueToday.length === 0 ? 'Czysta karta' : 'Do dzieła'}
                </div>
              </div>
            </div>
            <div className="hero-stats">
              <div><span>{pad2(todo.length)}</span>Do zrobienia</div>
              <div><span>{pad2(done.length)}</span>Ukończone</div>
              <div><span>{pad2(high.length)}</span>Pilne</div>
            </div>
          </section>

          {/* View + filters */}
          <section className="filter-panel">
            <div className="filter-row">
              <div className="filter-rail">
                <button className={`filter-tab ${view === 'all' ? 'active' : ''}`} onClick={() => setView('all')}>Wszystkie</button>
                <button className={`filter-tab filter-tab-alert ${view === 'overdue' ? 'active' : ''}`} data-filter="overdue" onClick={() => setView('overdue')}>
                  <Icon name="alert" size={15} />
                  Przeterminowane
                </button>
                <button className={`filter-tab ${view === 'upcoming' ? 'active' : ''}`} data-filter="upcoming" onClick={() => setView('upcoming')}>
                  <Icon name="clock" size={15} />
                  Nadchodzące (7 dni)
                </button>
              </div>
              <div className="filter-selects">
                <label className="select-wrap">
                  <select aria-label="Filtruj po statusie" value={filters.status} onChange={e => setFilter('status', e.target.value)}>
                    <option value="">Wszystkie statusy</option>
                    <option value="todo">Do zrobienia</option>
                    <option value="done">Ukończone</option>
                  </select>
                  <Icon name="chevron" size={14} />
                </label>
                <label className="select-wrap">
                  <select aria-label="Filtruj po priorytecie" value={filters.priority} onChange={e => setFilter('priority', e.target.value)}>
                    <option value="">Wszystkie priorytety</option>
                    <option value="high">Wysoki</option>
                    <option value="medium">Średni</option>
                    <option value="low">Niski</option>
                  </select>
                  <Icon name="chevron" size={14} />
                </label>
              </div>
            </div>
          </section>

          {/* Search + new task */}
          <div className="toolbar">
            <label className="search-field">
              <Icon name="search" size={17} />
              <input
                placeholder="Filtruj po tagu…"
                value={tagSearch}
                onChange={e => { setTagSearch(e.target.value); setFilter('tag', e.target.value) }}
              />
            </label>
            <button className="btn btn-primary" onClick={() => setModal({ type: 'task', task: null })}>
              <Icon name="plus" size={18} />
              Nowe zadanie
            </button>
          </div>

          {/* Task board */}
          <section className="task-board">
            <div className="task-board-header">
              <div className="board-crumb">
                <span className="category-mark"><Icon name="tag" size={17} /></span>
                <span>
                  Kategoria
                  <small>/ {activeCategory ? activeCategory.name : 'Wszystkie'}</small>
                </span>
              </div>
              <span className="board-count">{tasks.length}</span>
            </div>

            {loading ? (
              <div className="board-loading"><span className="spinner spinner-lg" /></div>
            ) : tasks.length === 0 ? (
              <EmptyState filtered={hasActiveFilters} onAdd={() => setModal({ type: 'task', task: null })} />
            ) : (
              <>
                {todo.length > 0 && (
                  <section className="board-section">
                    <h2 className="board-section-title">Do zrobienia ({todo.length})</h2>
                    <div className="task-list">{todo.map(renderTask)}</div>
                  </section>
                )}
                {done.length > 0 && (
                  <section className="board-section">
                    <h2 className="board-section-title">Ukończone ({done.length})</h2>
                    <div className="task-list">{done.map(renderTask)}</div>
                  </section>
                )}
              </>
            )}
          </section>
        </div>
      </div>

      {/* Modals */}
      {modal?.type === 'task' && (
        <TaskModal
          task={modal.task}
          categories={categories}
          projects={projects}
          onSave={handleSaveTask}
          onClose={() => setModal(null)}
        />
      )}
      {modal?.type === 'history' && (
        <HistoryModal
          task={modal.task}
          categories={categories}
          projects={projects}
          members={membersByProject[modal.task.project_id]}
          onClose={() => setModal(null)}
        />
      )}
      {modal?.type === 'category' && (
        <CategoryModal
          onSave={handleSaveCategory}
          onClose={() => setModal(null)}
        />
      )}
      {modal?.type === 'project' && (
        <ProjectModal onSave={handleSaveProject} onClose={() => setModal(null)} />
      )}
      {modal?.type === 'members' && (
        <MembersModal
          project={modal.project}
          members={membersByProject[modal.project.id]}
          userEmail={userEmail}
          connected={projectsStatus === 'online'}
          send={sendProjectCommand}
          onClose={() => setModal(null)}
        />
      )}
    </div>
  )
}

// ── Root App ──────────────────────────────────────────────────────────────────
export default function App() {
  const [user, setUser] = useState(() => {
    const token = localStorage.getItem('token')
    const email = localStorage.getItem('userEmail')
    return token ? { email } : null
  })

  function handleLogin(email) {
    localStorage.setItem('userEmail', email)
    setUser({ email })
  }

  function handleLogout() {
    localStorage.removeItem('userEmail')
    setUser(null)
  }

  return (
    <ToastProvider>
      {user
        ? <Dashboard userEmail={user.email} onLogout={handleLogout} />
        : <AuthPage onLogin={handleLogin} />
      }
    </ToastProvider>
  )
}
