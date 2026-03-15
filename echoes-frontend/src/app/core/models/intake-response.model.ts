import { ValuesVector } from './values-vector.model';

export interface IntakeResponse {
  sessionId: string;
  message: string;
  turnNumber: number;
  isComplete: boolean;
  complete: boolean; // alias from backend
  valuesVector?: ValuesVector;
}
