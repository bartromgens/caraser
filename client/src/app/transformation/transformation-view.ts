import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { NgIf } from '@angular/common';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { RouterLink } from '@angular/router';

import { TransformationService, Transformation } from '../core/transformation.service';
import { BeforeAfterSliderComponent } from '../shared/before-after-slider/before-after-slider';

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
  templateUrl: './transformation-view.html',
  styleUrl: './transformation-view.scss',
})
export class TransformationViewComponent implements OnInit {
  private readonly service = inject(TransformationService);
  private readonly route = inject(ActivatedRoute);

  transformation = signal<Transformation | null>(null);
  loading = signal(true);
  error = signal('');

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id')!;
    this.service.get(id).subscribe({
      next: (t) => {
        this.transformation.set(t);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Transformation not found or no longer available.');
        this.loading.set(false);
      },
    });
  }

  download(): void {
    const t = this.transformation();
    if (!t?.result_image) return;
    this.triggerDownload(t.result_image, `caraser-${t.id}.png`);
  }

  downloadComparison(): void {
    const t = this.transformation();
    if (!t?.comparison_image) return;
    this.triggerDownload(t.comparison_image, `caraser-${t.id}-comparison.png`);
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
        return;
      } catch {
        // fall through
      }
    }
    await navigator.clipboard.writeText(shareUrl);
  }
}
