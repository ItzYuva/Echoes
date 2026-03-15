import { Story } from './story.model';

export interface QueryResponse {
  queryId: string;
  presentation: {
    text: string;
    storiesCount: number;
  };
  confidence: {
    score: number;
    level: string;
    reasons: string[];
  };
  queryAnalysis: {
    decisionType: string;
    decisionSubcategory: string;
    coreTension: string;
    emotionalState: string[];
    stakes: string;
    keyFactors: string[];
    whatWouldHelp: string;
  };
  stories: Story[];
  metadata: {
    totalLatencyMs: number;
    liveSearchUsed: boolean;
    agentSearching: boolean;
    candidatesFound: number;
    storiesPresented: number;
    counterNarrativeRatio: number;
  };
}
