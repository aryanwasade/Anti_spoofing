/**
 * useWebSocket — manages WebSocket lifecycle + message parsing.
 * Returns: { connect, disconnect, send, lastMessage, status }
 * status: 'idle' | 'connecting' | 'open' | 'closed' | 'error'
 */
import { useRef, useState, useCallback } from 'react'

export default function useWebSocket(url) {
  const wsRef = useRef(null)
  const [status, setStatus]           = useState('idle')
  const [lastMessage, setLastMessage] = useState(null)

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return
    setStatus('connecting')
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen  = () => setStatus('open')
    ws.onclose = () => setStatus('closed')
    ws.onerror = () => setStatus('error')
    ws.onmessage = (e) => {
      try { setLastMessage(JSON.parse(e.data)) } catch {}
    }
  }, [url])

  const disconnect = useCallback(() => {
    wsRef.current?.close()
    wsRef.current = null
  }, [])

  const send = useCallback((data) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(typeof data === 'string' ? data : JSON.stringify(data))
    }
  }, [])

  return { connect, disconnect, send, lastMessage, status }
}
