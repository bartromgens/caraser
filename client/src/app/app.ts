import { Component, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { RouterOutlet, RouterLink } from '@angular/router';
import { map } from 'rxjs/operators';
import { BreakpointObserver } from '@angular/cdk/layout';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';

@Component({
  selector: 'app-root',
  imports: [
    RouterOutlet,
    RouterLink,
    MatToolbarModule,
    MatSidenavModule,
    MatListModule,
    MatIconModule,
    MatButtonModule,
  ],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {
  protected readonly title = 'Caraser';

  private readonly breakpointObserver = inject(BreakpointObserver);

  protected readonly isHandset = toSignal(
    this.breakpointObserver.observe('(max-width: 959.98px)').pipe(map(r => r.matches)),
    { initialValue: false }
  );

  protected readonly sidenavOpened = signal(false);

  protected closeOnMobile(): void {
    if (this.isHandset()) {
      this.sidenavOpened.set(false);
    }
  }
}
