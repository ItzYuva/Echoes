import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { intakeCompleteGuard } from './core/guards/intake-complete.guard';

export const routes: Routes = [
  { path: '', redirectTo: '/intake', pathMatch: 'full' },
  {
    path: 'intake',
    loadComponent: () =>
      import('./features/intake/intake.component').then((m) => m.IntakeComponent),
    canActivate: [authGuard],
  },
  {
    path: 'query',
    loadComponent: () =>
      import('./features/query/query.component').then((m) => m.QueryComponent),
    canActivate: [authGuard, intakeCompleteGuard],
  },
  {
    path: 'profile',
    loadComponent: () =>
      import('./features/profile/profile.component').then((m) => m.ProfileComponent),
    canActivate: [authGuard, intakeCompleteGuard],
  },
  {
    path: 'decisions',
    loadComponent: () =>
      import('./features/decision-log/decision-log.component').then(
        (m) => m.DecisionLogComponent
      ),
    canActivate: [authGuard, intakeCompleteGuard],
  },
];
