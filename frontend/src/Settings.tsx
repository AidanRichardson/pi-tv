"use client"

import { useEffect, useState } from "react"
import { Link } from "react-router"
import { Button } from "./components/ui/button"

type TestResult = {
  domain: string
  working: boolean
}

export function Settings() {
  const [domains, setDomains] = useState<string[]>([""])
  const [epgUrl, setEpgUrl] = useState<string>("")
  const [username, setUsername] = useState<string>("")
  const [password, setPassword] = useState<string>("")

  const [domainsChanged, setDomainsChanged] = useState(false)
  const [userPassChanged, setUserPassChanged] = useState(false)
  const [epgUrlChanged, setEpgUrlChanged] = useState(false)

  const [isLoading, setIsLoading] = useState(true)

  const [isTesting, setIsTesting] = useState(false)
  const [testResults, setTestResults] = useState<TestResult[]>([])
  const [hasTested, setHasTested] = useState(false)

  useEffect(() => {
    async function init() {
      try {
        const domainsRes = await fetch("/api/domains")
        const userpassRes = await fetch("/api/userpass")
        const epgurlRes = await fetch("/api/epgurl")
        const domainsData = await domainsRes.json()
        const userpassData = await userpassRes.json()
        const epgurlData = await epgurlRes.json()
        const fetchedDomains: string[] = []

        domainsData.forEach((element: { key: string; domain: string }) => {
          fetchedDomains.push(element["domain"])
        })

        setDomains(fetchedDomains)
        setEpgUrl(epgurlData["epg_url"])
        setUsername(userpassData["username"])
        setPassword(userpassData["password"])
      } catch (error) {
        console.error("Failed to fetch initial data:", error)
      } finally {
        setIsLoading(false)
      }
    }
    init()
  }, [])

  async function save() {
    if (domainsChanged) {
      const res = await fetch("/api/domains", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ domains }),
      })
      if (!res.ok) throw new Error("Save failed")
    }

    if (userPassChanged) {
      const res = await fetch("/api/userpass", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: username, password: password }),
      })
      if (!res.ok) throw new Error("Save failed")
    }

    if (epgUrlChanged) {
      const res = await fetch("/api/epgurl", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ epg_url: epgUrl }),
      })
      if (!res.ok) throw new Error("Save failed")
    }
  }

  async function testDomains() {
    setIsTesting(true)
    setHasTested(false)
    try {
      const res = await fetch("/api/domains-test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ domains }),
      })

      if (res.ok) {
        const data: TestResult[] = await res.json()
        setTestResults(data)
        setHasTested(true)
      }
    } catch (error) {
      console.error("Failed to test domains:", error)
    } finally {
      setIsTesting(false)
    }
  }

  function removeBrokenDomains() {
    const workingDomains = domains.filter((d) => {
      const result = testResults.find((r) => r.domain === d)
      return result ? result.working : true
    })

    setDomains(workingDomains.length > 0 ? workingDomains : [""])
    setDomainsChanged(true)
    setHasTested(false)
    setTestResults([])
  }

  function addDomain() {
    setDomains([...domains, ""])
    setDomainsChanged(true)
  }

  function updateDomain(i: number, val: string) {
    setDomains(domains.map((d, idx) => (idx === i ? val : d)))
    setDomainsChanged(true)
  }

  function removeDomain(i: number) {
    setDomains(domains.filter((_, idx) => idx !== i))
    setDomainsChanged(true)
  }

  const workingCount = testResults.filter((r) => r.working).length
  const brokenCount = testResults.filter((r) => !r.working).length

  if (isLoading) {
    return (
      <div className="flex min-h-[50vh] flex-col items-center justify-center space-y-4">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        <p className="text-sm font-medium text-muted-foreground">Loading...</p>
      </div>
    )
  }

  return (
    <div className="container mx-auto max-w-2xl space-y-10 p-4 md:p-6 lg:p-8">
      <div className="space-y-1.5">
        <h1 className="font-bold tracking-wider text-primary/85">EPG url</h1>
        <label className="text-xs font-medium tracking-wider text-muted-foreground uppercase">
          EPG url
        </label>
        <input
          value={epgUrl}
          onChange={(e) => {
            setEpgUrl(e.target.value)
            setEpgUrlChanged(true)
          }}
          placeholder="epg_url"
          className="w-full border border-border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground/50 focus:border-primary focus:outline-none"
        />
      </div>
      <div className="space-y-1.5">
        <h1 className="font-bold tracking-wider text-primary/85">
          Provider Username/Password
        </h1>
        <label className="text-xs font-medium tracking-wider text-muted-foreground uppercase">
          Username
        </label>
        <input
          value={username}
          onChange={(e) => {
            setUsername(e.target.value)
            setUserPassChanged(true)
          }}
          placeholder="provider_username"
          className="w-full border border-border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground/50 focus:border-primary focus:outline-none"
        />

        <label className="text-xs font-medium tracking-wider text-muted-foreground uppercase">
          Password
        </label>
        <input
          value={password}
          onChange={(e) => {
            setPassword(e.target.value)
            setUserPassChanged(true)
          }}
          placeholder="provider_password"
          className="w-full border border-border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground/50 focus:border-primary focus:outline-none"
        />
      </div>

      <div className="space-y-1.5">
        <h1 className="font-bold tracking-wider text-primary/85">Domains</h1>
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
          disabled={isTesting}
          className="w-full border border-dashed border-border py-2 text-xs text-muted-foreground transition-all hover:border-primary/50 hover:text-primary disabled:opacity-50"
        >
          + add domain
        </button>

        <button
          onClick={testDomains}
          disabled={isTesting}
          className="w-full border border-dashed border-green-400 py-2 text-xs text-green-400 transition-all hover:border-green-400/80 hover:text-green-400/80 disabled:opacity-50"
        >
          {isTesting ? "Loading..." : "Test Domains"}
        </button>

        {hasTested && (
          <div className="space-y-2 pt-2 text-center">
            <p className="text-sm font-medium text-muted-foreground">
              {workingCount} / {testResults.length} Domains Working
            </p>

            {brokenCount > 0 && (
              <button
                onClick={removeBrokenDomains}
                className="w-full border border-dashed border-destructive py-2 text-xs text-destructive transition-all hover:border-destructive/80 hover:text-destructive/80 disabled:opacity-50"
              >
                Remove {brokenCount} Broken Domain{brokenCount > 1 ? "s" : ""}
              </button>
            )}
          </div>
        )}
      </div>

      <div className="flex justify-center">
        <Button
          asChild
          size="lg"
          className="mt-2 rounded-full px-8 shadow-md"
          onClick={save}
        >
          <Link to="/">
            <p className="text-lg font-bold">Save</p>
          </Link>
        </Button>
      </div>
    </div>
  )
}

export default Settings
