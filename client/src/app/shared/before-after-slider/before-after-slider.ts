import {
  Component,
  Input,
  ElementRef,
  ViewChild,
  AfterViewInit,
  OnDestroy,
  ChangeDetectionStrategy,
  signal,
} from '@angular/core';

@Component({
  selector: 'app-before-after-slider',
  standalone: true,
  templateUrl: './before-after-slider.html',
  styleUrl: './before-after-slider.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BeforeAfterSliderComponent implements AfterViewInit, OnDestroy {
  @Input() beforeUrl = '';
  @Input() afterUrl = '';
  @Input() beforeLabel = 'Before';
  @Input() afterLabel = 'After';

  @ViewChild('container') containerRef!: ElementRef<HTMLDivElement>;
  @ViewChild('handle') handleRef!: ElementRef<HTMLDivElement>;

  position = signal(50);

  private dragging = false;
  private cleanupFns: (() => void)[] = [];

  ngAfterViewInit(): void {
    const container = this.containerRef.nativeElement;
    const handle = this.handleRef.nativeElement;

    const onMouseDown = (e: MouseEvent) => {
      e.preventDefault();
      this.dragging = true;
    };
    const onTouchStart = () => {
      this.dragging = true;
    };
    const onMouseMove = (e: MouseEvent) => {
      if (!this.dragging) return;
      this.updateFromClientX(e.clientX, container);
    };
    const onTouchMove = (e: TouchEvent) => {
      if (!this.dragging) return;
      this.updateFromClientX(e.touches[0].clientX, container);
    };
    const onEnd = () => {
      this.dragging = false;
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') this.position.update((p) => Math.max(0, p - 2));
      if (e.key === 'ArrowRight') this.position.update((p) => Math.min(100, p + 2));
    };

    handle.addEventListener('mousedown', onMouseDown);
    handle.addEventListener('touchstart', onTouchStart, { passive: true });
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('touchmove', onTouchMove, { passive: true });
    window.addEventListener('mouseup', onEnd);
    window.addEventListener('touchend', onEnd);
    handle.addEventListener('keydown', onKeyDown);

    this.cleanupFns = [
      () => handle.removeEventListener('mousedown', onMouseDown),
      () => handle.removeEventListener('touchstart', onTouchStart),
      () => window.removeEventListener('mousemove', onMouseMove),
      () => window.removeEventListener('touchmove', onTouchMove),
      () => window.removeEventListener('mouseup', onEnd),
      () => window.removeEventListener('touchend', onEnd),
      () => handle.removeEventListener('keydown', onKeyDown),
    ];
  }

  ngOnDestroy(): void {
    this.cleanupFns.forEach((fn) => fn());
  }

  private updateFromClientX(clientX: number, container: HTMLDivElement): void {
    const rect = container.getBoundingClientRect();
    const pct = ((clientX - rect.left) / rect.width) * 100;
    this.position.set(Math.min(100, Math.max(0, pct)));
  }
}
