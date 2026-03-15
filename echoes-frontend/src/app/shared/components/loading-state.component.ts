import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-loading-state',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex flex-col items-center justify-center py-16 gap-6">
      <!-- Breathing dots -->
      <div class="flex gap-2">
        <span class="w-2 h-2 rounded-full bg-echoes-accent-warm animate-breathe"
              [style.animation-delay]="'0s'"></span>
        <span class="w-2 h-2 rounded-full bg-echoes-accent-warm animate-breathe"
              [style.animation-delay]="'0.5s'"></span>
        <span class="w-2 h-2 rounded-full bg-echoes-accent-warm animate-breathe"
              [style.animation-delay]="'1s'"></span>
      </div>

      <p class="font-story text-echoes-text-secondary text-lg italic">
        {{ message }}
      </p>

      @if (secondaryMessage) {
        <p class="font-ui text-echoes-text-tertiary text-sm mt-2 animate-fade-in">
          {{ secondaryMessage }}
        </p>
      }
    </div>
  `,
})
export class LoadingStateComponent {
  @Input() message = 'Understanding your situation...';
  @Input() secondaryMessage: string | null = null;
}
