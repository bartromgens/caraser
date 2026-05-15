import { Component, Input, ChangeDetectionStrategy } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-gallery-card',
  standalone: true,
  imports: [RouterLink, MatIconModule],
  templateUrl: './gallery-card.component.html',
  styleUrl: './gallery-card.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GalleryCardComponent {
  @Input() src: string | null = null;
  @Input() alt = '';
  @Input() itemId: number | string = '';
  @Input() imgLoading: 'eager' | 'lazy' = 'lazy';
  @Input() imgFetchPriority: 'high' | 'low' | 'auto' = 'auto';
  @Input() borderRadius = '16px';
}
