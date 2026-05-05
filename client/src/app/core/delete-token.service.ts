import { Injectable } from '@angular/core';

const STORAGE_KEY = 'caraser:tokens';

@Injectable({ providedIn: 'root' })
export class DeleteTokenService {
  private load(): Record<string, string> {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}');
    } catch {
      return {};
    }
  }

  private persist(map: Record<string, string>): void {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(map));
  }

  save(id: string, token: string): void {
    const map = this.load();
    map[id] = token;
    this.persist(map);
  }

  get(id: string): string | null {
    return this.load()[id] ?? null;
  }

  has(id: string): boolean {
    return id in this.load();
  }

  ids(): string[] {
    return Object.keys(this.load());
  }

  remove(id: string): void {
    const map = this.load();
    delete map[id];
    this.persist(map);
  }
}
