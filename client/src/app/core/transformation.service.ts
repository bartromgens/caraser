import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, interval, switchMap, takeWhile, distinctUntilChanged } from 'rxjs';

export interface PaintColor {
  hex: string;
  color_name: string;
  label: string;
  short: string;
}

export type GroundCover = 'mixed' | 'stones' | 'grass' | 'flowers';
export type ShapeStyle = 'mixed' | 'organic' | 'straight' | 'wilderness';

export interface TransformationOptions {
  allow_cars: boolean;
  fietsstraat: boolean;
  ground_cover: GroundCover;
  shape_style: ShapeStyle;
}

export interface Transformation extends TransformationOptions {
  id: string;
  mode: 'classic' | 'designer';
  original_image: string;
  overlay_image: string | null;
  result_image: string | null;
  thumbnail_image: string | null;
  comparison_image: string | null;
  status: 'pending' | 'processing' | 'done' | 'failed';
  error: string;
  is_public: boolean;
  is_featured: boolean;
  prompt?: string | null;
  annotated_image?: string | null;
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

  uploadDesigner(file: File, overlayPng: Blob): Observable<Transformation> {
    const form = new FormData();
    form.append('image', file);
    form.append('overlay', overlayPng, 'overlay.png');
    form.append('mode', 'designer');
    return this.http.post<Transformation>('/api/transformations/upload/', form);
  }

  get(id: string): Observable<Transformation> {
    return this.http.get<Transformation>(`/api/transformations/${id}/`);
  }

  list(
    page = 1,
    opts: { featured?: boolean | 'exclude'; pageSize?: number; ids?: string[] } = {},
  ): Observable<PaginatedTransformations> {
    const params: Record<string, string> = { page: page.toString() };
    if (opts.featured === true) params['featured'] = 'true';
    else if (opts.featured === 'exclude') params['featured'] = 'false';
    if (opts.pageSize) params['page_size'] = opts.pageSize.toString();
    if (opts.ids?.length) params['ids'] = opts.ids.join(',');
    return this.http.get<PaginatedTransformations>('/api/transformations/', { params });
  }

  poll(id: string): Observable<Transformation> {
    return interval(1500).pipe(
      switchMap(() => this.get(id)),
      distinctUntilChanged((a, b) => a.status === b.status),
      takeWhile((t) => t.status !== 'done' && t.status !== 'failed', true),
    );
  }

  delete(id: string, token?: string): Observable<void> {
    const headers = token ? new HttpHeaders({ 'X-Delete-Token': token }) : new HttpHeaders();
    return this.http.delete<void>(`/api/transformations/${id}/`, { headers });
  }

  promote(id: string, featured: boolean): Observable<Transformation> {
    return this.http.patch<Transformation>(`/api/transformations/${id}/`, {
      is_featured: featured,
    });
  }

  getLegend(): Observable<PaintColor[]> {
    return this.http.get<PaintColor[]>('/api/designer/legend/');
  }
}
