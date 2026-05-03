import { Component, OnInit, inject, signal } from '@angular/core';
import { NgIf, NgFor } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

import { TransformationService, Transformation } from '../../core/transformation.service';

@Component({
  selector: 'app-featured-strip',
  standalone: true,
  imports: [NgIf, NgFor, RouterLink, MatButtonModule, MatIconModule],
  templateUrl: './featured-strip.component.html',
  styleUrl: './featured-strip.component.scss',
})
export class FeaturedStripComponent implements OnInit {
  private readonly service = inject(TransformationService);

  items = signal<Transformation[]>([]);

  ngOnInit(): void {
    this.service.list(1, { featured: true, pageSize: 6 }).subscribe({
      next: (res) => this.items.set(res.results),
      error: () => {},
    });
  }
}
