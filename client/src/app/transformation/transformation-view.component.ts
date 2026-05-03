import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { NgIf } from '@angular/common';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar } from '@angular/material/snack-bar';
import { RouterLink } from '@angular/router';

import { TransformationService, Transformation } from '../core/transformation.service';
import { DeleteTokenService } from '../core/delete-token.service';
import { SeoService } from '../core/seo.service';
import { TrackingService } from '../core/tracking.service';
import { BeforeAfterSliderComponent } from '../shared/before-after-slider/before-after-slider.component';

@Component({
  selector: 'app-transformation-view',
  standalone: true,
  imports: [
    NgIf,
    RouterLink,
    MatProgressSpinnerModule,
    MatButtonModule,
    MatIconModule,
    BeforeAfterSliderComponent,
  ],
  templateUrl: './transformation-view.component.html',
  styleUrl: './transformation-view.component.scss',
})
export class TransformationViewComponent implements OnInit {
  private readonly service = inject(TransformationService);
  private readonly tokenService = inject(DeleteTokenService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly snackBar = inject(MatSnackBar);
  private readonly seo = inject(SeoService);
  private readonly tracking = inject(TrackingService);

  transformation = signal<Transformation | null>(null);
  loading = signal(true);
  error = signal('');
  canDelete = signal(false);

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id')!;
    this.canDelete.set(this.tokenService.has(id));
    this.service.get(id).subscribe({
      next: (t) => {
        this.transformation.set(t);
        this.loading.set(false);
        this.seo.set({
          title: 'Street transformation',
          description: 'See what this street looks like without cars, reimagined by Caraser.',
        });
      },
      error: () => {
        this.error.set('Transformation not found or no longer available.');
        this.loading.set(false);
      },
    });
  }

  deleteTransformation(): void {
    const t = this.transformation();
    if (!t) return;
    const token = this.tokenService.get(t.id);
    if (!token) return;
    if (!confirm('Delete this transformation and all its images? This cannot be undone.')) return;

    this.tracking.trackEvent('Transformation', 'delete', t.id);
    this.service.delete(t.id, token).subscribe({
      next: () => {
        this.tokenService.remove(t.id);
        this.router.navigate(['/']);
      },
      error: () => {
        alert('Delete failed. Please try again.');
      },
    });
  }

  download(): void {
    const t = this.transformation();
    if (!t?.result_image) return;
    this.tracking.trackEvent('Transformation', 'download', t.id);
    this.triggerDownload(t.result_image, `caraser-${t.id}.jpg`);
  }

  downloadComparison(): void {
    const t = this.transformation();
    if (!t?.comparison_image) return;
    this.tracking.trackEvent('Transformation', 'download_comparison', t.id);
    this.triggerDownload(t.comparison_image, `caraser-${t.id}-comparison.jpg`);
  }

  private triggerDownload(url: string, filename: string): void {
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
  }

  async share(): Promise<void> {
    const shareUrl = location.href;
    if (navigator.share) {
      try {
        await navigator.share({ title: 'Caraser – streets without cars', url: shareUrl });
        this.tracking.trackEvent('Transformation', 'share', this.transformation()?.id);
        return;
      } catch (err) {
        if (err instanceof DOMException && err.name === 'AbortError') return;
      }
    }
    await this.copyLink();
  }

  async copyLink(): Promise<void> {
    try {
      await navigator.clipboard.writeText(location.href);
      this.snackBar.open('Link copied to clipboard', undefined, { duration: 3000 });
      this.tracking.trackEvent('Transformation', 'copy_link', this.transformation()?.id);
    } catch {
      this.snackBar.open('Could not copy link', undefined, { duration: 3000 });
    }
  }
}
