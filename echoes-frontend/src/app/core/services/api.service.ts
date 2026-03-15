import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { IntakeResponse } from '../models/intake-response.model';
import { QueryResponse } from '../models/query-response.model';
import { ValuesVector } from '../models/values-vector.model';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private baseUrl = environment.apiBaseUrl;

  constructor(private http: HttpClient) {}

  // Intake
  startIntake(): Observable<IntakeResponse> {
    return this.http.post<IntakeResponse>(`${this.baseUrl}/api/intake/start`, {});
  }

  respondIntake(sessionId: string, message: string): Observable<IntakeResponse> {
    return this.http.post<IntakeResponse>(`${this.baseUrl}/api/intake/respond`, {
      sessionId,
      userId: localStorage.getItem('echoes_user_id'),
      message,
    });
  }

  getIntakeStatus(userId: string): Observable<{ intakeCompleted: boolean }> {
    return this.http.get<{ intakeCompleted: boolean }>(
      `${this.baseUrl}/api/intake/status/${userId}`
    );
  }

  // Query
  submitQuery(decisionText: string): Observable<QueryResponse> {
    return this.http.post<QueryResponse>(`${this.baseUrl}/api/query`, {
      userId: localStorage.getItem('echoes_user_id'),
      decisionText,
    });
  }

  // Profile
  getProfile(userId: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/api/profile/${userId}`);
  }

  updateProfile(userId: string, valuesVector: ValuesVector): Observable<any> {
    return this.http.put(`${this.baseUrl}/api/profile/${userId}`, valuesVector);
  }

  getProfileHistory(userId: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/api/profile/${userId}/history`);
  }

  // Decisions
  logDecision(body: {
    userId: string;
    queryId?: string;
    decisionText: string;
    decisionType?: string;
    chosenPath?: string;
  }): Observable<any> {
    return this.http.post(`${this.baseUrl}/api/decisions`, body);
  }

  getDecisions(userId: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/api/decisions/${userId}`);
  }
}
