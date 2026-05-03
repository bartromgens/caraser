import { Component, inject, signal } from '@angular/core';
import { NgIf, NgClass } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';

import {
  GroundCover,
  ShapeStyle,
  Transformation,
  TransformationOptions,
  TransformationService,
} from '../core/transformation.service';
import { DeleteTokenService } from '../core/delete-token.service';
import { BeforeAfterSliderComponent } from '../shared/before-after-slider/before-after-slider';

type AppState = 'idle' | 'uploading' | 'processing' | 'done' | 'error';

const DEFAULT_OPTIONS: TransformationOptions = {
  allow_cars: false,
  fietsstraat: false,
  ground_cover: 'mixed',
  shape_style: 'organic',
};

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [
    NgIf,
    NgClass,
    MatButtonModule,
    MatButtonToggleModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatProgressBarModule,
    MatSelectModule,
    MatSlideToggleModule,
    BeforeAfterSliderComponent,
  ],
  templateUrl: './home.html',
  styleUrl: './home.scss',
})
export class HomeComponent {
  private readonly service = inject(TransformationService);
  private readonly tokenService = inject(DeleteTokenService);

  state = signal<AppState>('idle');
  errorMessage = signal('');
  transformation = signal<Transformation | null>(null);
  previewUrl = signal<string | null>(null);

  isDragOver = signal(false);

  allowCars = signal<boolean>(DEFAULT_OPTIONS.allow_cars);
  fietsstraat = signal<boolean>(DEFAULT_OPTIONS.fietsstraat);
  groundCover = signal<GroundCover>(DEFAULT_OPTIONS.ground_cover);
  shapeStyle = signal<ShapeStyle>(DEFAULT_OPTIONS.shape_style);

  get isWorking(): boolean {
    return this.state() === 'uploading' || this.state() === 'processing';
  }

  get progressMode(): 'indeterminate' | 'buffer' {
    return this.state() === 'processing' ? 'indeterminate' : 'buffer';
  }

  get statusLabel(): string {
    if (this.state() === 'uploading') return 'Uploading image…';
    if (this.state() === 'processing') return 'Caraser is erasing cars (this takes ~15 s)…';
    return '';
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    this.isDragOver.set(true);
  }

  onDragLeave(): void {
    this.isDragOver.set(false);
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    this.isDragOver.set(false);
    const file = event.dataTransfer?.files[0];
    if (file) this.processFile(file);
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (file) this.processFile(file);
    input.value = '';
  }

  resetOptions(): void {
    this.allowCars.set(DEFAULT_OPTIONS.allow_cars);
    this.fietsstraat.set(DEFAULT_OPTIONS.fietsstraat);
    this.groundCover.set(DEFAULT_OPTIONS.ground_cover);
    this.shapeStyle.set(DEFAULT_OPTIONS.shape_style);
  }

  reset(): void {
    this.state.set('idle');
    this.transformation.set(null);
    this.errorMessage.set('');
    if (this.previewUrl()) {
      URL.revokeObjectURL(this.previewUrl()!);
      this.previewUrl.set(null);
    }
  }

  deleteTransformation(): void {
    const t = this.transformation();
    if (!t) return;
    const token = this.tokenService.get(t.id);
    if (!token) return;
    if (!confirm('Delete this transformation and all its images? This cannot be undone.')) return;

    this.service.delete(t.id, token).subscribe({
      next: () => {
        this.tokenService.remove(t.id);
        this.reset();
      },
      error: () => {
        alert('Delete failed. Please try again.');
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
    const t = this.transformation();
    if (!t) return;
    const shareUrl = `${location.origin}/t/${t.id}`;

    if (navigator.share) {
      try {
        await navigator.share({ title: 'Caraser – streets without cars', url: shareUrl });
        return;
      } catch {
        // fall through to clipboard
      }
    }
    await navigator.clipboard.writeText(shareUrl);
  }

  private currentOptions(): TransformationOptions {
    return {
      allow_cars: this.allowCars(),
      fietsstraat: this.fietsstraat(),
      ground_cover: this.groundCover(),
      shape_style: this.shapeStyle(),
    };
  }

  private processFile(file: File): void {
    this.previewUrl.set(URL.createObjectURL(file));
    this.state.set('uploading');

    this.service.upload(file, this.currentOptions()).subscribe({
      next: (t) => {
        if (t.delete_token) {
          this.tokenService.save(t.id, t.delete_token);
        }
        this.transformation.set(t);
        this.state.set('processing');
        this.startPolling(t.id);
      },
      error: (err) => {
        this.state.set('error');
        this.errorMessage.set(err?.error?.detail ?? 'Upload failed. Please try again.');
      },
    });
  }

  private startPolling(id: string): void {
    this.service.poll(id).subscribe({
      next: (t) => {
        this.transformation.set(t);
        if (t.status === 'done') this.state.set('done');
        if (t.status === 'failed') {
          this.state.set('error');
          this.errorMessage.set(t.error || 'Processing failed.');
        }
      },
      error: () => {
        this.state.set('error');
        this.errorMessage.set('Lost connection while waiting for result.');
      },
    });
  }
}
