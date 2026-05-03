import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, interval, switchMap, takeWhile, distinctUntilChanged } from 'rxjs';

export type GroundCover = 'mixed' | 'stones' | 'grass' | 'flowers';
export type ShapeStyle = 'organic' | 'straight';

export interface TransformationOptions {
  allow_cars: boolean;
  fietsstraat: boolean;
  ground_cover: GroundCover;
  shape_style: ShapeStyle;
}

export interface Transformation extends TransformationOptions {
  id: string;
  original_image: string;
  result_image: string | null;
  comparison_image: string | null;
  status: 'pending' | 'processing' | 'done' | 'failed';
  error: string;
  is_public: boolean;
  created_at: string;
  delete_token?: string;
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

  upload(file: File, options: TransformationOptions): Observable<Transformation> {
    const form = new FormData();
    form.append('image', file);
    form.append('allow_cars', String(options.allow_cars));
    form.append('fietsstraat', String(options.fietsstraat));
    form.append('ground_cover', options.ground_cover);
    form.append('shape_style', options.shape_style);
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

  delete(id: string, token: string): Observable<void> {
    const headers = new HttpHeaders({ 'X-Delete-Token': token });
    return this.http.delete<void>(`/api/transformations/${id}/`, { headers });
  }
}
