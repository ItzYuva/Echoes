import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-mode-toggle',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex gap-1 rounded-full bg-echoes-bg-secondary border border-echoes-border p-1">
      <button
        (click)="modeChange.emit('quiet')"
        class="px-3 py-1 rounded-full text-xs font-ui transition-colors duration-150"
        [ngClass]="mode === 'quiet'
          ? 'bg-echoes-bg-tertiary text-echoes-text'
          : 'text-echoes-text-tertiary hover:text-echoes-text-secondary'"
      >
        Quiet
      </button>
      <button
        (click)="modeChange.emit('explorer')"
        class="px-3 py-1 rounded-full text-xs font-ui transition-colors duration-150"
        [ngClass]="mode === 'explorer'
          ? 'bg-echoes-bg-tertiary text-echoes-text'
          : 'text-echoes-text-tertiary hover:text-echoes-text-secondary'"
      >
        Explorer
      </button>
    </div>
  `,
})
export class ModeToggleComponent {
  @Input() mode: 'quiet' | 'explorer' = 'quiet';
  @Output() modeChange = new EventEmitter<'quiet' | 'explorer'>();
}
