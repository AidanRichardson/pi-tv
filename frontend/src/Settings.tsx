"use client"

import { useEffect, useState } from "react"
import { Link } from "react-router"
import { Button } from "./components/ui/button"

export function Settings() {
  const [domains, setDomains] = useState<string[]>([""])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    async function init() {
      try {
        const domainsRes = await fetch("/api/domains")

        const domainsData = await domainsRes.json()

        const domains: string[] = []

        domainsData.forEach((element: { key: string; domain: string }) => {
          domains.push(element["domain"])
        })

        setDomains(domains)
      } catch (error) {
        console.error("Failed to fetch initial data:", error)
      } finally {
        setIsLoading(false)
      }
    }
    init()
  }, [])

  async function save() {
    const res = await fetch("/api/domains", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ domains }),
    })
    if (!res.ok) throw new Error("Save failed")
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
          className="w-full border border-dashed border-border py-2 text-xs text-muted-foreground transition-all hover:border-primary/50 hover:text-primary"
        >
          + add domain
        </button>
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
