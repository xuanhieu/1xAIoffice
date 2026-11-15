---
title: 1xAIoffice: open CSV files without broken text
description: Open CSV as UTF-8 and keep leading zeros, ID numbers, codes and dates as written, with no stray formulas. Detects the separator, freezes the header.
headline: Open CSV files safely
lead: Click Open CSV Safely in 1xSheet: the file is read as UTF-8 and every column stays text, so accents, leading zeros, ID numbers and dates come through intact.
order: 7
---

Open CSV Safely reads the file as UTF-8 and keeps every column as text, so Vietnamese accents are not garbled, phone numbers keep their leading zero, long ID numbers are not turned into 1.2E+11, and dates stay as written.

## Steps {#steps}

1. **Click Open CSV Safely** on the AI tab in 1xSheet, or Vietnamese menu ▸ Open CSV Safely.
2. **Choose a .csv or .txt file.**
3. **Work with it like any sheet.** The app detects the separator (comma, semicolon, tab, pipe), fits column widths and, when the first row looks like a header, makes it bold and freezes it.

Cells starting with "=" stay text and never run as formulas, so a file from an unknown source cannot inject formulas into your sheet.

## What it does not do {#limits}

- It does not convert columns to numbers or dates. To calculate with a column, change it to a number format after opening.
- Files that are not UTF-8 (for example exports in the old TCVN3 encoding) may show wrong accents; use [Vietnamese conversion](/office/en/tieng-viet) after opening.
- Closing it without edits does not ask to save. To keep a spreadsheet copy, save as .xlsx or .ods.
