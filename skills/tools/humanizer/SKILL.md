---
name: humanizer
description: Rewrite AI-sounding text into more natural human prose while preserving meaning, voice, and technical accuracy. Use when editing drafts, blog posts, documentation, emails, notes, or generated text to remove obvious AI patterns such as inflated significance, promotional language, vague attributions, superficial -ing clauses, AI vocabulary, passive voice, rule-of-three structure, em dash overuse, and filler phrases.
---

# Humanizer

Use the bundled Python helper for deterministic AI-writing pattern detection. Use the LLM for judgement: preserving meaning, matching the author's voice, deciding which flagged items matter, and rewriting the final prose.

This skill is adapted from `blader/humanizer` and keeps the full upstream guidance in `references/upstream-humanizer-skill.md`. Read that reference only when the short workflow below is not enough or the user asks for a more aggressive humanization pass.

## Workflow

1. Put the target text in a file when it is more than a short paragraph.

2. Analyze the text:

   ```powershell
   python "<skill-dir>\scripts\humanizer-helper.py" analyze --file "<text-file>" --json
   ```

   For short inline text, use:

   ```powershell
   python "<skill-dir>\scripts\humanizer-helper.py" analyze --text "<text>" --json
   ```

3. Inspect these JSON fields:
   - `summary.ai_tell_count`: total deterministic pattern hits.
   - `summary.top_categories`: where the text feels most generated.
   - `findings`: exact snippets, rule names, and suggested edits.
   - `rhythm`: sentence length stats and repeated sentence starts.
   - `risk_flags`: stop if the helper could not read input or the text is empty.

4. Rewrite the text. Keep the meaning intact and prefer the user's natural voice over generic polish.
   - Replace inflated claims with concrete statements.
   - Remove vague attributions unless there is a named source.
   - Break formulaic list structures when they feel artificial.
   - Prefer active voice when it clarifies the actor.
   - Remove filler transitions and AI vocabulary that do not add meaning.
   - Avoid em dash overuse; use commas, periods, parentheses, or plain hyphens instead.
   - Add a little personality where appropriate, but do not invent facts.

5. Run a final check on the revised text:

   ```powershell
   python "<skill-dir>\scripts\humanizer-helper.py" analyze --file "<revised-file>" --json
   ```

   Treat remaining findings as prompts for review, not mandatory failures. Technical writing may legitimately keep some repeated terms or passive constructions.

## Voice calibration

If the user provides a writing sample, match it before applying generic advice:

- sentence length and rhythm
- level of formality
- paragraph openings
- punctuation habits
- recurring phrases
- how direct or opinionated the author tends to be

Do not over-humanize technical content. Keep precise terms, commands, code identifiers, citations, and security or infrastructure details intact.
