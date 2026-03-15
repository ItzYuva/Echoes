import { Component, Input, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Story } from '../../core/models/story.model';

@Component({
  selector: 'app-quiet-mode',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="space-y-8">
      <!-- Presentation text rendered as paragraphs -->
      @for (paragraph of paragraphs; track $index) {
        <div
          class="animate-fade-in"
          [style.animation-delay]="$index * 200 + 'ms'"
          [style.opacity]="0"
          [style.animation-fill-mode]="'forwards'"
        >
          @if (isSeparator(paragraph)) {
            <hr class="border-echoes-border my-8" />
          } @else {
            <p class="font-story text-lg leading-[1.8] text-echoes-text">
              {{ paragraph }}
            </p>
          }
        </div>
      }

      <!-- Story metadata (subtle, at bottom) -->
      @if (stories.length > 0) {
        <div class="mt-12 space-y-4">
          <p class="font-ui text-xs text-echoes-text-tertiary uppercase tracking-wider">
            Stories referenced
          </p>
          @for (story of stories; track story.id) {
            <div
              class="pl-4 border-l border-echoes-border animate-fade-in"
              [style.animation-delay]="($index + paragraphs.length) * 150 + 'ms'"
              [style.opacity]="0"
              [style.animation-fill-mode]="'forwards'"
            >
              <p class="font-meta text-xs text-echoes-text-secondary">
                {{ story.decisionSubcategory }}
                &middot;
                <span [ngClass]="{
                  'text-echoes-confidence-high': story.outcomeSentiment === 'positive',
                  'text-echoes-confidence-medium': story.outcomeSentiment === 'mixed',
                  'text-echoes-confidence-low': story.outcomeSentiment === 'negative'
                }">
                  {{ story.outcomeSentiment }}
                </span>
                @if (story.timeElapsedMonths > 0) {
                  &middot; {{ formatTime(story.timeElapsedMonths) }} later
                }
              </p>
              @if (story.hindsightInsight) {
                <p class="font-story text-sm text-echoes-text-secondary mt-1 italic">
                  "{{ story.hindsightInsight }}"
                </p>
              }
            </div>
          }
        </div>
      }
    </div>
  `,
})
export class QuietModeComponent implements OnInit {
  @Input() presentationText = '';
  @Input() stories: Story[] = [];

  paragraphs: string[] = [];

  ngOnInit(): void {
    this.paragraphs = this.presentationText
      .split('\n')
      .map((p) => p.trim())
      .filter((p) => p.length > 0);
  }

  isSeparator(text: string): boolean {
    return /^[-—─═]{3,}$/.test(text);
  }

  formatTime(months: number): string {
    if (months < 12) return `${months} months`;
    const years = Math.floor(months / 12);
    const remaining = months % 12;
    if (remaining === 0) return `${years} year${years > 1 ? 's' : ''}`;
    return `${years}y ${remaining}m`;
  }
}
