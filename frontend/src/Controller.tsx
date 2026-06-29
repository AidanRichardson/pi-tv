import { Button } from "@/components/ui/button"
import { ArrowLeft, Play, Radio } from "lucide-react"
import { useEffect, useState } from "react"
import { Link } from "react-router"

interface Group {
  group_id: number
  name: string
}

interface Programme {
  title: string
  start_time: string
  stop_time: string
}

interface Channel {
  id: number
  channel_id: string
  name: string
  logo: string
  ts: string
  group_id: number
  programme: Programme
}

interface Status {
  channel_id: number
}

function Controller() {
  const [groups, setGroups] = useState<Group[]>([])
  const [channels, setChannels] = useState<Channel[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [currentId, setCurrentId] = useState<number | null>(null)
  const [selectedGroup, setSelectedGroup] = useState<Group | null>(null)

  useEffect(() => {
    async function init() {
      try {
        const [groupsRes, statusRes] = await Promise.all([
          fetch("/api/groups"),
          fetch("/api/status"),
        ])

        const groupsData = await groupsRes.json()
        const statusData = (await statusRes.json()) as Status

        setGroups(groupsData)
        setCurrentId(statusData.channel_id)
      } catch (error) {
        console.error("Failed to fetch initial data:", error)
      } finally {
        setIsLoading(false)
      }
    }
    init()
  }, [])

  useEffect(() => {
    async function fetchChannels() {
      if (!selectedGroup) {
        setChannels([])
        return
      }

      try {
        const response = await fetch(`api/channels/${selectedGroup.group_id}`)
        const data = await response.json()
        setChannels(data)
      } catch (error) {
        console.error("Failed to fetch channels:", error)
      }
    }
    fetchChannels()
  }, [selectedGroup])

  async function switchChannel(id: number) {
    if (id === currentId) return
    try {
      setCurrentId(id)
      await fetch(`/api/switch/${id}`)
    } catch (error) {
      console.error("Failed to switch channel:", error)
    }
  }

  if (isLoading) {
    return (
      <div className="flex min-h-[50vh] flex-col items-center justify-center space-y-4">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        <p className="text-sm font-medium text-muted-foreground">
          Loading lineup...
        </p>
      </div>
    )
  }

  if (selectedGroup) {
    return (
      <div className="container mx-auto max-w-7xl space-y-6 p-4 md:p-6 lg:p-8">
        <div className="relative flex min-h-14 items-center justify-center">
          <button
            onClick={() => setSelectedGroup(null)}
            className="absolute left-0 flex rounded-2xl p-2 hover:cursor-pointer hover:text-primary"
          >
            <ArrowLeft size={40} />
          </button>

          <div className="text-center">
            <h2 className="text-2xl font-bold tracking-tight">
              {selectedGroup.name}
            </h2>
            <p className="text-sm text-muted-foreground">
              Select a channel to tune in
            </p>
          </div>
        </div>

        {channels.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-16 text-center text-muted-foreground">
            <Radio className="mb-4 h-10 w-10 opacity-20" />
            <p>No channels found in this group.</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
            {channels.map((channel) => {
              const isActive = currentId === channel.id

              return (
                <div
                  key={channel.id}
                  className={`group relative cursor-pointer overflow-hidden rounded-xl bg-card transition-all duration-200 hover:-translate-y-1 hover:shadow-md ${
                    isActive
                      ? "border-transparent bg-card text-primary ring-2 ring-primary"
                      : "hover:border hover:border-primary"
                  }`}
                  onClick={() => switchChannel(channel.id)}
                >
                  {isActive && (
                    <div className="absolute top-0 right-0 rounded-bl-lg bg-primary px-2 py-1 text-[9px] font-bold tracking-wider text-primary-foreground uppercase shadow-sm">
                      Playing
                    </div>
                  )}

                  <div className="flex aspect-square h-full flex-col items-center justify-center gap-y-2 p-4">
                    <div className="relative mb-3 flex w-full flex-1 items-center justify-center">
                      <img
                        src={channel.logo}
                        className="max-h-12 w-auto object-contain drop-shadow-sm transition-transform duration-200 group-hover:scale-110"
                      />
                    </div>
                    <h1 className="w-full text-center leading-tight font-medium group-hover:text-primary">
                      {channel.name}
                    </h1>
                    {channel["programme"] && (
                      <h2 className="w-full text-center text-sm leading-tight text-muted-foreground group-hover:text-primary">
                        {channel["programme"]["title"]}
                      </h2>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="container mx-auto max-w-7xl p-4 md:p-6 lg:p-3">
      <div className="flex flex-col items-center justify-center space-y-4 py-8 text-center">
        <h1 className="text-4xl font-extrabold tracking-tight lg:text-5xl">
          Channel Lineup
        </h1>
        <p className="max-w-150 text-muted-foreground">
          Select a category below to browse channels, or jump straight into the
          player.
        </p>
        <Button asChild size="lg" className="mt-2 rounded-full px-8 shadow-md">
          <Link to="/">
            <Play className="mr-2 h-5 w-5 fill-current" /> WATCH NOW
          </Link>
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
        {groups.map((group) => (
          <div
            key={group.group_id}
            className="group cursor-pointer rounded-xl border bg-card p-4 text-center transition-all duration-200 hover:-translate-y-1 hover:border-primary hover:shadow-md"
            onClick={() => setSelectedGroup(group)}
          >
            <h1 className="text-lg font-semibold transition-colors group-hover:text-primary">
              {group.name}
            </h1>
          </div>
        ))}
      </div>
    </div>
  )
}

export default Controller
