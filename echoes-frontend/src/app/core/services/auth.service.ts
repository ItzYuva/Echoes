import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, tap } from 'rxjs';
import { environment } from '../../../environments/environment';

interface AuthResponse {
  userId: string;
  token: string;
  intakeCompleted: boolean;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private baseUrl = environment.apiBaseUrl;
  private userId$ = new BehaviorSubject<string | null>(this.getStoredUserId());
  private intakeCompleted$ = new BehaviorSubject<boolean>(this.getStoredIntakeStatus());

  constructor(private http: HttpClient) {}

  get isAuthenticated(): boolean {
    return !!this.getToken();
  }

  get userId(): string | null {
    return this.userId$.value;
  }

  get isIntakeCompleted(): boolean {
    return this.intakeCompleted$.value;
  }

  get intakeCompleted(): Observable<boolean> {
    return this.intakeCompleted$.asObservable();
  }

  register(): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${this.baseUrl}/api/auth/register`, {}).pipe(
      tap((res) => this.storeAuth(res))
    );
  }

  login(userId: string, token: string): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${this.baseUrl}/api/auth/login`, { userId, token }).pipe(
      tap((res) => this.storeAuth(res))
    );
  }

  getToken(): string | null {
    return localStorage.getItem('echoes_token');
  }

  markIntakeCompleted(): void {
    localStorage.setItem('echoes_intake_completed', 'true');
    this.intakeCompleted$.next(true);
  }

  logout(): void {
    localStorage.removeItem('echoes_token');
    localStorage.removeItem('echoes_user_id');
    localStorage.removeItem('echoes_intake_completed');
    this.userId$.next(null);
    this.intakeCompleted$.next(false);
  }

  ensureAuthenticated(): Observable<AuthResponse> {
    if (this.isAuthenticated) {
      return new Observable((sub) => {
        sub.next({
          userId: this.userId!,
          token: this.getToken()!,
          intakeCompleted: this.isIntakeCompleted,
        });
        sub.complete();
      });
    }
    return this.register();
  }

  private storeAuth(res: AuthResponse): void {
    localStorage.setItem('echoes_token', res.token);
    localStorage.setItem('echoes_user_id', res.userId);
    localStorage.setItem('echoes_intake_completed', String(res.intakeCompleted));
    this.userId$.next(res.userId);
    this.intakeCompleted$.next(res.intakeCompleted);
  }

  private getStoredUserId(): string | null {
    return localStorage.getItem('echoes_user_id');
  }

  private getStoredIntakeStatus(): boolean {
    return localStorage.getItem('echoes_intake_completed') === 'true';
  }
}
