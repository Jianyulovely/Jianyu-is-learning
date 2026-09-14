---
name: study-note-summary
description: "Create dated Markdown study notes and directly return a concise learning summary from code exercises or learning notebooks."
---

# Study Note Summary

Use this skill when the user asks to summarize a day's programming practice or learning materials. It supports two distinct input modes: multiple code-practice scripts, and a learning notebook such as `.ipynb`. The summary is returned directly to the user and is not written into the Markdown note unless explicitly requested.

## Input modes

### Mode A: multiple code-practice scripts

When the input is a group of source files such as `.py` scripts, follow the full note-generation workflow below. Create a substantial dated Markdown learning note covering all requested files, using the repository's existing note style, and return a roughly 200-character Chinese summary separately.

### Mode B: a learning notebook (`.ipynb`)

When the input is a notebook that already records the day's learning content, such as `llm_study/week3/带kv cache的Transformer.ipynb`, do not expand it into a file-by-file programming note. Read the notebook's Markdown cells first, then use code cells and meaningful outputs as supporting context. Directly produce only a concise Chinese learning summary of approximately 200 Chinese characters, unless the user explicitly asks for a separate Markdown note. Focus on what was learned, the key mechanism or insight, and the practical takeaway; do not merely list cell contents or repeat the notebook filename.

## Workflow

1. Identify the files the user says they studied. Resolve paths carefully; if a stated path does not exist, search nearby with `rg --files` and use the closest matching actual file, mentioning the correction when relevant.
2. Choose the input mode before writing: a collection of code scripts uses Mode A; a notebook used as the day's learning record uses Mode B.
3. For Mode A, read all source files and at least one existing study-note Markdown file supplied by the user or found in the same repository. Treat the existing note as a style reference, not as content to copy.
4. Infer the current date from the environment unless the user provides another date. Use the repository's established date format when it is clear; otherwise use `YYYY/M/D`.
5. For Mode A, write a new or updated Markdown note in the user's intended learning directory. Preserve unrelated working-tree changes and avoid editing source files unless explicitly requested.
6. For Mode A, organize the note in a style similar to the reference: date, title, learning-content overview, topic/file table, one section per exercise, key ideas, complexity where meaningful, Python/API knowledge, and common pitfalls. Keep explanations grounded in the actual code, including notable implementation mistakes or corrections when they teach something useful.
7. For either mode, add a concise Chinese learning summary of approximately 200 Chinese characters when requested, and return it directly in the final response. Do not put the summary into the generated Markdown note unless explicitly requested. For Mode B, this summary is the only default output.
8. For Mode A, verify the output path, date, section coverage, Markdown readability, and `git status`. Do not claim completion until the file exists and includes every requested topic.

## Content guidance

- Prefer clear Chinese prose with short code snippets only where they explain a reusable pattern. For a full Mode A note intended for PDF export, expand principles, execution flow, comparisons, practical examples, review checklists, and grounded pitfalls so the document is substantial enough for roughly five A4 pages without repetitive filler.
- For algorithms, explain problem modeling, state/transition or iteration flow, and time/space complexity when it can be derived.
- For ACM exercises, explicitly note input shape, EOF handling, output formatting, and edge cases.
- Distinguish the behavior implemented by the source from textbook terminology. For example, call row-sum normalization “题目定义的归一化” if the code does not implement exponential Softmax.
- Record real code-level pitfalls such as empty clusters, noise reassignment, duplicate-distance indexing, invalid matrix shapes, unreachable DP states, and EOF handling when present.
- Do not invent problem statements, sample results, or requirements that are not supported by the files.

## Output convention

Unless the user specifies another location or filename, place the note beside the studied files and name it with the month and day followed by `笔记.md`: `M.D笔记.md`. For example, a note created on September 6 should be named `9.6笔记.md`; do not pad single-digit months or days with zeroes. If a summary is requested separately, return it directly and, when the user asks to update the note, add it to the note as well.
