"use client"

import Hls from "hls.js"
import { Tv2 } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { Link } from "react-router"
import { Button } from "./components/ui/button"

interface Status {
  channel: string
}

export function App() {
  const videoRef = useRef<HTMLVideoElement>(null)
  const hlsRef = useRef<Hls | null>(null)
  const [currentChannel, setCurrentChannel] = useState<string | null>(null)

  useEffect(() => {
    async function init() {
      const statusRes = await fetch("/api/status")

      const statusData = (await statusRes.json()) as Status

      setCurrentChannel(statusData.channel)
    }
    const video = videoRef.current
    if (!video) return

    init()

    const ws = new WebSocket(`ws://${window.location.host}/ws`)

    function createPlayer() {
      if (hlsRef.current) {
        hlsRef.current.destroy()
      }

      if (Hls.isSupported() && video) {
        const hls = new Hls()
        hlsRef.current = hls
        hls.loadSource("/api/hls/output.m3u8")
        hls.attachMedia(video)
        hls.on(Hls.Events.MANIFEST_PARSED, () => {
          video.play().catch((e) => console.error("Auto-play blocked", e))
        })
        hls.on(Hls.Events.ERROR, (_event, data) => {
          if (data.fatal) {
            hlsRef.current?.destroy()
            setTimeout(createPlayer, 3000)
          }
        })
      } else if (video && video.canPlayType("application/vnd.apple.mpegurl")) {
        video.src = "/api/hls/output.m3u8"
      }
    }

    ws.onmessage = (event) => {
      if (event.data === "switching") {
        video.pause()
      }
      if (event.data === "ready") {
        createPlayer()
      }
    }

    createPlayer()

    return () => {
      ws.close()
      if (hlsRef.current) hlsRef.current.destroy()
    }
  }, [])

  return (
    <div className="container mx-auto p-4 md:p-6 lg:p-3">
      <div className="flex flex-col items-center justify-center space-y-4 py-8 text-center">
        <h1 className="text-4xl font-extrabold tracking-tight lg:text-5xl">
          Live Player
        </h1>
        <p className="max-w-150 text-2xl text-muted-foreground">
          {currentChannel}
        </p>
        <Button asChild size="lg" className="mt-2 rounded-full px-8 shadow-md">
          <Link to="/controller">
            <Tv2 className="mr-2 h-5 w-5 fill-current" /> VIEW CHANNELS
          </Link>
        </Button>
      </div>

      <div className="relative flex w-full flex-1 items-center justify-center overflow-hidden rounded-2xl bg-black md:rounded-3xl">
        <video
          ref={videoRef}
          className="h-full w-full bg-black object-contain"
          controls
          autoPlay
          playsInline
        />
      </div>
    </div>
  )
}

export default App
