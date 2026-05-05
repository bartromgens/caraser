import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';

interface AuthResponse {
  is_authenticated: boolean;
  username?: string;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);

  readonly isAuthenticated = signal(false);
  readonly username = signal<string | null>(null);

  refresh(): Observable<AuthResponse> {
    return this.http.get<AuthResponse>('/api/auth/me/').pipe(
      tap((r) => {
        this.isAuthenticated.set(r.is_authenticated);
        this.username.set(r.username ?? null);
      }),
    );
  }
}
