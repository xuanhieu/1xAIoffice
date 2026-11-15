---
title: 1xAIoffice: convert TCVN3 and VNI text to Unicode
description: Convert TCVN3 (.VnTime), VNI or VIQR text to Unicode; normalise Unicode; remove accents; switch between old (hòa) and new (hoà) tone placement.
headline: Convert and normalise Vietnamese text
lead: Select text (or nothing, for the whole document) and click the command that matches the source: TCVN3, VNI or VIQR. Each run is a single undo step.
order: 8
---

Old documents typed in .VnTime fonts (TCVN3), VNI or VIQR (a', e^) open with broken accents. Select the part to fix, or nothing for the whole document, and click the matching conversion; 1xAIoffice turns it into Unicode and tells you how many passages changed.

## Commands

- **TCVN3 to Unicode:** text in .Vn… fonts to Unicode. With no selection, only text set in .Vn… fonts is converted and its font is set to Times New Roman.
- **VNI to Unicode, VIQR to Unicode:** VNI or VIQR text to Unicode.
- **Normalize Unicode:** one consistent Unicode form (NFC), extra spaces collapsed, spacing around punctuation fixed. Run it before searching, sorting or comparing.
- **Remove Diacritics:** "Tiếng Việt" becomes "Tieng Viet", for file names, codes and email addresses.
- **Old Tone Style / New Tone Style:** switch between hòa, khỏe, thủy and hoà, khoẻ, thuỷ. Only oa, oe and uy syllables change.

## Where to find them

The AI tab on the ribbon (small buttons) and the Vietnamese menu in the menu bar. The two tone-style commands are only in the Vietnamese menu.

## Steps {#steps}

1. **Select what to change.** In 1xDoc, no selection means the whole document. In 1xSheet, text cells in the selection are converted.
2. **Click the command for the source encoding.**
3. **Check the result.** If it is wrong, one undo restores it.

## What it does not do {#limits}

- VNI and VIQR: a mark is converted only when it comes right after its vowel; marks typed at the end of the word are not recognised.
- Normalize Unicode does not change tone placement; use Old Tone Style or New Tone Style.
