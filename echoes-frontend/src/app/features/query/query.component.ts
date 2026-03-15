import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';
import { QueryResponse } from '../../core/models/query-response.model';
import { LoadingStateComponent } from '../../shared/components/loading-state.component';
import { ConfidenceBadgeComponent } from '../../shared/components/confidence-badge.component';
import { ModeToggleComponent } from '../../shared/components/mode-toggle.component';
import { QuietModeComponent } from '../quiet-mode/quiet-mode.component';
import { ExplorerModeComponent } from '../explorer-mode/explorer-mode.component';

type QueryStatus = 'idle' | 'analyzing' | 'searching' | 'complete';

@Component({
  selector: 'app-query',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    LoadingStateComponent,
    ConfidenceBadgeComponent,
    ModeToggleComponent,
    QuietModeComponent,
    ExplorerModeComponent,
  ],
  template: `
    <div class="min-h-screen px-4 pt-16 pb-12">
      <div class="max-w-[700px] mx-auto">
        <!-- Query input -->
        <div class="mb-12">
          <textarea
            [(ngModel)]="decisionText"
            (keydown)="onKeydown($event)"
            [disabled]="status !== 'idle'"
            placeholder="What decision are you facing?"
            rows="3"
            class="w-full bg-transparent border-b border-echoes-border
                   font-story text-xl text-echoes-text
                   placeholder:text-echoes-text-tertiary
                   focus:border-echoes-accent-warm focus:outline-none
                   disabled:opacity-50 resize-none pb-4 transition-colors"
          ></textarea>

          @if (status === 'idle') {
            <div class="flex justify-between items-center mt-3">
              <p class="font-meta text-xs text-echoes-text-tertiary">
                Ctrl+Enter to submit
              </p>
              <button
                (click)="submitQuery()"
                [disabled]="!decisionText.trim()"
                class="px-5 py-2 border border-echoes-border rounded text-sm font-ui
                       text-echoes-text-secondary
                       hover:border-echoes-accent-warm hover:text-echoes-text
                       disabled:opacity-30 disabled:cursor-not-allowed
                       transition-colors duration-150"
              >
                Ask Echoes
              </button>
            </div>
          }
        </div>

        <!-- Error message -->
        @if (errorMessage) {
          <div class="mb-8 p-4 border border-red-800 rounded bg-red-900/20">
            <p class="font-ui text-sm text-red-400">{{ errorMessage }}</p>
          </div>
        }

        <!-- Loading state -->
        @if (status === 'analyzing' || status === 'searching') {
          <app-loading-state
            [message]="status === 'analyzing'
              ? 'Understanding your situation...'
              : 'Searching for stories that match...'"
            [secondaryMessage]="status === 'searching'
              ? 'Finding people who stood where you\\'re standing...'
              : null"
          />
        }

        <!-- Results -->
        @if (status === 'complete' && response) {
          <div class="animate-fade-in">
            <!-- Header bar: confidence + mode toggle -->
            <div class="flex justify-between items-center mb-8">
              <app-confidence-badge
                [level]="response.confidence.level"
                [score]="response.confidence.score"
                [reasons]="response.confidence.reasons"
              />
              <app-mode-toggle
                [mode]="viewMode"
                (modeChange)="viewMode = $event"
              />
            </div>

            <!-- Quiet Mode -->
            @if (viewMode === 'quiet') {
              <app-quiet-mode
                [presentationText]="response.presentation.text"
                [stories]="response.stories"
              />
            }

            <!-- Explorer Mode -->
            @if (viewMode === 'explorer') {
              <app-explorer-mode
                [response]="response"
              />
            }

            <!-- Metadata footer -->
            <div class="mt-12 pt-4 border-t border-echoes-border">
              <p class="font-meta text-xs text-echoes-text-tertiary">
                {{ response.stories.length }} stories from {{ response.metadata.candidatesFound }} candidates
                &middot; {{ response.metadata.totalLatencyMs }}ms
                @if (response.metadata.liveSearchUsed) {
                  &middot; live search active
                }
              </p>
            </div>

            <!-- New query -->
            <button
              (click)="reset()"
              class="mt-6 px-4 py-2 border border-echoes-border rounded text-sm font-ui
                     text-echoes-text-secondary hover:border-echoes-accent-warm
                     hover:text-echoes-text transition-colors"
            >
              Ask another question
            </button>
          </div>
        }
      </div>
    </div>
  `,
})
export class QueryComponent {
  decisionText = '';
  status: QueryStatus = 'idle';
  viewMode: 'quiet' | 'explorer' = 'quiet';
  response: QueryResponse | null = null;
  errorMessage: string | null = null;

  constructor(private api: ApiService) {}

  onKeydown(event: KeyboardEvent): void {
    if (event.ctrlKey && event.key === 'Enter') {
      this.submitQuery();
    }
  }

  submitQuery(): void {
    const text = this.decisionText.trim();
    if (!text) return;

    this.status = 'analyzing';
    this.response = null;
    this.errorMessage = null;

    // Simulate phase transition after 2.5s
    const phaseTimer = setTimeout(() => {
      if (this.status === 'analyzing') {
        this.status = 'searching';
      }
    }, 2500);

    this.api.submitQuery(text).subscribe({
      next: (res) => {
        clearTimeout(phaseTimer);
        this.response = res;
        this.status = 'complete';
      },
      error: (err) => {
        clearTimeout(phaseTimer);
        this.status = 'idle';
        this.errorMessage = err?.error?.message || err?.message || 'Something went wrong. Please try again.';
        console.error('Query failed:', err);
      },
    });
  }

  reset(): void {
    this.decisionText = '';
    this.status = 'idle';
    this.response = null;
    this.viewMode = 'quiet';
  }
}
