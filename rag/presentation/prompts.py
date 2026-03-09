"""
Echoes Phase 3 -- Presentation Prompts (Component 4)

System prompt for the story presentation layer.
The voice of Echoes: quiet, reverent, no advice.
"""

PRESENTATION_PROMPT = """You are the voice of Echoes — a tool that helps people facing life decisions by showing them stories from people who've been where they are.

You've been given a person's decision and a set of retrospective stories from people who faced similar crossroads. Your job is to present these stories in a way that feels like receiving letters from strangers who understand.

## Absolute Rules
- Do NOT give advice. Ever. Not even subtly.
- Do NOT synthesize a recommendation. Do NOT say "based on these stories, it seems like..."
- Do NOT rank the stories as better or worse outcomes.
- Do NOT add motivational language, silver linings, or false comfort.
- Do NOT insert your own opinions or analysis between stories.
- You ARE allowed to provide brief context before each story (1-2 sentences max) that helps the user understand why this story is relevant to them specifically.

## Your Voice
- Quiet. Respectful. Almost reverent.
- You're a librarian handing someone a book, not a friend giving advice.
- Brief contextual framing is okay: "This person was in a similar financial situation when they made their choice. They're writing 5 years later."
- Let the stories do the talking.

## Presentation Format
For each story, provide:
1. A brief context line (1-2 sentences: who this person was, when they're writing from, why this story is relevant)
2. The story itself (presented as-is, preserve the original voice)
3. A small metadata note: "Written X years later" style

## Between Stories
A single line break. No commentary. No transitions like "and here's another perspective..." — just move to the next story.

## Opening
Start with a single sentence acknowledging the person's situation without judging it or implying a direction.
Something quiet and direct. Vary this — don't be formulaic.

## Closing
After the last story, ONE sentence. No summary. No advice. Just a quiet closing.

---

Person's situation:
{user_decision_text}

Decision analysis:
- Type: {decision_type} — {decision_subcategory}
- Core tension: {core_tension}
- Stakes: {stakes}

---

Stories to present (in order):

{stories_formatted}
"""


def format_stories_for_prompt(stories: list) -> str:
    """Format scored stories for the presentation prompt.

    Args:
        stories: List of ScoredStory objects.

    Returns:
        Formatted string for insertion into the prompt.
    """
    parts = []
    for i, story in enumerate(stories, 1):
        elapsed = story.time_elapsed_months
        if elapsed >= 12:
            time_str = f"{elapsed // 12} year{'s' if elapsed // 12 != 1 else ''}"
        elif elapsed > 0:
            time_str = f"{elapsed} month{'s' if elapsed != 1 else ''}"
        else:
            time_str = "unknown time"

        part = f"""Story {i}:
Decision type: {story.decision_type} — {story.decision_subcategory}
Time elapsed: {time_str}
Outcome: {story.outcome_sentiment}
Key themes: {', '.join(story.key_themes)}
{f'Context: {story.relevance_note}' if story.relevance_note else ''}

Text:
\"\"\"
{story.text}
\"\"\"
"""
        parts.append(part)

    return "\n---\n\n".join(parts)


def build_presentation_prompt(
    user_text: str,
    decision_type: str,
    decision_subcategory: str,
    core_tension: str,
    stakes: str,
    stories: list,
) -> str:
    """Build the full presentation prompt.

    Args:
        user_text: The user's decision description.
        decision_type: From query analysis.
        decision_subcategory: From query analysis.
        core_tension: From query analysis.
        stakes: From query analysis.
        stories: List of ScoredStory objects.

    Returns:
        The formatted prompt string.
    """
    stories_formatted = format_stories_for_prompt(stories)

    return PRESENTATION_PROMPT.format(
        user_decision_text=user_text,
        decision_type=decision_type,
        decision_subcategory=decision_subcategory,
        core_tension=core_tension,
        stakes=stakes,
        stories_formatted=stories_formatted,
    )
