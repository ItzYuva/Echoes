import { Component, Input, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { QueryResponse } from '../../core/models/query-response.model';
import { Story } from '../../core/models/story.model';

@Component({
  selector: 'app-explorer-mode',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="space-y-10">
      <!-- Core tension header -->
      <div class="text-center py-6">
        <p class="font-ui text-xs text-echoes-text-tertiary uppercase tracking-wider mb-2">
          Core tension
        </p>
        <p class="font-story text-xl text-echoes-accent-warm">
          {{ response.queryAnalysis.coreTension }}
        </p>
        <p class="font-meta text-xs text-echoes-text-tertiary mt-2">
          {{ response.queryAnalysis.decisionType }} &middot; {{ response.queryAnalysis.stakes }} stakes
        </p>
      </div>

      <!-- Sentiment distribution -->
      <div>
        <p class="font-ui text-xs text-echoes-text-tertiary uppercase tracking-wider mb-3">
          Outcome distribution
        </p>
        <div class="flex h-6 rounded-full overflow-hidden bg-echoes-bg-tertiary">
          @if (sentimentCounts.positive > 0) {
            <div
              class="bg-echoes-confidence-high flex items-center justify-center text-xs font-meta"
              [style.width.%]="(sentimentCounts.positive / response.stories.length) * 100"
            >
              @if (sentimentCounts.positive > 1) { {{ sentimentCounts.positive }} }
            </div>
          }
          @if (sentimentCounts.mixed > 0) {
            <div
              class="bg-echoes-confidence-medium flex items-center justify-center text-xs font-meta text-echoes-bg"
              [style.width.%]="(sentimentCounts.mixed / response.stories.length) * 100"
            >
              @if (sentimentCounts.mixed > 1) { {{ sentimentCounts.mixed }} }
            </div>
          }
          @if (sentimentCounts.negative > 0) {
            <div
              class="bg-echoes-confidence-low flex items-center justify-center text-xs font-meta"
              [style.width.%]="(sentimentCounts.negative / response.stories.length) * 100"
            >
              @if (sentimentCounts.negative > 1) { {{ sentimentCounts.negative }} }
            </div>
          }
          @if (sentimentCounts.neutral > 0) {
            <div
              class="bg-echoes-text-tertiary flex items-center justify-center text-xs font-meta"
              [style.width.%]="(sentimentCounts.neutral / response.stories.length) * 100"
            >
            </div>
          }
        </div>
        <div class="flex justify-between font-meta text-xs text-echoes-text-tertiary mt-1">
          <span class="text-echoes-confidence-high">Positive ({{ sentimentCounts.positive }})</span>
          <span class="text-echoes-confidence-medium">Mixed ({{ sentimentCounts.mixed }})</span>
          <span class="text-echoes-confidence-low">Negative ({{ sentimentCounts.negative }})</span>
        </div>
      </div>

      <!-- Time horizon chart -->
      @if (timeGroups.length > 0) {
        <div>
          <p class="font-ui text-xs text-echoes-text-tertiary uppercase tracking-wider mb-3">
            How people felt over time
          </p>
          <div class="flex items-end gap-3 h-32">
            @for (group of timeGroups; track group.label) {
              <div class="flex-1 flex flex-col items-center gap-1">
                <div class="w-full flex flex-col gap-0.5">
                  @if (group.positive > 0) {
                    <div
                      class="w-full bg-echoes-confidence-high rounded-t"
                      [style.height.px]="(group.positive / maxGroupSize) * 80"
                    ></div>
                  }
                  @if (group.mixed > 0) {
                    <div
                      class="w-full bg-echoes-confidence-medium"
                      [style.height.px]="(group.mixed / maxGroupSize) * 80"
                    ></div>
                  }
                  @if (group.negative > 0) {
                    <div
                      class="w-full bg-echoes-confidence-low rounded-b"
                      [style.height.px]="(group.negative / maxGroupSize) * 80"
                    ></div>
                  }
                </div>
                <p class="font-meta text-xs text-echoes-text-tertiary">{{ group.label }}</p>
              </div>
            }
          </div>
        </div>
      }

      <!-- Theme cloud -->
      @if (themes.length > 0) {
        <div>
          <p class="font-ui text-xs text-echoes-text-tertiary uppercase tracking-wider mb-3">
            Key themes
          </p>
          <div class="flex flex-wrap gap-2">
            @for (theme of themes; track theme.name) {
              <span
                class="px-3 py-1 rounded-full border border-echoes-border font-ui
                       transition-colors hover:border-echoes-accent-warm"
                [style.font-size.rem]="0.7 + theme.weight * 0.4"
                [class.text-echoes-text]="theme.weight > 0.5"
                [class.text-echoes-text-secondary]="theme.weight <= 0.5"
              >
                {{ theme.name }}
              </span>
            }
          </div>
        </div>
      }

      <!-- Emotional state -->
      @if (response.queryAnalysis.emotionalState.length > 0) {
        <div>
          <p class="font-ui text-xs text-echoes-text-tertiary uppercase tracking-wider mb-3">
            Detected emotions
          </p>
          <div class="flex gap-3">
            @for (emotion of response.queryAnalysis.emotionalState; track emotion) {
              <span class="font-story text-sm text-echoes-accent-cool italic">
                {{ emotion }}
              </span>
            }
          </div>
        </div>
      }

      <!-- Stories list -->
      <div>
        <p class="font-ui text-xs text-echoes-text-tertiary uppercase tracking-wider mb-3">
          All stories ({{ response.stories.length }})
        </p>
        @for (story of response.stories; track story.id) {
          <div class="p-4 mb-3 rounded bg-echoes-bg-secondary border border-echoes-border">
            <div class="flex justify-between items-start mb-2">
              <span class="font-meta text-xs text-echoes-text-secondary">
                {{ story.decisionSubcategory }}
              </span>
              <span
                class="font-meta text-xs px-2 py-0.5 rounded-full"
                [ngClass]="{
                  'bg-echoes-confidence-high/20 text-echoes-confidence-high': story.outcomeSentiment === 'positive',
                  'bg-echoes-confidence-medium/20 text-echoes-confidence-medium': story.outcomeSentiment === 'mixed',
                  'bg-echoes-confidence-low/20 text-echoes-confidence-low': story.outcomeSentiment === 'negative'
                }"
              >
                {{ story.outcomeSentiment }}
              </span>
            </div>
            @if (story.hindsightInsight) {
              <p class="font-story text-sm text-echoes-text italic">
                "{{ story.hindsightInsight }}"
              </p>
            }
            <div class="flex gap-2 mt-2 flex-wrap">
              @for (theme of story.keyThemes; track theme) {
                <span class="font-meta text-xs text-echoes-text-tertiary">
                  #{{ theme }}
                </span>
              }
            </div>
            <div class="flex gap-4 mt-2 font-meta text-xs text-echoes-text-tertiary">
              @if (story.timeElapsedMonths > 0) {
                <span>{{ formatTime(story.timeElapsedMonths) }}</span>
              }
              <span>richness: {{ story.emotionalRichness }}/10</span>
              <span>score: {{ (story.compositeScore * 100).toFixed(0) }}%</span>
              @if (story.isCounterNarrative) {
                <span class="text-echoes-accent-cool">counter-narrative</span>
              }
            </div>
          </div>
        }
      </div>
    </div>
  `,
})
export class ExplorerModeComponent implements OnInit {
  @Input() response!: QueryResponse;

  sentimentCounts = { positive: 0, mixed: 0, negative: 0, neutral: 0 };
  themes: { name: string; weight: number }[] = [];
  timeGroups: { label: string; positive: number; mixed: number; negative: number }[] = [];
  maxGroupSize = 1;

  ngOnInit(): void {
    this.computeSentimentCounts();
    this.computeThemes();
    this.computeTimeGroups();
  }

  private computeSentimentCounts(): void {
    for (const s of this.response.stories) {
      const key = s.outcomeSentiment as keyof typeof this.sentimentCounts;
      if (key in this.sentimentCounts) {
        this.sentimentCounts[key]++;
      }
    }
  }

  private computeThemes(): void {
    const counts = new Map<string, number>();
    for (const s of this.response.stories) {
      for (const t of s.keyThemes) {
        counts.set(t, (counts.get(t) || 0) + 1);
      }
    }
    const max = Math.max(...counts.values(), 1);
    this.themes = Array.from(counts.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 15)
      .map(([name, count]) => ({ name, weight: count / max }));
  }

  private computeTimeGroups(): void {
    const groups: Record<string, { positive: number; mixed: number; negative: number }> = {
      '<1y': { positive: 0, mixed: 0, negative: 0 },
      '1-3y': { positive: 0, mixed: 0, negative: 0 },
      '3-5y': { positive: 0, mixed: 0, negative: 0 },
      '5y+': { positive: 0, mixed: 0, negative: 0 },
    };

    for (const s of this.response.stories) {
      if (s.timeElapsedMonths <= 0) continue;
      let bucket: string;
      if (s.timeElapsedMonths < 12) bucket = '<1y';
      else if (s.timeElapsedMonths < 36) bucket = '1-3y';
      else if (s.timeElapsedMonths < 60) bucket = '3-5y';
      else bucket = '5y+';

      const sent = s.outcomeSentiment === 'positive' ? 'positive'
        : s.outcomeSentiment === 'negative' ? 'negative' : 'mixed';
      groups[bucket][sent]++;
    }

    this.timeGroups = Object.entries(groups)
      .filter(([, g]) => g.positive + g.mixed + g.negative > 0)
      .map(([label, g]) => ({ label, ...g }));

    this.maxGroupSize = Math.max(
      ...this.timeGroups.map((g) => g.positive + g.mixed + g.negative),
      1
    );
  }

  formatTime(months: number): string {
    if (months < 12) return `${months}mo`;
    const years = Math.floor(months / 12);
    return `${years}y`;
  }
}
