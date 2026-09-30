import { apiRequest } from './client';
import type {
  GovernmentRecordsResponse,
  MarksheetHistoryResponse,
  StudentDocumentLink,
  StudentSummary,
} from '../types/api';

export function listStudents(): Promise<StudentSummary[]> {
  return apiRequest<StudentSummary[]>('/students');
}

export function getStudentDocuments(studentRef: string): Promise<StudentDocumentLink[]> {
  return apiRequest<StudentDocumentLink[]>(`/students/${encodeURIComponent(studentRef)}/documents`);
}

export function getGovernmentRecords(studentRef: string): Promise<GovernmentRecordsResponse> {
  return apiRequest<GovernmentRecordsResponse>(
    `/students/${encodeURIComponent(studentRef)}/government-records`
  );
}

export function getMarksheetHistory(studentRef: string): Promise<MarksheetHistoryResponse> {
  return apiRequest<MarksheetHistoryResponse>(`/students/${encodeURIComponent(studentRef)}/marksheets`);
}
