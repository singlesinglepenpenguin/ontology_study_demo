"""Reproducible account lifecycle fixes for the supplier React adapter."""

def apply(root, replace_once):
    app = root / 'src/App.tsx'
    replace_once(app, 'useCallback, useEffect }', 'useCallback, useEffect, useRef }')
    if '  const accountEpoch = useRef(0)' not in app.read_text():
        replace_once(app, '  const showLanding =', '''  const accountEpoch = useRef(0)
  const streamAbort = useRef<AbortController | null>(null)
  const clearAccountState = () => {
    streamAbort.current?.abort()
    streamAbort.current = null
    setSessionId(null)
    setSessions([])
    setMessages([])
    setTraceEvents([])
    setAwaitingConfirmation(false)
    setStartedChat(false)
    setShowWelcome(true)
    setActiveView('chat')
    setRightPanel(null)
    setLoading(false)
  }
  const showLanding =''')
    replace_once(app, '  const handleLogin = (loggedInUser: LoginUser) => {\n    setUser(loggedInUser)', '''  const handleLogin = (loggedInUser: LoginUser) => {
    if (__SUPPLIER_DEMO__) { accountEpoch.current += 1; clearAccountState() }
    setUser(loggedInUser)''')
    replace_once(app, '  const handleLogout = () => {\n    setUser(null)', '''  const handleLogout = async () => {
    if (__SUPPLIER_DEMO__) {
      accountEpoch.current += 1
      clearAccountState()
      try { await fetch('/api/logout', { method: 'POST' }) } catch {}
    }
    setUser(null)''')
    replace_once(app, "  const fetchSessions = () => {\n    fetch('/api/sessions').then(r => r.json()).then(data => {\n      setSessions", """  const fetchSessions = () => {
    if (__SUPPLIER_DEMO__ && !user) return
    const epoch = accountEpoch.current
    fetch('/api/sessions').then(async r => { if (!r.ok) throw new Error('读取会话失败'); return r.json() }).then(data => {
      if (__SUPPLIER_DEMO__ && epoch !== accountEpoch.current) return
      setSessions""")
    if '  const switchSession = async (sid: string) => {\n    try {' in app.read_text():
        replace_once(app, '  const switchSession = async (sid: string) => {\n    try {', '''  const switchSession = async (sid: string) => {
    const epoch = accountEpoch.current
    try {''')
    replace_once(app, '      if (!data.session) {', '      if (__SUPPLIER_DEMO__ && epoch !== accountEpoch.current) return\n      if (!data.session) {')
    # Only the history-loading occurrence, not logout/new-chat resets.
    replace_once(app, '      setAwaitingConfirmation(false)\n      setTraceEvents([])\n      setStartedChat(true)', '      setAwaitingConfirmation(Boolean(data.session.pending_action))\n      setTraceEvents([])\n      setStartedChat(true)')
    replace_once(app, '  useEffect(() => {\n    fetchSessions()', '  useEffect(() => {\n    if (__SUPPLIER_DEMO__ && !user) return\n    fetchSessions()')
    replace_once(app, '  }, [])\n\n  const handleTraceEvent', '  }, [user?.id])\n\n  const handleTraceEvent')
    replace_once(app, '  const sendMessage = async (message: string, confirmed: boolean) => {\n    setStartedChat', '  const sendMessage = async (message: string, confirmed: boolean) => {\n    const sendEpoch = accountEpoch.current\n    setStartedChat')
    replace_once(app, '    } finally {\n      setLoading(false)\n    }\n  }', '    } finally {\n      if (!__SUPPLIER_DEMO__ || sendEpoch === accountEpoch.current) setLoading(false)\n    }\n  }')
    # A conversation switch invalidates callbacks just like an account switch.
    replace_once(app, '  const showLanding =', '''  const invalidateConversation = () => {
    if (!__SUPPLIER_DEMO__) return
    accountEpoch.current += 1
    streamAbort.current?.abort()
    streamAbort.current = null
    setLoading(false)
  }
  const showLanding =''')
    replace_once(app, '  const switchSession = async (sid: string) => {\n    const epoch', '  const switchSession = async (sid: string) => {\n    invalidateConversation()\n    const epoch')
    replace_once(app, '  const newChat = () => {\n    setSessionId(null)', '  const newChat = () => {\n    invalidateConversation()\n    setSessionId(null)')
    replace_once(app, "    if (!window.confirm('确定要删除此会话吗？')) return\n    try {\n      await fetch", "    if (!window.confirm('确定要删除此会话吗？')) return\n    if (sessionId === sid) invalidateConversation()\n    const epoch = accountEpoch.current\n    try {\n      const response = await fetch")
    replace_once(app, "{ method: 'DELETE' })\n      if (sessionId === sid)", "{ method: 'DELETE' })\n      if (!response.ok || (__SUPPLIER_DEMO__ && epoch !== accountEpoch.current)) return\n      if (sessionId === sid)")
    replace_once(app, '        setMessages([])\n        setStartedChat(false)', '        setMessages([])\n        setAwaitingConfirmation(false)\n        setTraceEvents([])\n        setStartedChat(false)')
