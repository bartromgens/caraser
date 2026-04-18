import { Component, inject, signal, computed } from '@angular/core';
import { NgIf, NgClass } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatCardModule } from '@angular/material/card';

import { TransformationService, Transformation } from '../core/transformation.service';
import { BeforeAfterSliderComponent } from '../shared/before-after-slider/before-after-slider';

type AppState = 'idle' | 'uploading' | 'processing' | 'done' | 'error';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [
    NgIf,
    NgClass,
    MatButtonModule,
    MatIconModule,
    MatProgressBarModule,
    MatCardModule,
    BeforeAfterSliderComponent,
  ],
  templateUrl: './home.html',
  styleUrl: './home.scss',
})
export class HomeComponent {
  private readonly service = inject(TransformationService);

  state = signal<AppState>('idle');
  errorMessage = signal('');
  transformation = signal<Transformation | null>(null);
  previewUrl = signal<string | null>(null);

  isDragOver = signal(false);

  get isWorking(): boolean {
    return this.state() === 'uploading' || this.state() === 'processing';
  }

  get progressMode(): 'indeterminate' | 'buffer' {
    return this.state() === 'processing' ? 'indeterminate' : 'buffer';
  }

  get statusLabel(): string {
    if (this.state() === 'uploading') return 'Uploading image…';
    if (this.state() === 'processing') return 'Gemini is removing cars (this takes ~30 s)…';
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

  reset(): void {
    this.state.set('idle');
    this.transformation.set(null);
    this.errorMessage.set('');
    if (this.previewUrl()) {
      URL.revokeObjectURL(this.previewUrl()!);
      this.previewUrl.set(null);
    }
  }

  download(): void {
    const t = this.transformation();
    if (!t?.result_image) return;
    const a = document.createElement('a');
    a.href = t.result_image;
    a.download = `caraser-${t.id}.png`;
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
    // brief visual acknowledgment handled by template signal
  }

  private processFile(file: File): void {
    this.previewUrl.set(URL.createObjectURL(file));
    this.state.set('uploading');

    this.service.upload(file).subscribe({
      next: (t) => {
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
