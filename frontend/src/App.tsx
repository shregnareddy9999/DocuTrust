import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';

import { AppLayout } from './components/AppLayout';

import { DashboardPage } from './pages/DashboardPage';
import { UploadPage } from './pages/UploadPage';
import { DocumentsPage } from './pages/DocumentsPage';
import { DocumentDetailPage } from './pages/DocumentDetailPage';
import { AcademicSummaryPage } from './pages/AcademicSummaryPage';
import { AcademicSummaryDocumentPreviewPage } from './pages/AcademicSummaryDocumentPreviewPage';
import { ReviewQueuePage } from './pages/ReviewQueuePage';
import { HistoryPage } from './pages/HistoryPage';
import { BlockchainReceiptsPage } from './pages/BlockchainReceiptsPage';
import { VerificationResultPage } from './pages/VerificationResultPage';
import { ReviewPage } from './pages/ReviewPage';
import { BlockchainReceiptPage } from './pages/BlockchainReceiptPage';
import { DemoDashboardPage } from './pages/DemoDashboardPage';
import { ProfilePage } from './pages/ProfilePage';
import { HelpPage } from './pages/HelpPage';
import { AboutPage } from './pages/AboutPage';
import { AuthPage } from './pages/AuthPage';

import { RequireDemoSession, GuestOnly } from './components/RequireDemoSession';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>

        {/* Login */}
        <Route
          path="/login"
          element={
            <GuestOnly>
              <AuthPage mode="login" />
            </GuestOnly>
          }
        />

        {/* Register */}
        <Route
          path="/register"
          element={
            <GuestOnly>
              <AuthPage mode="register" />
            </GuestOnly>
          }
        />

        {/* Protected application */}
        <Route element={<RequireDemoSession />}>
          <Route element={<AppLayout />}>

            <Route
              path="/"
              element={<DashboardPage />}
            />

            <Route
              path="/verify"
              element={<UploadPage />}
            />

            <Route
              path="/documents"
              element={<DocumentsPage />}
            />

            <Route
              path="/academic-summary"
              element={<AcademicSummaryPage />}
            />

            <Route
              path="/academic-summary/document/:documentId"
              element={<AcademicSummaryDocumentPreviewPage />}
            />

            <Route
              path="/documents/:documentId"
              element={<DocumentDetailPage />}
            />

            <Route
              path="/review-queue"
              element={<ReviewQueuePage />}
            />

            <Route
              path="/history"
              element={<HistoryPage />}
            />

            <Route
              path="/blockchain-receipts"
              element={<BlockchainReceiptsPage />}
            />

            <Route
              path="/verifications/:verificationId"
              element={<VerificationResultPage />}
            />

            <Route
              path="/verifications/:verificationId/review"
              element={<ReviewPage />}
            />

            <Route
              path="/verifications/:verificationId/blockchain"
              element={<BlockchainReceiptPage />}
            />

            <Route
              path="/demo"
              element={<DemoDashboardPage />}
            />

            <Route
              path="/demo/:documentId"
              element={<DemoDashboardPage />}
            />

            <Route
              path="/profile"
              element={<ProfilePage />}
            />

            <Route
              path="/help"
              element={<HelpPage />}
            />

            <Route
              path="/about"
              element={<AboutPage />}
            />

            <Route path="*" element={<Navigate to="/" replace />} />

          </Route>
        </Route>

      </Routes>
    </BrowserRouter>
  );
}