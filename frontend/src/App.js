import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from '@/contexts/AuthContext';
import { Toaster } from '@/components/ui/sonner';
import LandingPage from '@/pages/LandingPage';
import LoginPage from '@/pages/LoginPage';
import RegisterPage from '@/pages/RegisterPage';
import DashboardPage from '@/pages/DashboardPage';
import GroupSetupPage from '@/pages/GroupSetupPage';
import PreferenceSurveyPage from '@/pages/PreferenceSurveyPage';
import WaitingRoomPage from '@/pages/WaitingRoomPage';
import RecommendationsPage from '@/pages/RecommendationsPage';
import FeedbackPage from '@/pages/FeedbackPage';
import '@/App.css';

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="App">
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/group/create" element={<GroupSetupPage />} />
            <Route path="/group/:groupId/survey" element={<PreferenceSurveyPage />} />
            <Route path="/group/:groupId/waiting" element={<WaitingRoomPage />} />
            <Route path="/group/:groupId/recommendations" element={<RecommendationsPage />} />
            <Route path="/group/:groupId/feedback/:recommendationId" element={<FeedbackPage />} />
          </Routes>
          <Toaster richColors position="top-center" />
        </div>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;