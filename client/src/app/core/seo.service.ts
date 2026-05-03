import { Injectable, inject } from '@angular/core';
import { Title, Meta } from '@angular/platform-browser';

const DEFAULT_TITLE = 'Caraser – See your street without cars';
const DEFAULT_DESCRIPTION =
  'Upload a street photo and see what it looks like without cars. Caraser uses AI to replace cars with trees, benches, greenery and people.';

@Injectable({ providedIn: 'root' })
export class SeoService {
  private readonly titleService = inject(Title);
  private readonly meta = inject(Meta);

  set(opts: { title?: string; description?: string } = {}): void {
    const title = opts.title ? `${opts.title} | Caraser` : DEFAULT_TITLE;
    const description = opts.description ?? DEFAULT_DESCRIPTION;
    this.titleService.setTitle(title);
    this.meta.updateTag({ name: 'description', content: description });
  }

  reset(): void {
    this.set();
  }
}
