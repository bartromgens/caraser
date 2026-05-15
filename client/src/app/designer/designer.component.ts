import { Component, OnDestroy, OnInit, ViewChild, inject, signal } from '@angular/core';
import { NgIf, NgClass } from '@angular/common';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';

import { TransformationService } from '../core/transformation.service';
import { DeleteTokenService } from '../core/delete-token.service';
import { SeoService } from '../core/seo.service';
import { TrackingService } from '../core/tracking.service';
import { PaintCanvasComponent } from './paint-canvas/paint-canvas.component';

type AppState = 'upload' | 'paint' | 'uploading' | 'processing' | 'error';

const SLOW_PROCESSING_THRESHOLD_MS = 20_000;

@Component({
  selector: 'app-designer',
  standalone: true,
  imports: [
    NgIf,
    NgClass,
    MatButtonModule,
    MatCardModule,
    MatIconModule,
    MatProgressBarModule,
    PaintCanvasComponent,
  ],
  templateUrl: './designer.component.html',
  styleUrl: './designer.component.scss',
})
export class DesignerComponent implements OnInit, OnDestroy {
  private readonly service = inject(TransformationService);
  private readonly tokenService = inject(DeleteTokenService);
  private readonly router = inject(Router);
  private readonly seo = inject(SeoService);
  private readonly tracking = inject(TrackingService);

  @ViewChild(PaintCanvasComponent) paintCanvas?: PaintCanvasComponent;

  state = signal<AppState>('upload');
  errorMessage = signal('');
  previewUrl = signal<string | null>(null);
  selectedFile = signal<File | null>(null);
  naturalWidth = signal(0);
  naturalHeight = signal(0);
  canGenerate = signal(false);
  processingSlow = signal(false);

  isDragOver = signal(false);

  private slowTimer: ReturnType<typeof setTimeout> | null = null;

  ngOnInit(): void {
    this.seo.set({
      title: 'Designer mode — Caraser',
      description: 'Draw your ideal street design with colors and let AI bring it to life.',
    });
  }

  ngOnDestroy(): void {
    this.clearSlowTimer();
    if (this.previewUrl()) URL.revokeObjectURL(this.previewUrl()!);
  }

  get isUploadStep(): boolean {
    return this.state() === 'upload';
  }

  get isPaintStep(): boolean {
    return this.state() === 'paint';
  }

  get isWorking(): boolean {
    return this.state() === 'uploading' || this.state() === 'processing';
  }

  get progressMode(): 'indeterminate' | 'buffer' {
    return this.state() === 'processing' ? 'indeterminate' : 'buffer';
  }

  get statusLabel(): string {
    if (this.state() === 'uploading') return 'Uploading image…';
    if (this.state() === 'processing') {
      return this.processingSlow()
        ? 'Still working — the AI is busy right now, hang on…'
        : 'Caraser is applying your design (this takes ~15 s)…';
    }
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

  onImageLoad(event: Event): void {
    const img = event.target as HTMLImageElement;
    this.naturalWidth.set(img.naturalWidth);
    this.naturalHeight.set(img.naturalHeight);
  }

  onHasStrokes(has: boolean): void {
    this.canGenerate.set(has);
  }

  changeImage(): void {
    if (this.previewUrl()) {
      URL.revokeObjectURL(this.previewUrl()!);
      this.previewUrl.set(null);
    }
    this.selectedFile.set(null);
    this.canGenerate.set(false);
    this.state.set('upload');
  }

  async generate(): Promise<void> {
    if (!this.paintCanvas || !this.selectedFile()) return;
    this.state.set('uploading');
    this.tracking.trackEvent('Designer', 'generate');

    let overlayBlob: Blob;
    try {
      overlayBlob = await this.paintCanvas.exportPng();
    } catch {
      this.state.set('error');
      this.errorMessage.set('Could not export the painted overlay. Please try again.');
      return;
    }

    this.service.uploadDesigner(this.selectedFile()!, overlayBlob).subscribe({
      next: (t) => {
        if (t.delete_token) this.tokenService.save(t.id, t.delete_token);
        this.state.set('processing');
        this.startSlowTimer();
        this.startPolling(t.id);
      },
      error: (err) => {
        this.state.set('error');
        this.errorMessage.set(err?.error?.detail ?? 'Upload failed. Please try again.');
        this.tracking.trackEvent('Designer', 'upload_error');
      },
    });
  }

  reset(): void {
    this.state.set('upload');
    this.errorMessage.set('');
    this.selectedFile.set(null);
    this.canGenerate.set(false);
    this.clearSlowTimer();
    if (this.previewUrl()) {
      URL.revokeObjectURL(this.previewUrl()!);
      this.previewUrl.set(null);
    }
  }

  private processFile(file: File): void {
    this.selectedFile.set(file);
    this.previewUrl.set(URL.createObjectURL(file));
    this.canGenerate.set(false);
    this.state.set('paint');
    this.tracking.trackEvent('Designer', 'file_selected');
  }

  private startPolling(id: string): void {
    this.service.poll(id).subscribe({
      next: (t) => {
        if (t.status === 'done') {
          this.clearSlowTimer();
          this.tracking.trackEvent('Designer', 'generate_success');
          this.router.navigate(['/t', id]);
        }
        if (t.status === 'failed') {
          this.clearSlowTimer();
          this.state.set('error');
          this.errorMessage.set(t.error || 'Processing failed.');
          this.tracking.trackEvent('Designer', 'generate_error');
        }
      },
      error: () => {
        this.clearSlowTimer();
        this.state.set('error');
        this.errorMessage.set('Lost connection while waiting for result.');
        this.tracking.trackEvent('Designer', 'polling_error');
      },
    });
  }

  private startSlowTimer(): void {
    this.clearSlowTimer();
    this.processingSlow.set(false);
    this.slowTimer = setTimeout(() => {
      this.processingSlow.set(true);
    }, SLOW_PROCESSING_THRESHOLD_MS);
  }

  private clearSlowTimer(): void {
    if (this.slowTimer !== null) {
      clearTimeout(this.slowTimer);
      this.slowTimer = null;
    }
    this.processingSlow.set(false);
  }
}
