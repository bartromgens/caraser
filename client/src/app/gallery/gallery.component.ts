import { Component, OnInit, inject, signal } from '@angular/core';
import { NgIf, NgFor } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';

import { TransformationService, Transformation } from '../core/transformation.service';
import { SeoService } from '../core/seo.service';

@Component({
  selector: 'app-gallery',
  standalone: true,
  imports: [NgIf, NgFor, RouterLink, MatButtonModule, MatProgressSpinnerModule, MatIconModule],
  templateUrl: './gallery.component.html',
  styleUrl: './gallery.component.scss',
})
export class GalleryComponent implements OnInit {
  private readonly service = inject(TransformationService);
  private readonly seo = inject(SeoService);

  items = signal<Transformation[]>([]);
  loading = signal(true);
  error = signal('');
  page = signal(1);
  hasNext = signal(false);

  ngOnInit(): void {
    this.seo.set({
      title: 'Gallery',
      description:
        'Browse street photos transformed by Caraser – see what these spaces look like without cars.',
    });
    this.load();
  }

  loadMore(): void {
    this.page.update((p) => p + 1);
    this.load(true);
  }

  private load(append = false): void {
    this.loading.set(true);
    this.service.list(this.page()).subscribe({
      next: (res) => {
        this.items.update((prev) => (append ? [...prev, ...res.results] : res.results));
        this.hasNext.set(!!res.next);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Failed to load gallery.');
        this.loading.set(false);
      },
    });
  }
}
