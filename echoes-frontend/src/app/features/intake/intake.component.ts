import { Component, OnInit, ElementRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';
import { ValuesVector, DIMENSION_LABELS } from '../../core/models/values-vector.model';

interface Message {
  role: 'assistant' | 'user';
  content: string;
}

@Component({
  selector: 'app-intake',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <!-- Redirect if already completed -->
    @if (auth.isIntakeCompleted && !showingResults) {
      <div class="min-h-screen flex items-center justify-center">
        <div class="text-center">
          <p class="font-story text-lg text-echoes-text-secondary mb-4">
            You've already completed your intake.
          </p>
          <button
            (click)="router.navigate(['/query'])"
            class="px-6 py-2 border border-echoes-border rounded text-sm
                   hover:border-echoes-accent-warm transition-colors"
          >
            Go to Query
          </button>
        </div>
      </div>
    } @else {
      <div class="h-screen flex flex-col">
        <!-- Messages area -->
        <div
          #messagesContainer
          class="flex-1 overflow-y-auto px-4 pt-16 pb-48"
        >
          <div class="max-w-[600px] mx-auto space-y-6">
            @for (msg of messages; track $index) {
              <div
                class="animate-fade-in"
                [style.animation-delay]="$index * 100 + 'ms'"
              >
                @if (msg.role === 'assistant') {
                  <p class="font-story text-lg leading-relaxed text-echoes-text">
                    {{ msg.content }}
                  </p>
                } @else {
                  <p class="font-story text-lg leading-relaxed text-echoes-text opacity-70 pl-4
                            border-l border-echoes-border">
                    {{ msg.content }}
                  </p>
                }
              </div>
            }

            @if (isLoading) {
              <div class="animate-breathe font-story text-echoes-text-secondary">
                ...
              </div>
            }

            <!-- Values vector visualization -->
            @if (showingResults && valuesVector) {
              <div class="mt-12 animate-fade-in">
                <p class="font-ui text-sm text-echoes-text-tertiary mb-6 uppercase tracking-wider">
                  Your Values Profile
                </p>
                @for (dim of dimensions; track dim.key) {
                  <div class="mb-3">
                    <div class="flex justify-between font-meta text-xs text-echoes-text-secondary mb-1">
                      <span>{{ dim.labels[0] }}</span>
                      <span>{{ dim.labels[1] }}</span>
                    </div>
                    <div class="h-1.5 bg-echoes-bg-tertiary rounded-full overflow-hidden">
                      <div
                        class="h-full bg-echoes-accent-warm rounded-full transition-all duration-slow"
                        [style.width.%]="dim.value * 100"
                      ></div>
                    </div>
                  </div>
                }
              </div>
            }
          </div>
        </div>

        <!-- Error message -->
        @if (errorMessage) {
          <div class="fixed bottom-28 left-0 right-0 flex justify-center z-10">
            <div class="max-w-[600px] w-full mx-4 p-3 border border-red-800 rounded bg-red-900/20">
              <p class="font-ui text-sm text-red-400">{{ errorMessage }}</p>
            </div>
          </div>
        }

        <!-- Input area -->
        @if (!showingResults) {
          <div class="fixed bottom-0 left-0 right-0 bg-echoes-bg border-t border-echoes-border">
            <div class="max-w-[600px] mx-auto p-4">
              <textarea
                [(ngModel)]="userInput"
                (keydown.enter)="onEnter($event)"
                [disabled]="isLoading"
                placeholder="Share your thoughts..."
                rows="2"
                class="w-full bg-echoes-bg-tertiary border border-echoes-border rounded-lg px-4 py-3
                       font-story text-base text-echoes-text resize-none
                       focus:border-echoes-accent-warm focus:outline-none
                       disabled:opacity-50 transition-colors"
              ></textarea>
              <p class="font-meta text-xs text-echoes-text-tertiary mt-1 text-right">
                Press Enter to send
              </p>
            </div>
          </div>
        }
      </div>
    }
  `,
})
export class IntakeComponent implements OnInit {
  @ViewChild('messagesContainer') messagesContainer!: ElementRef;

  messages: Message[] = [];
  userInput = '';
  isLoading = false;
  sessionId: string | null = null;
  showingResults = false;
  valuesVector: ValuesVector | null = null;
  dimensions: { key: string; labels: [string, string]; value: number }[] = [];
  errorMessage: string | null = null;

  constructor(
    public auth: AuthService,
    private api: ApiService,
    public router: Router
  ) {}

  ngOnInit(): void {
    if (!this.auth.isIntakeCompleted) {
      this.startIntake();
    }
  }

  startIntake(): void {
    this.isLoading = true;
    this.api.startIntake().subscribe({
      next: (res) => {
        this.sessionId = res.sessionId;
        this.messages.push({ role: 'assistant', content: res.message });
        this.isLoading = false;
        this.scrollToBottom();
      },
      error: () => {
        this.isLoading = false;
      },
    });
  }

  onEnter(event: Event): void {
    event.preventDefault();
    const text = this.userInput.trim();
    if (!text || this.isLoading || !this.sessionId) return;

    this.messages.push({ role: 'user', content: text });
    this.userInput = '';
    this.isLoading = true;
    this.scrollToBottom();

    this.errorMessage = null;
    this.api.respondIntake(this.sessionId, text).subscribe({
      next: (res) => {
        console.log('Intake response:', JSON.stringify(res));
        this.messages.push({ role: 'assistant', content: res.message });
        this.isLoading = false;
        this.scrollToBottom();

        if (res.isComplete || res.complete) {
          this.handleIntakeComplete(res.valuesVector);
        }
      },
      error: (err) => {
        console.error('Intake error:', err);
        this.isLoading = false;
        this.errorMessage = err?.error?.message || err?.message || 'Something went wrong. Try again.';
      },
    });
  }

  private handleIntakeComplete(vv?: ValuesVector): void {
    this.auth.markIntakeCompleted();

    if (vv) {
      this.valuesVector = vv;
      this.dimensions = (Object.keys(DIMENSION_LABELS) as (keyof ValuesVector)[]).map(
        (key) => ({
          key,
          labels: DIMENSION_LABELS[key],
          value: vv[key] as number,
        })
      );
      this.showingResults = true;

      // Redirect after showing results
      setTimeout(() => {
        this.router.navigate(['/query']);
      }, 4000);
    } else {
      this.router.navigate(['/query']);
    }
  }

  private scrollToBottom(): void {
    setTimeout(() => {
      if (this.messagesContainer) {
        const el = this.messagesContainer.nativeElement;
        el.scrollTop = el.scrollHeight;
      }
    }, 50);
  }
}
