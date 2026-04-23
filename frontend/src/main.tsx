import React from 'react'
import ReactDOM from 'react-dom/client'
import { AuctionProvider } from './context/Auctioncontext'
import App from './App'

const rootEl = document.getElementById('root')!

ReactDOM.createRoot(rootEl).render(
  <React.StrictMode>
    <AuctionProvider>
      <App />
    </AuctionProvider>
  </React.StrictMode>
)