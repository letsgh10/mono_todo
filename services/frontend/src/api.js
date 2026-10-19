const BASE = ''

function getToken() {
  return localStorage.getItem('token')
}

function authHeaders(extra = {}) {
  const token = getToken()
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  }
}

async function request(method, path, body, params) {
  let url = BASE + path
  if (params) {
    const q = new URLSearchParams()
    for (const [k, v] of Object.entries(params)) {
      if (v !== null && v !== undefined && v !== '') q.append(k, v)
    }
    const qs = q.toString()
    if (qs) url += '?' + qs
  }
  const res = await fetch(url, {
    method,
    headers: authHeaders(),
    body: body ? JSON.stringify(body) : undefined,
  })
  if (res.status === 204) return null
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || JSON.stringify(data))
  return data
}

export const api = {
  // Auth
  async register(email, password) {
    const res = await fetch('/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || JSON.stringify(data))
    return data
  },

  async login(email, password) {
    const body = new URLSearchParams({ username: email, password })
    const res = await fetch('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body,
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || JSON.stringify(data))
    localStorage.setItem('token', data.access_token)
    return data
  },

  logout() {
    localStorage.removeItem('token')
  },

  // Tasks
  getTasks(filters = {}) {
    return request('GET', '/tasks/', null, filters)
  },

  createTask(task, useAI = false) {
    return request('POST', '/tasks/', task, useAI ? { use_ai_priority: true } : null)
  },

  updateTask(id, data) {
    return request('PATCH', `/tasks/${id}`, data)
  },

  deleteTask(id) {
    return request('DELETE', `/tasks/${id}`)
  },

  addTag(taskId, name) {
    return request('POST', `/tasks/${taskId}/tags`, { name })
  },

  removeTag(taskId, tagName) {
    return request('DELETE', `/tasks/${taskId}/tags/${tagName}`)
  },

  reanalyzePriority(taskId) {
    return request('POST', `/tasks/${taskId}/reanalyze-priority`)
  },

  getTaskHistory(taskId) {
    return request('GET', `/tasks/${taskId}/history`)
  },

  getUpcomingTasks(days = 7) {
    return request('GET', '/tasks/upcoming', null, { days })
  },

  // Categories
  getCategories() {
    // There's no GET /categories in the API, but we'll cache from tasks
    return []
  },

  createCategory(name, color) {
    return request('POST', '/categories/', { name, color })
  },

  deleteCategory(id) {
    return request('DELETE', `/categories/${id}`)
  },

  // Projects — live over WebSocket, see connectProjects below
  connectProjects,
}

// ── Projects over WebSocket ───────────────────────────────────────────────────
// Protocol (see backend app/schemas/realtime.py):
//   client → server: { type: 'create_project' | 'list_members' | 'add_member' | 'remove_member', request_id, ... }
//                    create_project may carry member_emails: [] — registered users added as members at once
//   server → client: 'projects' (snapshot), 'project_added', 'project_removed', 'members',
//                    'member_added', 'member_removed', 'ack', 'error' — replies echo request_id.
//                    'task_created' | 'task_updated' | 'task_deleted' — a task the user can see
//                    changed (own or in a shared project); the dashboard reloads its list.

const WS_UNAUTHORIZED = 4401
const WS_RECONNECT_MAX_MS = 30000

const WS_ERROR_LABEL = {
  project_not_found: 'Projekt nie istnieje',
  not_member: 'Nie jesteś członkiem tego projektu',
  not_owner: 'Tylko właściciel projektu może zarządzać członkami',
  user_not_found: 'Nie ma użytkownika o tym adresie email',
  already_member: 'Ten użytkownik już należy do projektu',
  member_not_found: 'Ten użytkownik nie należy do projektu',
  cannot_remove_owner: 'Nie można usunąć właściciela projektu',
  invalid_message: 'Nieprawidłowe polecenie',
}

// Polish label for a server error; `email` (user_not_found) names the offending address.
function describeError(msg) {
  const label = WS_ERROR_LABEL[msg.code] ?? msg.detail
  return msg.email ? `${label}: ${msg.email}` : label
}

function projectsSocketUrl() {
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws'
  return `${protocol}://${location.host}/ws/projects?token=${encodeURIComponent(getToken() ?? '')}`
}

/**
 * Opens the projects WebSocket and keeps it alive (reconnects with backoff).
 *
 * onMessage(msg)  — every server event except ack/error
 * onStatus(s)     — 'connecting' | 'online' | 'offline' | 'unauthorized' (token rejected, no retry)
 *
 * Returns { send(command) → Promise resolved with the reply or rejected with Error, close() }.
 */
function connectProjects({ onMessage, onStatus }) {
  let socket = null
  let closed = false
  let attempt = 0
  let reconnectTimer = null
  let nextRequestId = 1
  const pending = new Map() // request_id → { resolve, reject }

  function failPending(reason) {
    for (const { reject } of pending.values()) reject(new Error(reason))
    pending.clear()
  }

  function handleMessage(event) {
    const msg = JSON.parse(event.data)
    const waiter = msg.request_id ? pending.get(msg.request_id) : null
    if (waiter) {
      pending.delete(msg.request_id)
      if (msg.type === 'error') waiter.reject(new Error(describeError(msg)))
      else waiter.resolve(msg)
    }
    if (msg.type === 'error' && !waiter) console.warn('projects socket:', msg.detail)
    if (msg.type !== 'ack' && msg.type !== 'error') onMessage(msg)
  }

  function open() {
    if (closed) return
    onStatus('connecting')
    socket = new WebSocket(projectsSocketUrl())
    socket.onopen = () => {
      attempt = 0
      onStatus('online')
    }
    socket.onmessage = handleMessage
    socket.onclose = event => {
      socket = null
      failPending('Połączenie z serwerem zostało przerwane')
      if (closed) return
      if (event.code === WS_UNAUTHORIZED) {
        onStatus('unauthorized')
        return
      }
      onStatus('offline')
      const delay = Math.min(1000 * 2 ** attempt, WS_RECONNECT_MAX_MS)
      attempt += 1
      reconnectTimer = setTimeout(open, delay)
    }
  }

  open()

  return {
    send(command) {
      return new Promise((resolve, reject) => {
        if (!socket || socket.readyState !== WebSocket.OPEN) {
          reject(new Error('Brak połączenia z serwerem'))
          return
        }
        const request_id = String(nextRequestId++)
        pending.set(request_id, { resolve, reject })
        socket.send(JSON.stringify({ ...command, request_id }))
      })
    },
    close() {
      closed = true
      clearTimeout(reconnectTimer)
      socket?.close()
    },
  }
}
