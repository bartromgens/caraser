import { Component, OnInit, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { NgIf } from '@angular/common';

interface HealthResponse {
  status: string;
}

@Component({
  selector: 'app-home',
  imports: [MatCardModule, MatProgressSpinnerModule, NgIf],
  styles: [`
    .home-container {
      padding: 24px;
    }
    mat-card {
      max-width: 400px;
    }
    .status-value {
      font-size: 1.2rem;
      font-weight: 500;
      margin-top: 8px;
    }
    .spinner-wrapper {
      display: flex;
      justify-content: center;
      padding: 16px 0;
    }
  `],
  templateUrl: './home.html',
})
export class HomeComponent implements OnInit {
  healthStatus = signal<string | null>(null);
  loading = signal(true);
  error = signal<string | null>(null);

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.http.get<HealthResponse>('/api/health/').subscribe({
      next: (res) => {
        this.healthStatus.set(res.status);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Could not reach API');
        this.loading.set(false);
      },
    });
  }
}
