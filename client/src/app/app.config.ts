import {
  ApplicationConfig,
  inject,
  provideBrowserGlobalErrorListeners,
  provideAppInitializer,
} from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient, withXsrfConfiguration } from '@angular/common/http';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideMatomo, withRouter } from 'ngx-matomo-client';

import { routes } from './app.routes';
import { environment } from '../environments/environment';
import { AuthService } from './core/auth.service';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes),
    provideHttpClient(
      withXsrfConfiguration({ cookieName: 'csrftoken', headerName: 'X-CSRFToken' }),
    ),
    provideAnimationsAsync(),
    provideAppInitializer(() => inject(AuthService).refresh()),
    ...(environment.matomo.enabled
      ? [
          provideMatomo(
            {
              siteId: environment.matomo.siteId,
              trackerUrl: environment.matomo.trackerUrl,
            },
            withRouter(),
          ),
        ]
      : []),
  ],
};
