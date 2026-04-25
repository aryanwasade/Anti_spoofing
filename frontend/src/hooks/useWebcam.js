/**
 * useWebcam — manages getUserMedia stream and canvas frame capture.
 * Returns: { videoRef, canvasRef, startCamera, stopCamera, captureFrame, isReady }
 *
 * FIXED: captureFrame no longer depends on `isReady` React state (stale closure bug).
 * Instead it checks video.readyState >= 2 directly at call time.
 * This means the interval in CandidatePage will always capture valid frames
 * as soon as the camera is ready, regardless of when the closure was created.
 */
import { useRef, useState, useCallback } from 'react'

export default function useWebcam(width = 640, height = 480) {
  const videoRef   = useRef(null)
  const canvasRef  = useRef(null)
  const streamRef  = useRef(null)
  const [isReady, setIsReady] = useState(false)
  const [error, setError]     = useState(null)

  const startCamera = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width, height, facingMode: 'user', frameRate: { ideal: 15 } },
        audio: false,
      })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
        setIsReady(true)
        setError(null)
      }
    } catch (err) {
      setError(err.message || 'Camera access denied')
    }
  }, [width, height])

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach(t => t.stop())
    streamRef.current = null
    if (videoRef.current) videoRef.current.srcObject = null
    setIsReady(false)
  }, [])

  /**
   * Captures the current video frame onto the canvas and returns base64 JPEG.
   * Uses video.readyState >= 2 instead of isReady state to avoid stale closure issues.
   * @param {number} quality 0-1
   */
  const captureFrame = useCallback((quality = 0.6) => {
    const video  = videoRef.current
    const canvas = canvasRef.current
    // Check readyState directly — avoids stale closure from React state
    if (!video || !canvas || video.readyState < 2) return null
    if (video.videoWidth === 0 || video.videoHeight === 0) return null

    canvas.width  = video.videoWidth  || width
    canvas.height = video.videoHeight || height
    const ctx = canvas.getContext('2d')
    // Draw mirrored to match what the user sees (scaleX(-1) CSS)
    ctx.save()
    ctx.scale(-1, 1)
    ctx.drawImage(video, -canvas.width, 0, canvas.width, canvas.height)
    ctx.restore()
    return canvas.toDataURL('image/jpeg', quality)
  }, [width, height])   // NOTE: no isReady dep — prevents stale closure

  return { videoRef, canvasRef, startCamera, stopCamera, captureFrame, isReady, error }
}
