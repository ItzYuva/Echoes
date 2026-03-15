import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';
import { ValuesVector, DIMENSION_LABELS } from '../../core/models/values-vector.model';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="min-h-screen px-4 pt-16 pb-12">
      <div class="max-w-[600px] mx-auto">
        <h1 class="font-story text-2xl text-echoes-text mb-2">Your Values Profile</h1>
        <p class="font-ui text-sm text-echoes-text-tertiary mb-8">
          This is who you are when you decide. Adjust if anything feels off.
        </p>

        @if (loading) {
          <p class="font-story text-echoes-text-secondary italic animate-breathe">Loading...</p>
        } @else if (dimensions.length > 0) {
          <div class="space-y-5">
            @for (dim of dimensions; track dim.key) {
              <div>
                <div class="flex justify-between font-meta text-xs text-echoes-text-secondary mb-1">
                  <span>{{ dim.labels[0] }}</span>
                  <span class="font-meta text-echoes-text-tertiary">
                    {{ (dim.value * 100).toFixed(0) }}%
                  </span>
                  <span>{{ dim.labels[1] }}</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.01"
                  [(ngModel)]="dim.value"
                  class="w-full h-1.5 rounded-full appearance-none bg-echoes-bg-tertiary
                         cursor-pointer accent-echoes-accent-warm"
                />
              </div>
            }
          </div>

          <div class="flex gap-4 mt-8">
            <button
              (click)="saveProfile()"
              [disabled]="saving"
              class="px-5 py-2 border border-echoes-accent-warm rounded text-sm font-ui
                     text-echoes-accent-warm hover:bg-echoes-accent-warm/10
                     disabled:opacity-50 transition-colors"
            >
              {{ saving ? 'Saving...' : 'Save changes' }}
            </button>
            <button
              (click)="router.navigate(['/intake'])"
              class="px-5 py-2 border border-echoes-border rounded text-sm font-ui
                     text-echoes-text-secondary hover:border-echoes-text-tertiary
                     transition-colors"
            >
              Retake intake
            </button>
          </div>

          <!-- Version history -->
          @if (history.length > 0) {
            <div class="mt-12">
              <p class="font-ui text-xs text-echoes-text-tertiary uppercase tracking-wider mb-3">
                Version history
              </p>
              @for (version of history; track version.id) {
                <div class="flex justify-between py-2 border-b border-echoes-border font-meta text-xs">
                  <span class="text-echoes-text-secondary">v{{ version.version }}</span>
                  <span class="text-echoes-text-tertiary">{{ version.source }}</span>
                  <span class="text-echoes-text-tertiary">{{ version.created_at | date:'short' }}</span>
                </div>
              }
            </div>
          }

          <!-- Metadata -->
          @if (profileMeta) {
            <div class="mt-8 font-meta text-xs text-echoes-text-tertiary">
              <p>Created: {{ profileMeta.createdAt }}</p>
              <p>{{ profileMeta.intakeTurns }} turns &middot; {{ profileMeta.intakeDurationSeconds }}s</p>
            </div>
          }
        }
      </div>
    </div>
  `,
})
export class ProfileComponent implements OnInit {
  dimensions: { key: keyof ValuesVector; labels: [string, string]; value: number }[] = [];
  history: any[] = [];
  profileMeta: any = null;
  loading = true;
  saving = false;

  constructor(
    private api: ApiService,
    private auth: AuthService,
    public router: Router
  ) {}

  ngOnInit(): void {
    const userId = this.auth.userId;
    if (!userId) return;

    this.api.getProfile(userId).subscribe({
      next: (profile) => {
        const vv = profile.valuesVector;
        this.dimensions = (Object.keys(DIMENSION_LABELS) as (keyof ValuesVector)[]).map(
          (key) => ({
            key,
            labels: DIMENSION_LABELS[key],
            value: vv[key] ?? 0.5,
          })
        );
        this.profileMeta = profile;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
      },
    });

    this.api.getProfileHistory(userId).subscribe({
      next: (h) => {
        this.history = h || [];
      },
    });
  }

  saveProfile(): void {
    const userId = this.auth.userId;
    if (!userId) return;

    this.saving = true;
    const vv: any = {};
    for (const dim of this.dimensions) {
      vv[dim.key] = dim.value;
    }

    this.api.updateProfile(userId, vv).subscribe({
      next: () => {
        this.saving = false;
      },
      error: () => {
        this.saving = false;
      },
    });
  }
}
