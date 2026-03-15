export interface Story {
  id: string;
  decisionType: string;
  decisionSubcategory: string;
  outcomeSentiment: string;
  timeElapsedMonths: number;
  emotionalRichness: number;
  keyThemes: string[];
  hindsightInsight: string;
  isCounterNarrative: boolean;
  compositeScore: number;
}
