import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppLayout } from './components/AppLayout';
import { GuestOnly, RequireDemoSession } from './components/RequireDemoSession';
import { UploadPage } from './pages/UploadPage';
import { DocumentDetailPage } from './pages/DocumentDetailPage';
import { VerificationResultPage } from './pages/VerificationResultPage';
import { ReviewPage } from './pages/ReviewPage';
import { BlockchainReceiptPage } from './pages/BlockchainReceiptPage';
import { BlockchainReceiptsPage } from './pages/BlockchainReceiptsPage';
import { DemoDashboardPage } from './pages/DemoDashboardPage';
import { DashboardPage } from './pages/DashboardPage';
import { DocumentsPage } from './pages/DocumentsPage';
import { ReviewQueuePage } from './pages/ReviewQueuePage';
import { HistoryPage } from './pages/HistoryPage';
import { ProfilePage } from './pages/ProfilePage';
import { HelpPage } from './pages/HelpPage';
import { AboutPage } from './pages/AboutPage';
import { AuthPage } from './pages/AuthPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={
            <GuestOnly>
              <AuthPage mode="login" />
            </GuestOnly>
          }
        />
        <Route
          path="/register"
          element={
            <GuestOnly>
              <AuthPage mode="register" />
            </GuestOnly>
          }
        />
        <Route element={<RequireDemoSession />}>
          <Route element={<AppLayout />}>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/verify" element={<UploadPage />} />
            <Route path="/documents" element={<DocumentsPage />} />
            <Route path="/documents/:documentId" element={<DocumentDetailPage />} />
            <Route path="/review-queue" element={<ReviewQueuePage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/blockchain-receipts" element={<BlockchainReceiptsPage />} />
            <Route path="/verifications/:verificationId" element={<VerificationResultPage />} />
            <Route path="/verifications/:verificationId/review" element={<ReviewPage />} />
            <Route path="/verifications/:verificationId/blockchain" element={<BlockchainReceiptPage />} />
            <Route path="/demo" element={<DemoDashboardPage />} />
            <Route path="/demo/:documentId" element={<DemoDashboardPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/help" element={<HelpPage />} />
            <Route path="/about" element={<AboutPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
