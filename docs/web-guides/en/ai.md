---
title: 1xAIoffice: ask AI and rewrite text
description: Ask AI about the open document or have it rewrite a paragraph in 1xAIoffice. Asking never edits the document; rewriting always shows a preview first.
headline: Ask AI and rewrite text in 1xAIoffice
lead: Click Ask AI to ask about the selection or the whole document, or Rewrite to have AI redo a paragraph. Asking only reads; Rewrite shows a preview before it changes anything.
order: 1
---

Ask AI sends your selection (or the whole document when nothing is selected) to your own AI account and shows the answer without touching the document. Rewrite (1xDoc only) shows the new text first, replaces it only when you agree, and one Cmd+Z undoes it.

## Where to find it

- **AI tab on the ribbon:** Ask AI, Rewrite.
- **AI sidebar** on the right edge of the window: the same buttons, plus a line showing which AI account is in use.
- **Right-click** on text (1xDoc) or a cell (1xSheet): Ask AI about This Document…
- **Vietnamese menu** in the menu bar: every AI command.

If no AI account is set up yet, the app offers to add one and opens [AI Accounts](/office/en/tai-khoan-ai).

## Ask AI {#ask}

1. **Select what you want to ask about.** With no selection the app uses the whole document. In 1xSheet it sends the used area of every sheet.
2. **Click Ask AI and type your question.** For example "Summarise this in five points" or "Which column has unusual figures?".
3. **Read the answer.** The footer names the account and model, what was sent, how many characters, and whether it was trimmed.

Each question sends at most about 12,000 characters, cut at a paragraph boundary. For longer documents, select the part you need.

## Rewrite {#rewrite}

1. **Put the cursor in the paragraph** or select text inside it. Rewrite works on the whole paragraph that holds your selection.
2. **Click Rewrite and say how to change it.** Leave it empty and AI makes it clearer while keeping the meaning and terms.
3. **Check the preview and decide.** If you agree, the paragraph is replaced in one step and one undo brings it back.

If you edit that paragraph while AI is still working, the app does not apply the result, so your own typing is never overwritten.

## Where your text goes {#privacy}

Text goes straight from your Mac to the AI provider you chose, on your own account. API keys stay in the macOS Keychain, never in a settings file. With Ollama or LM Studio nothing leaves your computer. 1xAIoffice does not sell AI plans: any fees are charged by the provider to your account.

## What it does not do {#limits}

- Ask AI never edits the document. Use Rewrite for that.
- Rewrite is not available in 1xSheet or 1xSlide yet.
- AI answers can be wrong; check them before using them in official documents.
