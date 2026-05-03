import { Routes } from '@angular/router';
import { HomeComponent } from './home/home.component';

export const routes: Routes = [
  { path: '', component: HomeComponent },
  {
    path: 'gallery',
    loadComponent: () =>
      import('./gallery/gallery.component').then((m) => m.GalleryComponent),
  },
  {
    path: 't/:id',
    loadComponent: () =>
      import('./transformation/transformation-view.component').then(
        (m) => m.TransformationViewComponent,
      ),
  },
  { path: '**', redirectTo: '' },
];
