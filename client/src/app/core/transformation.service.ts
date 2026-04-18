import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, interval, switchMap, takeWhile, distinctUntilChanged } from 'rxjs';

export interface Transformation {
  id: string;
  original_image: string;
  result_image: string | null;
  status: 'pending' | 'processing' | 'done' | 'failed';
  error: string;
  is_public: boolean;
  created_at: string;
}

export interface PaginatedTransformations {
  count: number;
  next: string | null;
  previous: string | null;
  results: Transformation[];
}

@Injectable({ providedIn: 'root' })
export class TransformationService {
  private readonly http = inject(HttpClient);

  upload(file: File): Observable<Transformation> {
    const form = new FormData();
    form.append('image', file);
    return this.http.post<Transformation>('/api/transformations/upload/', form);
  }

  get(id: string): Observable<Transformation> {
    return this.http.get<Transformation>(`/api/transformations/${id}/`);
  }

  list(page = 1): Observable<PaginatedTransformations> {
    return this.http.get<PaginatedTransformations>('/api/transformations/', {
      params: { page: page.toString() },
    });
  }

  poll(id: string): Observable<Transformation> {
    return interval(1500).pipe(
      switchMap(() => this.get(id)),
      distinctUntilChanged((a, b) => a.status === b.status),
      takeWhile((t) => t.status !== 'done' && t.status !== 'failed', true),
    );
  }
}
