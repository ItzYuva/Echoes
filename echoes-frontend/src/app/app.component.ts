import { Component } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AuthService } from './core/services/auth.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <div class="min-h-screen bg-echoes-bg text-echoes-text">
      <!-- Minimal nav — only shown after intake -->
      @if (auth.isIntakeCompleted) {
        <nav class="fixed top-0 right-0 p-4 z-50 flex gap-6 font-ui text-sm text-echoes-text-secondary">
          <a routerLink="/query" routerLinkActive="text-echoes-accent-warm"
             class="hover:text-echoes-text transition-colors duration-150">Query</a>
          <a routerLink="/profile" routerLinkActive="text-echoes-accent-warm"
             class="hover:text-echoes-text transition-colors duration-150">Profile</a>
          <a routerLink="/decisions" routerLinkActive="text-echoes-accent-warm"
             class="hover:text-echoes-text transition-colors duration-150">Decisions</a>
        </nav>
      }

      <router-outlet />
    </div>
  `,
})
export class AppComponent {
  constructor(public auth: AuthService) {}
}
