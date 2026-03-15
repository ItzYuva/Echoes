export interface ValuesVector {
  riskTolerance: number;
  changeOrientation: number;
  securityVsGrowth: number;
  actionBias: number;
  socialWeight: number;
  timeHorizon: number;
  lossSensitivity: number;
  ambiguityTolerance: number;
}

export const DIMENSION_LABELS: Record<keyof ValuesVector, [string, string]> = {
  riskTolerance: ['Risk-averse', 'Risk-seeking'],
  changeOrientation: ['Stability-seeking', 'Change-seeking'],
  securityVsGrowth: ['Security-driven', 'Growth-driven'],
  actionBias: ['Deliberate', 'Act fast'],
  socialWeight: ['Independent', 'Relational'],
  timeHorizon: ['Present-focused', 'Future-focused'],
  lossSensitivity: ['Loss-fearful', 'Gain-excited'],
  ambiguityTolerance: ['Needs clarity', 'Comfortable with grey'],
};
