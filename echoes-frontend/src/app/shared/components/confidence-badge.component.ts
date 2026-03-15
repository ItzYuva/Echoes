import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-confidence-badge',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="relative inline-block">
      <button
        (click)="showTooltip = !showTooltip"
        class="flex items-center gap-2 px-3 py-1 rounded-full text-xs font-meta
               bg-echoes-bg-secondary border border-echoes-border
               hover:border-echoes-text-tertiary transition-colors cursor-pointer"
      >
        <span
          class="w-2 h-2 rounded-full"
          [ngClass]="{
            'bg-echoes-confidence-high': level === 'high',
            'bg-echoes-confidence-medium': level === 'medium',
            'bg-echoes-confidence-low': level === 'low',
            'bg-echoes-confidence-insufficient': level === 'insufficient'
          }"
        ></span>
        <span class="text-echoes-text-secondary">{{ level }}</span>
      </button>

      @if (showTooltip) {
        <div class="absolute right-0 top-full mt-2 w-64 p-3 rounded-md
                    bg-echoes-bg-tertiary border border-echoes-border shadow-lg z-10">
          <p class="font-meta text-xs text-echoes-text-secondary mb-2">
            Score: {{ (score * 100).toFixed(0) }}%
          </p>
          @for (reason of reasons; track reason) {
            <p class="text-xs text-echoes-text-tertiary mb-1">{{ reason }}</p>
          }
        </div>
      }
    </div>
  `,
})
export class ConfidenceBadgeComponent {
  @Input() level = 'insufficient';
  @Input() score = 0;
  @Input() reasons: string[] = [];
  showTooltip = false;
}
