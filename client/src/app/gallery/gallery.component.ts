import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { NgIf, NgFor } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';

import { TransformationService, Transformation } from '../core/transformation.service';
import { DeleteTokenService } from '../core/delete-token.service';
import { SeoService } from '../core/seo.service';
import { TrackingService } from '../core/tracking.service';
import { GalleryCardComponent } from '../shared/gallery-card/gallery-card.component';

@Component({
  selector: 'app-gallery',
  standalone: true,
  imports: [
    NgIf,
    NgFor,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatIconModule,
    GalleryCardComponent,
  ],
  templateUrl: './gallery.component.html',
  styleUrl: './gallery.component.scss',
})
export class GalleryComponent implements OnInit {
  private readonly service = inject(TransformationService);
  private readonly tokenService = inject(DeleteTokenService);
  private readonly seo = inject(SeoService);
  private readonly tracking = inject(TrackingService);

  userItems = signal<Transformation[]>([]);
  featuredItems = signal<Transformation[]>([]);
  items = signal<Transformation[]>([]);
  loading = signal(true);
  loadingUser = signal(false);
  loadingFeatured = signal(false);
  loadingMore = signal(false);
  initialLoading = computed(
    () =>
      (this.loading() && this.items().length === 0) || this.loadingUser() || this.loadingFeatured(),
  );
  error = signal('');
  page = signal(1);
  hasNext = signal(false);

  ngOnInit(): void {
    this.seo.set({
      title: 'Gallery',
      description:
        'Browse street photos transformed by Caraser – see what these spaces look like without cars.',
    });

    const userIds = this.tokenService.ids();
    if (userIds.length > 0) {
      this.loadingUser.set(true);
      this.service.list(1, { ids: userIds }).subscribe({
        next: (res) => {
          this.userItems.set(res.results);
          this.loadingUser.set(false);
        },
        error: () => this.loadingUser.set(false),
      });
    }

    this.loadingFeatured.set(true);
    this.service.list(1, { featured: true, pageSize: 12 }).subscribe({
      next: (res) => {
        this.featuredItems.set(res.results);
        this.loadingFeatured.set(false);
      },
      error: () => this.loadingFeatured.set(false),
    });

    this.load();
  }

  loadMore(): void {
    this.page.update((p) => p + 1);
    this.tracking.trackEvent('Gallery', 'load_more', undefined, this.page());
    this.load(true);
  }

  private load(append = false): void {
    this.loading.set(true);
    if (append) this.loadingMore.set(true);
    this.service.list(this.page(), { featured: 'exclude' }).subscribe({
      next: (res) => {
        this.items.update((prev) => (append ? [...prev, ...res.results] : res.results));
        this.hasNext.set(!!res.next);
        this.loading.set(false);
        this.loadingMore.set(false);
      },
      error: () => {
        this.error.set('Failed to load gallery.');
        this.loading.set(false);
        this.loadingMore.set(false);
      },
    });
  }
}
