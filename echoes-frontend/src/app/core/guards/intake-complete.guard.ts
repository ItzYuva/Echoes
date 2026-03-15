import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

export const intakeCompleteGuard: CanActivateFn = () => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (authService.isIntakeCompleted) {
    return true;
  }

  router.navigate(['/intake']);
  return false;
};
