import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import "./App.css";

// Register Service Worker for Step 81 PWA installation & safe static caching
if (typeof window !== "undefined" && "serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker
      .register("/sw.js")
      .then((registration) => {
        console.debug("TravelSync ServiceWorker registered with scope:", registration.scope);
      })
      .catch((error) => {
        console.warn("TravelSync ServiceWorker registration failed:", error);
      });
  });
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
