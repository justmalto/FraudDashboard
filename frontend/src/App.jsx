import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'
import Navbar from './components/Navbar'
import LiveAlertPanel from './components/LiveAlertPanel'
import Analytics from './components/Analytics'

function App() {


  return (
    <div className='app'>
      <Navbar></Navbar>
      <div className='content'>
        <LiveAlertPanel></LiveAlertPanel>
        <div className='analytics-container'>
          <Analytics></Analytics>
        </div>
        
      </div>
    </div>

  )
}

export default App
