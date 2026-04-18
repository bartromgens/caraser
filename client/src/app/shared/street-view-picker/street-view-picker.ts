import {
  Component,
  ElementRef,
  EventEmitter,
  NgZone,
  OnDestroy,
  Output,
  ViewChild,
  inject,
  signal,
} from '@angular/core';
import { NgIf } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { importLibrary, setOptions } from '@googlemaps/js-api-loader';
import { firstValueFrom } from 'rxjs';

type PickerState = 'idle' | 'loading' | 'ready' | 'capturing' | 'error';

@Component({
  selector: 'app-street-view-picker',
  standalone: true,
  imports: [
    NgIf,
    FormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './street-view-picker.html',
  styleUrl: './street-view-picker.scss',
})
export class StreetViewPickerComponent implements OnDestroy {
  @Output() imageSelected = new EventEmitter<File>();
  @ViewChild('panoramaContainer') containerRef!: ElementRef<HTMLDivElement>;

  private readonly http = inject(HttpClient);
  private readonly zone = inject(NgZone);

  address = '';
  state = signal<PickerState>('idle');
  statusMessage = signal('');

  private panorama: google.maps.StreetViewPanorama | null = null;
  private apiKey = '';
  private mapsConfigured = false;

  get isPanoramaVisible(): boolean {
    const s = this.state();
    return s === 'ready' || s === 'capturing';
  }

  async loadStreetView(): Promise<void> {
    if (!this.address.trim()) return;

    this.zone.run(() => {
      this.state.set('loading');
      this.statusMessage.set('');
    });

    if (this.panorama) {
      this.panorama.unbindAll();
      this.panorama = null;
      this.containerRef.nativeElement.innerHTML = '';
    }

    try {
      if (!this.apiKey) {
        const cfg = await firstValueFrom(
          this.http.get<{ google_maps_api_key: string }>('/api/config/'),
        );
        this.apiKey = cfg.google_maps_api_key;
      }

      if (!this.mapsConfigured) {
        setOptions({ key: this.apiKey, v: 'weekly' });
        this.mapsConfigured = true;
      }

      const [{ Geocoder }, { StreetViewService, StreetViewPanorama }, geometry] =
        await Promise.all([
          importLibrary('geocoding'),
          importLibrary('streetView'),
          importLibrary('geometry'),
        ]);

      const geocodeResult = await new Geocoder().geocode({ address: this.address.trim() });
      if (!geocodeResult.results.length) {
        this.setError('Address not found. Please try a more specific address.');
        return;
      }
      const addressLatLng = geocodeResult.results[0].geometry.location;

      let panoResult: google.maps.StreetViewResponse;
      try {
        panoResult = await new StreetViewService().getPanorama({
          location: addressLatLng,
          radius: 100,
        });
      } catch {
        this.setError('No Street View imagery found near this address.');
        return;
      }

      if (!panoResult.data?.location?.latLng) {
        this.setError('No Street View imagery found near this address.');
        return;
      }

      const panoLocation = panoResult.data.location;
      const heading = geometry.spherical.computeHeading(panoLocation.latLng!, addressLatLng);

      this.zone.run(() => this.state.set('ready'));

      // Allow Angular to render the visible panorama container before mounting
      await new Promise<void>((resolve) => setTimeout(resolve, 0));

      this.panorama = new StreetViewPanorama(this.containerRef.nativeElement, {
        pano: panoLocation.pano,
        pov: { heading, pitch: 0 },
        addressControl: false,
        fullscreenControl: false,
        motionTrackingControl: false,
        showRoadLabels: false,
        zoomControl: true,
      });
    } catch (err) {
      this.setError('Could not load Street View. Check the address and try again.');
      console.error(err);
    }
  }

  async useThisView(): Promise<void> {
    if (!this.panorama) return;
    this.zone.run(() => {
      this.state.set('capturing');
      this.statusMessage.set('');
    });

    try {
      const pov = this.panorama.getPov();
      const pos = this.panorama.getPosition();
      if (!pos) {
        this.zone.run(() => {
          this.state.set('ready');
          this.statusMessage.set(
            'Could not read the current position. Try panning slightly and retry.',
          );
        });
        return;
      }

      const params = new URLSearchParams({
        size: '640x640',
        scale: '2',
        location: `${pos.lat()},${pos.lng()}`,
        heading: String(pov.heading ?? 0),
        pitch: String(pov.pitch ?? 0),
        fov: '90',
        key: this.apiKey,
        return_error_code: 'true',
      });
      const response = await fetch(
        `https://maps.googleapis.com/maps/api/streetview?${params}`,
      );
      if (!response.ok) {
        this.zone.run(() => {
          this.state.set('ready');
          this.statusMessage.set('Could not retrieve the Street View image. Please try again.');
        });
        return;
      }
      const blob = await response.blob();
      const file = new File([blob], 'streetview.jpg', { type: 'image/jpeg' });
      this.zone.run(() => this.imageSelected.emit(file));
    } catch (err) {
      this.zone.run(() => {
        this.state.set('ready');
        this.statusMessage.set('Failed to capture the view. Please try again.');
      });
      console.error(err);
    }
  }

  ngOnDestroy(): void {
    if (this.panorama) {
      this.panorama.unbindAll();
      this.panorama = null;
    }
  }

  private setError(message: string): void {
    this.zone.run(() => {
      this.state.set('error');
      this.statusMessage.set(message);
    });
  }
}
