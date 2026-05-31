import { BrowserRouter, Routes, Route } from 'react-router-dom';
import './styles/App.css';
import Layout from './components/layout/Layout';
import HomePage from './pages/HomePage';
import RecommendPage from './pages/RecommendPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/recommend" element={<RecommendPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
