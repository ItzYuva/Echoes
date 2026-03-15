import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-decision-log',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="min-h-screen px-4 pt-16 pb-12">
      <div class="max-w-[600px] mx-auto">
        <h1 class="font-story text-2xl text-echoes-text mb-2">Decision Log</h1>
        <p class="font-ui text-sm text-echoes-text-tertiary mb-8">
          Track what you decided. Someday you'll look back.
        </p>

        <!-- Log new decision -->
        <div class="mb-10 p-4 rounded bg-echoes-bg-secondary border border-echoes-border">
          <p class="font-ui text-sm text-echoes-text-secondary mb-3">
            Log a decision
          </p>
          <textarea
            [(ngModel)]="newDecisionText"
            placeholder="What did you decide?"
            rows="2"
            class="w-full bg-echoes-bg-tertiary border border-echoes-border rounded px-3 py-2
                   font-story text-base text-echoes-text resize-none mb-3
                   focus:border-echoes-accent-warm focus:outline-none"
          ></textarea>
          <div class="flex gap-3 items-center">
            <input
              [(ngModel)]="newDecisionType"
              placeholder="Type (e.g., career)"
              class="flex-1 bg-echoes-bg-tertiary border border-echoes-border rounded px-3 py-2
                     font-ui text-sm text-echoes-text
                     focus:border-echoes-accent-warm focus:outline-none"
            />
            <button
              (click)="logDecision()"
              [disabled]="!newDecisionText.trim() || logging"
              class="px-4 py-2 border border-echoes-accent-warm rounded text-sm font-ui
                     text-echoes-accent-warm hover:bg-echoes-accent-warm/10
                     disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              {{ logging ? 'Saving...' : 'Log it' }}
            </button>
          </div>
        </div>

        <!-- Decisions list -->
        @if (loading) {
          <p class="font-story text-echoes-text-secondary italic animate-breathe">Loading...</p>
        } @else if (decisions.length === 0) {
          <p class="font-story text-echoes-text-tertiary italic text-center py-12">
            No decisions logged yet.
          </p>
        } @else {
          <div class="space-y-4">
            @for (d of decisions; track d.id) {
              <div class="p-4 border border-echoes-border rounded">
                <p class="font-story text-base text-echoes-text">
                  {{ d.decisionText }}
                </p>
                <div class="flex gap-4 mt-2 font-meta text-xs text-echoes-text-tertiary">
                  @if (d.decisionType) {
                    <span>{{ d.decisionType }}</span>
                  }
                  @if (d.chosenPath) {
                    <span>Path: {{ d.chosenPath }}</span>
                  }
                  <span>{{ d.createdAt | date:'mediumDate' }}</span>
                </div>
                @if (d.followUpAt) {
                  <p class="font-meta text-xs text-echoes-accent-cool mt-1">
                    Follow-up scheduled: {{ d.followUpAt | date:'mediumDate' }}
                  </p>
                }
              </div>
            }
          </div>
        }
      </div>
    </div>
  `,
})
export class DecisionLogComponent implements OnInit {
  decisions: any[] = [];
  loading = true;
  logging = false;
  newDecisionText = '';
  newDecisionType = '';

  constructor(private api: ApiService, private auth: AuthService) {}

  ngOnInit(): void {
    this.loadDecisions();
  }

  loadDecisions(): void {
    const userId = this.auth.userId;
    if (!userId) return;

    this.api.getDecisions(userId).subscribe({
      next: (decisions) => {
        this.decisions = decisions || [];
        this.loading = false;
      },
      error: () => {
        this.loading = false;
      },
    });
  }

  logDecision(): void {
    const userId = this.auth.userId;
    if (!userId || !this.newDecisionText.trim()) return;

    this.logging = true;
    this.api
      .logDecision({
        userId,
        decisionText: this.newDecisionText.trim(),
        decisionType: this.newDecisionType.trim() || undefined,
      })
      .subscribe({
        next: () => {
          this.newDecisionText = '';
          this.newDecisionType = '';
          this.logging = false;
          this.loadDecisions();
        },
        error: () => {
          this.logging = false;
        },
      });
  }
}
