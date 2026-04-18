import { Routes } from '@angular/router';
import { HomeComponent } from './home/home';

export const routes: Routes = [
  { path: '', component: HomeComponent },
  {
    path: 'gallery',
    loadComponent: () =>
      import('./gallery/gallery').then((m) => m.GalleryComponent),
  },
  {
    path: 't/:id',
    loadComponent: () =>
      import('./transformation/transformation-view').then(
        (m) => m.TransformationViewComponent,
      ),
  },
  { path: '**', redirectTo: '' },
];
