import { Component, inject, signal } from '@angular/core';
import { NgIf, NgClass } from '@angular/common';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';

import {
  GroundCover,
  ShapeStyle,
  TransformationOptions,
  TransformationService,
} from '../core/transformation.service';
import { DeleteTokenService } from '../core/delete-token.service';

type AppState = 'upload' | 'options' | 'uploading' | 'processing' | 'error';

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
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatProgressBarModule,
    MatSelectModule,
    MatSlideToggleModule,
  ],
  templateUrl: './home.component.html',
  styleUrl: './home.component.scss',
})
export class HomeComponent {
  private readonly service = inject(TransformationService);
  private readonly tokenService = inject(DeleteTokenService);
  private readonly router = inject(Router);

  state = signal<AppState>('upload');
  errorMessage = signal('');
  previewUrl = signal<string | null>(null);
  selectedFile = signal<File | null>(null);

  isDragOver = signal(false);

  allowCars = signal<boolean>(DEFAULT_OPTIONS.allow_cars);
  fietsstraat = signal<boolean>(DEFAULT_OPTIONS.fietsstraat);
  groundCover = signal<GroundCover>(DEFAULT_OPTIONS.ground_cover);
  shapeStyle = signal<ShapeStyle>(DEFAULT_OPTIONS.shape_style);

  get isWorking(): boolean {
    return this.state() === 'uploading' || this.state() === 'processing';
  }

  get isUploadStep(): boolean {
    return this.state() === 'upload';
  }

  get isOptionsStep(): boolean {
    return this.state() === 'options';
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

  changeImage(): void {
    if (this.previewUrl()) {
      URL.revokeObjectURL(this.previewUrl()!);
      this.previewUrl.set(null);
    }
    this.selectedFile.set(null);
    this.state.set('upload');
  }

  reset(): void {
    this.state.set('upload');
    this.errorMessage.set('');
    this.selectedFile.set(null);
    if (this.previewUrl()) {
      URL.revokeObjectURL(this.previewUrl()!);
      this.previewUrl.set(null);
    }
  }

  generate(): void {
    const file = this.selectedFile();
    if (!file) return;
    this.state.set('uploading');

    this.service.upload(file, this.currentOptions()).subscribe({
      next: (t) => {
        if (t.delete_token) {
          this.tokenService.save(t.id, t.delete_token);
        }
        this.state.set('processing');
        this.startPolling(t.id);
      },
      error: (err) => {
        this.state.set('error');
        this.errorMessage.set(err?.error?.detail ?? 'Upload failed. Please try again.');
      },
    });
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
    this.selectedFile.set(file);
    this.previewUrl.set(URL.createObjectURL(file));
    this.state.set('options');
  }

  private startPolling(id: string): void {
    this.service.poll(id).subscribe({
      next: (t) => {
        if (t.status === 'done') {
          this.router.navigate(['/t', id]);
        }
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
