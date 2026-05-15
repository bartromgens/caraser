import { Component, OnInit, inject, signal } from '@angular/core';
import { NgIf, NgFor, DOCUMENT } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';

import { TransformationService, Transformation } from '../../core/transformation.service';
import { GalleryCardComponent } from '../../shared/gallery-card/gallery-card.component';

@Component({
  selector: 'app-featured-strip',
  standalone: true,
  imports: [NgIf, NgFor, RouterLink, MatIconModule, GalleryCardComponent],
  templateUrl: './featured-strip.component.html',
  styleUrl: './featured-strip.component.scss',
})
export class FeaturedStripComponent implements OnInit {
  private readonly service = inject(TransformationService);
  private readonly document = inject(DOCUMENT);

  items = signal<Transformation[]>([]);

  ngOnInit(): void {
    this.service.list(1, { featured: true, pageSize: 6 }).subscribe({
      next: (res) => {
        this.items.set(res.results);
        this.preloadLcpImage(res.results[0]);
      },
      error: () => {},
    });
  }

  private preloadLcpImage(item: Transformation | undefined): void {
    const url = item?.thumbnail_image ?? item?.result_image;
    if (!url) return;
    const link = this.document.createElement('link');
    link.rel = 'preload';
    link.as = 'image';
    link.href = url;
    link.setAttribute('fetchpriority', 'high');
    this.document.head.appendChild(link);
  }
}
