---
title: 1xAIoffice: run AI skills for office work
description: Skills are ready-made instructions for AI: Decree 30 documents, legal summaries, payroll tables. How to run the bundled skills and add your own.
headline: Run AI skills in 1xAIoffice
lead: A skill is a ready-made way to do one kind of job. Click Run Skill, pick a skill and describe the task; AI follows that method on your document.
order: 2
---

A skill is a ready-made set of instructions for one kind of job, such as drafting a Decree 30 document or building a payroll table. Click Run Skill, choose the skill that fits, and describe the task; AI reads the open document and answers the way the skill prescribes.

## Bundled skills

| Skill | Works in |
|---|---|
| soan-van-ban-nd30: draft an administrative document (Decree 30) | 1xDoc |
| viet-lai-trang-trong: rewrite in a formal tone | 1xDoc |
| kiem-chinh-ta-tieng-viet: Vietnamese spell check | 1xDoc |
| tom-tat-van-ban-phap-luat: summarise a legal document | 1xDoc |
| dich-viet-anh-hanh-chinh: Vietnamese–English administrative translation | 1xDoc |
| tao-slide-tu-van-ban: slide outline from a document | 1xDoc, 1xSlide |
| bang-luong-thue-tncn: payroll and personal income tax | 1xSheet |
| lap-bang-du-toan: cost estimate table | 1xSheet |

The list you see after clicking Run Skill only shows skills that work in the open app.

## Steps {#steps}

1. **Click Run Skill** on the AI tab, in the AI sidebar or in the right-click menu.
2. **Type the skill's name** from the list.
3. **Describe the task.** The prompt shows the skill's description so you know what it can do.
4. **Read the result.** The answer ends with the name and version of the skill used.

Skills only read the document. To put the result in your text, copy it in or use [Rewrite](/office/en/ai).

## Add your own skills {#your-skills}

Each skill is a folder with a `SKILL.md` file (its header gives `name`, `description` and `apps`: doc, sheet, slide), in the Agent Skills format. Put the folder in:

`~/.config/1xaioffice/skills/`

The next time you click Run Skill it appears in the list. This folder lives outside the app profile, so resetting 1xAIoffice does not remove it. Your own skills are also offered to outside assistants when you turn on the [MCP server](/office/en/mcp).

## What it does not do {#limits}

- Skills never run scripts or programs that come with them; only the instructions are given to AI.
- The bundled 1xAIoffice skills are not shared with outside assistants over MCP.
- Skills need an [AI account](/office/en/tai-khoan-ai).
