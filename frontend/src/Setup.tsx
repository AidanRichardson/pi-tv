import { Fragment, useRef, useState } from "react"
import { useNavigate } from "react-router"
import { Button } from "./components/ui/button"

type Step = "upload" | "credentials" | "complete"
type uploadType = "file" | "url"

export default function Setup() {
  const navigate = useNavigate()
  const [step, setStep] = useState<Step>("upload")
  const [m3uParsed, setM3uParsed] = useState(false)
  const [m3uUploaded, setM3uUploaded] = useState(false)
  const [parsing, setParsing] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [domains, setDomains] = useState<string[]>([""])
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const [dragOver, setDragOver] = useState(false)
  const [parseProgress, setParseProgress] = useState(0)
  const [uploadType, setUploadType] = useState<uploadType>("file")
  const [m3uUrl, setM3uUrl] = useState("")

  async function handleFileUpload(file: File) {
    if (!file) return
    setUploadError(null)
    setParseProgress(0)

    const form = new FormData()
    form.append("file", file)

    try {
      const res = await fetch("/api/setup/upload-m3u", {
        method: "POST",
        body: form,
      })
      if (!res.ok) throw new Error("Upload failed")
    } catch {
      setUploadError("Failed to upload playlist. Check the file and try again.")
    } finally {
      setM3uUploaded(true)
    }
  }

  async function parsePlaylist() {
    console.log(m3uUrl)
    if (uploadType == "url") {
      const res = await fetch("/api/setup/upload-url-m3u", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: m3uUrl }),
      })
      if (!res.ok) throw new Error("Upload failed")
    }
    setParsing(true)
    try {
      const res = await fetch("/api/setup/parse-playlist", {
        method: "GET",
      })
      if (!res.ok) throw new Error("Upload failed")

      const reader = res.body!.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        for (const line of decoder.decode(value).split("\n")) {
          if (!line.startsWith("data: ")) continue
          const data = JSON.parse(line.slice(6))
          setParseProgress(data.progress)
          if (data.done) setM3uParsed(true)
        }
      }
    } catch {
      setUploadError("Failed to upload playlist. Check the file and try again.")
    } finally {
      setParsing(false)
      setStep("credentials")
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFileUpload(file)
  }

  function addDomain() {
    setDomains([...domains, ""])
  }

  function updateDomain(i: number, val: string) {
    setDomains(domains.map((d, idx) => (idx === i ? val : d)))
  }

  function removeDomain(i: number) {
    setDomains(domains.filter((_, idx) => idx !== i))
  }

  async function handleComplete() {
    setSubmitting(true)
    setSubmitError(null)
    try {
      const res = await fetch("/api/setup/complete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password, domains }),
      })
      if (!res.ok) throw new Error("Setup failed")
      setStep("complete")
      setTimeout(() => navigate("/controller"), 1500)
    } catch (e) {
      setSubmitError("Something went wrong. Please try again.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="container mx-auto p-4 md:p-6 lg:p-8">
      {/* Logo */}
      <div className="flex flex-col items-center justify-center space-y-2 py-10 text-center">
        <h1 className="text-4xl font-extrabold tracking-tight lg:text-5xl">
          Setup
        </h1>
        <p className="text-sm text-muted-foreground">
          Configure PI-TV in a few steps
        </p>
      </div>

      <div className="mx-auto mb-10 flex w-full max-w-xl items-center">
        {(["upload", "credentials", "complete"] as Step[]).map((s, i) => (
          <Fragment key={s}>
            <div
              className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-full border border-primary text-sm font-semibold text-primary transition-all ${
                step === s ? "bg-primary/20" : "bg-background"
              }`}
            >
              {i + 1}
            </div>
            {i < 2 && <div className="h-px flex-1 bg-border" />}
          </Fragment>
        ))}
      </div>

      <div className="mx-auto w-full max-w-2xl space-y-6 border border-border bg-card/80 p-6">
        {step === "upload" && parsing && (
          <div>
            <div className="space-y-3">
              <p className="animate-pulse text-sm text-muted-foreground">
                Parsing playlist...
              </p>
              <div className="h-1 w-full bg-border">
                <div
                  className="h-1 bg-primary transition-all duration-300"
                  style={{ width: `${parseProgress}%` }}
                />
              </div>
              <p className="text-xs text-muted-foreground">{parseProgress}%</p>
            </div>
          </div>
        )}

        {step === "upload" && !parsing && (
          <>
            <div className="space-y-1">
              <h2 className="text-lg font-semibold tracking-tight">
                Upload playlist
              </h2>
              <p className="text-sm text-muted-foreground">
                Upload an M3U or M3U8 file containing your IPTV channels.
              </p>
            </div>
            <div className="flex space-x-1">
              <Button
                variant={uploadType == "file" ? "default" : "outline"}
                onClick={() => setUploadType("file")}
                disabled={m3uUploaded}
              >
                File Upload
              </Button>
              <Button
                variant={uploadType == "url" ? "default" : "outline"}
                onClick={() => setUploadType("url")}
                disabled={m3uUploaded}
              >
                URL
              </Button>
            </div>

            {uploadType == "url" ? (
              <div>
                <h2 className="text-lg font-semibold tracking-tight">
                  Playlist URL
                </h2>
                <label className="text-xs font-medium tracking-wider text-muted-foreground uppercase">
                  Link to Playlist
                </label>
                <input
                  onChange={(e) => setM3uUrl(e.target.value)}
                  placeholder="playlist_url"
                  className="w-full border border-border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground/50 focus:border-primary focus:outline-none"
                />
              </div>
            ) : (
              <div>
                <h2 className="text-lg font-semibold tracking-tight">
                  File Upload
                </h2>

                <div
                  onClick={() => fileRef.current?.click()}
                  onDragOver={(e) => {
                    e.preventDefault()
                    setDragOver(true)
                  }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={handleDrop}
                  className={`cursor-pointer space-y-1 border border-dashed p-12 text-center transition-all ${
                    dragOver
                      ? "border-primary bg-primary/10"
                      : m3uParsed
                        ? "border-primary bg-primary/10"
                        : "border-border bg-transparent hover:border-primary/50 hover:bg-primary/5"
                  }`}
                >
                  <input
                    ref={fileRef}
                    type="file"
                    accept=".m3u,.m3u8"
                    className="hidden"
                    onChange={(e) =>
                      e.target.files?.[0] && handleFileUpload(e.target.files[0])
                    }
                  />
                  {m3uUploaded ? (
                    <p className="text-sm font-medium text-primary">
                      Playlist uploaded successfully
                    </p>
                  ) : (
                    <>
                      <p className="text-sm font-medium">
                        Drop your M3U file here
                      </p>
                      <p className="text-xs text-muted-foreground">
                        or click to browse
                      </p>
                    </>
                  )}
                </div>
              </div>
            )}

            {uploadError && (
              <p className="text-xs text-destructive">{uploadError}</p>
            )}

            <button
              onClick={() => {
                parsePlaylist()
              }}
              disabled={!m3uUploaded && uploadType == "file"}
              className={`w-full p-2.5 text-sm font-medium transition-all ${
                m3uUploaded || uploadType == "url"
                  ? "cursor-pointer bg-primary text-primary-foreground hover:bg-primary/90"
                  : "cursor-not-allowed bg-muted text-muted-foreground"
              }`}
            >
              Continue
            </button>
          </>
        )}

        {step === "credentials" && (
          <>
            <div className="space-y-1">
              <h2 className="text-lg font-semibold tracking-tight">
                Provider details
              </h2>
              <p className="text-sm text-muted-foreground">
                Enter your IPTV provider credentials and stream domains.
                Multiple domains can be added as fallbacks.
              </p>
            </div>

            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium tracking-wider text-muted-foreground uppercase">
                  Username
                </label>
                <input
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="provider_username"
                  className="w-full border border-border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground/50 focus:border-primary focus:outline-none"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium tracking-wider text-muted-foreground uppercase">
                  Password
                </label>
                <input
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="provider_password"
                  className="w-full border border-border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground/50 focus:border-primary focus:outline-none"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium tracking-wider text-muted-foreground uppercase">
                  Domains
                </label>
                <div className="space-y-2">
                  {domains.map((d, i) => (
                    <div key={i} className="flex gap-2">
                      <input
                        value={d}
                        onChange={(e) => updateDomain(i, e.target.value)}
                        placeholder="streams.provider.com"
                        className="flex-1 border border-border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground/50 focus:border-primary focus:outline-none"
                      />
                      {domains.length > 1 && (
                        <button
                          onClick={() => removeDomain(i)}
                          className="border border-border px-3 text-muted-foreground transition-all hover:border-destructive hover:text-destructive"
                        >
                          ×
                        </button>
                      )}
                    </div>
                  ))}
                </div>
                <button
                  onClick={addDomain}
                  className="w-full border border-dashed border-border py-2 text-xs text-muted-foreground transition-all hover:border-primary/50 hover:text-primary"
                >
                  + add domain
                </button>
              </div>
            </div>

            {submitError && (
              <p className="text-xs text-destructive">{submitError}</p>
            )}

            <div className="flex gap-2">
              <button
                onClick={() => setStep("upload")}
                className="flex-1 border border-border py-2.5 text-sm text-muted-foreground transition-all hover:border-primary/50 hover:text-foreground"
              >
                Back
              </button>
              <button
                onClick={handleComplete}
                disabled={
                  submitting ||
                  !username ||
                  !password ||
                  domains.every((d) => !d.trim())
                }
                className={`flex-2 py-2.5 text-sm font-medium transition-all ${
                  !username || !password || domains.every((d) => !d.trim())
                    ? "cursor-not-allowed bg-muted text-muted-foreground"
                    : "cursor-pointer bg-primary text-primary-foreground hover:bg-primary/90"
                }`}
              >
                {submitting ? "Finishing..." : "Finish setup"}
              </button>
            </div>
          </>
        )}

        {step === "complete" && (
          <div className="flex flex-col items-center space-y-3 py-6 text-center">
            <div className="flex h-12 w-12 items-center justify-center border border-primary text-primary">
              ✓
            </div>
            <div className="space-y-1">
              <h2 className="text-lg font-semibold tracking-tight">
                Setup complete
              </h2>
              <p className="text-sm text-muted-foreground">
                Redirecting to controller...
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
