import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom'
import Home from './pages/Home'
import Wizard from './pages/Wizard'
import RunView from './pages/RunView'
import Results from './pages/Results'
import Compare from './pages/Compare'

export default function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <header>
          <h1>VLM Benchmark</h1>
          <nav>
            <NavLink to="/" end>Home</NavLink>
            <NavLink to="/wizard">New Benchmark</NavLink>
            <NavLink to="/compare">Compare</NavLink>
          </nav>
        </header>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/wizard" element={<Wizard />} />
          <Route path="/runs/:id" element={<RunView />} />
          <Route path="/runs/:id/results" element={<Results />} />
          <Route path="/compare" element={<Compare />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
