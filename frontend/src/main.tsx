import { StrictMode } from "react"
import { createRoot } from "react-dom/client"

import { ThemeProvider } from "@/components/theme-provider.tsx"
import { BrowserRouter, Route, Routes } from "react-router"
import App from "./App.tsx"
import Controller from "./Controller.tsx"
import "./index.css"
import Settings from "./Settings.tsx"
import Setup from "./Setup.tsx"

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<App />} />
          <Route path="controller" element={<Controller />} />
          <Route path="setup" element={<Setup />} />
          <Route path="settings" element={<Settings />} />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  </StrictMode>
)
