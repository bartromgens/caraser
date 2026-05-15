import {
  Component,
  ElementRef,
  EventEmitter,
  Input,
  OnChanges,
  OnDestroy,
  Output,
  SimpleChanges,
  ViewChild,
  signal,
} from '@angular/core';
import { NgFor, NgIf, TitleCasePipe } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatSliderModule } from '@angular/material/slider';
import { MatTooltipModule } from '@angular/material/tooltip';
import { FormsModule } from '@angular/forms';
import { PaintColor } from '../../core/transformation.service';

@Component({
  selector: 'app-paint-canvas',
  standalone: true,
  imports: [
    NgFor,
    NgIf,
    TitleCasePipe,
    MatIconModule,
    MatButtonModule,
    MatSliderModule,
    MatTooltipModule,
    FormsModule,
  ],
  templateUrl: './paint-canvas.component.html',
  styleUrl: './paint-canvas.component.scss',
})
export class PaintCanvasComponent implements OnChanges, OnDestroy {
  @Input() colors: PaintColor[] = [];
  @Input() imageUrl?: string;
  @Input() naturalWidth = 0;
  @Input() naturalHeight = 0;
  @Output() hasStrokes = new EventEmitter<boolean>();

  @ViewChild('displayCanvas', { static: false }) displayCanvasRef!: ElementRef<HTMLCanvasElement>;
  @ViewChild('offscreenCanvas', { static: false })
  offscreenCanvasRef!: ElementRef<HTMLCanvasElement>;
  @ViewChild('imageEl', { static: false }) imageElRef!: ElementRef<HTMLImageElement>;

  activeColor = signal<PaintColor | null>(null);
  brushSize = 105;
  isEraser = signal(false);

  private painting = false;
  private lastX = 0;
  private lastY = 0;
  private _hasStrokes = false;

  // Undo stack: each entry is an ImageData snapshot of the off-screen canvas
  private undoStack: ImageData[] = [];

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['colors'] && this.colors.length && !this.activeColor()) {
      this.activeColor.set(this.colors[2] ?? this.colors[0]);
    }
    if (changes['imageUrl'] && this.imageUrl) {
      setTimeout(() => this.clearAll(), 50);
    }
  }

  ngOnDestroy(): void {
    this.undoStack = [];
  }

  selectColor(color: PaintColor): void {
    this.activeColor.set(color);
    this.isEraser.set(false);
  }

  activeHex(): string | null {
    return this.activeColor()?.hex ?? null;
  }

  toggleEraser(): void {
    this.isEraser.set(!this.isEraser());
  }

  undo(): void {
    if (this.undoStack.length === 0) return;
    const offCtx = this.offscreenCtx();
    if (!offCtx) return;
    const snapshot = this.undoStack.pop()!;
    offCtx.putImageData(snapshot, 0, 0);
    this.syncDisplayFromOffscreen();
    this._hasStrokes = this.undoStack.length > 0;
    this.hasStrokes.emit(this._hasStrokes);
  }

  clearAll(): void {
    const offCtx = this.offscreenCtx();
    const dispCtx = this.displayCtx();
    if (offCtx) offCtx.clearRect(0, 0, this.naturalWidth, this.naturalHeight);
    if (dispCtx) {
      const c = this.displayCanvasRef.nativeElement;
      dispCtx.clearRect(0, 0, c.width, c.height);
    }
    this.undoStack = [];
    this._hasStrokes = false;
    this.hasStrokes.emit(false);
  }

  onPointerDown(event: PointerEvent): void {
    event.preventDefault();
    const canvas = this.displayCanvasRef.nativeElement;
    canvas.setPointerCapture(event.pointerId);
    this.painting = true;
    this.saveUndoSnapshot();
    const [x, y] = this.toNaturalCoords(event, canvas);
    this.lastX = x;
    this.lastY = y;
    this.drawDot(x, y);
    this.syncDisplayFromOffscreen();
    this.emitStrokes();
  }

  onPointerMove(event: PointerEvent): void {
    if (!this.painting) return;
    event.preventDefault();
    const canvas = this.displayCanvasRef.nativeElement;
    const [x, y] = this.toNaturalCoords(event, canvas);
    this.drawLine(this.lastX, this.lastY, x, y);
    this.lastX = x;
    this.lastY = y;
    this.syncDisplayFromOffscreen();
  }

  onPointerUp(event: PointerEvent): void {
    this.painting = false;
  }

  exportPng(): Promise<Blob> {
    return new Promise((resolve, reject) => {
      const canvas = this.offscreenCanvasRef?.nativeElement;
      if (!canvas) {
        reject(new Error('Canvas not ready'));
        return;
      }
      canvas.toBlob((blob) => {
        if (blob) resolve(blob);
        else reject(new Error('Canvas toBlob returned null'));
      }, 'image/png');
    });
  }

  private displayCtx(): CanvasRenderingContext2D | null {
    return this.displayCanvasRef?.nativeElement.getContext('2d') ?? null;
  }

  private offscreenCtx(): CanvasRenderingContext2D | null {
    return this.offscreenCanvasRef?.nativeElement.getContext('2d') ?? null;
  }

  private toNaturalCoords(event: PointerEvent, canvas: HTMLCanvasElement): [number, number] {
    const rect = canvas.getBoundingClientRect();
    const scaleX = this.naturalWidth / rect.width;
    const scaleY = this.naturalHeight / rect.height;
    return [(event.clientX - rect.left) * scaleX, (event.clientY - rect.top) * scaleY];
  }

  private drawDot(x: number, y: number): void {
    const ctx = this.offscreenCtx();
    if (!ctx) return;
    ctx.save();
    this.applyCompositing(ctx);
    ctx.beginPath();
    ctx.arc(x, y, this.brushSize / 2, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  private drawLine(x0: number, y0: number, x1: number, y1: number): void {
    const ctx = this.offscreenCtx();
    if (!ctx) return;
    ctx.save();
    this.applyCompositing(ctx);
    ctx.beginPath();
    ctx.moveTo(x0, y0);
    ctx.lineTo(x1, y1);
    ctx.lineWidth = this.brushSize;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.stroke();
    ctx.fill();
    ctx.restore();
  }

  private applyCompositing(ctx: CanvasRenderingContext2D): void {
    if (this.isEraser()) {
      ctx.globalCompositeOperation = 'destination-out';
      ctx.fillStyle = 'rgba(0,0,0,1)';
      ctx.strokeStyle = 'rgba(0,0,0,1)';
    } else {
      const hex = this.activeHex();
      if (!hex) return;
      ctx.globalCompositeOperation = 'source-over';
      ctx.fillStyle = hex;
      ctx.strokeStyle = hex;
    }
  }

  private syncDisplayFromOffscreen(): void {
    const offCanvas = this.offscreenCanvasRef?.nativeElement;
    const dispCanvas = this.displayCanvasRef?.nativeElement;
    const dispCtx = this.displayCtx();
    if (!offCanvas || !dispCanvas || !dispCtx) return;
    dispCtx.clearRect(0, 0, dispCanvas.width, dispCanvas.height);
    dispCtx.drawImage(offCanvas, 0, 0, dispCanvas.width, dispCanvas.height);
  }

  private saveUndoSnapshot(): void {
    const ctx = this.offscreenCtx();
    if (!ctx) return;
    const snapshot = ctx.getImageData(0, 0, this.naturalWidth, this.naturalHeight);
    this.undoStack.push(snapshot);
    if (this.undoStack.length > 50) this.undoStack.shift();
  }

  private emitStrokes(): void {
    if (!this._hasStrokes) {
      this._hasStrokes = true;
      this.hasStrokes.emit(true);
    }
  }
}
