---
title: 1xAIoffice: write numbers and amounts in Vietnamese words
description: Turn numbers into Vietnamese words in 1xDoc, 1xSheet and the DOCSO and DOCTIEN functions: 1,250,000 becomes "Một triệu hai trăm năm mươi nghìn đồng".
headline: Write numbers and amounts in words
lead: Select a number and click Amount in Words, or type =DOCTIEN(E5) in 1xSheet: 1,250,000 becomes "Một triệu hai trăm năm mươi nghìn đồng".
order: 9
---

Select a number and click Number in Words or Amount in Words; in spreadsheets there are also the =DOCSO() and =DOCTIEN() functions, which update when the number changes. For example =DOCTIEN(1250000) gives "Một triệu hai trăm năm mươi nghìn đồng". The words are always in Vietnamese, as invoices and contracts in Vietnam require.

## In 1xDoc

1. **Select the number.** The app understands 1.250.000, 1,250,000.5, 12 500, a trailing đ or ₫, and negative numbers.
2. **Click Amount in Words** (or Number in Words) on the AI tab or in the Vietnamese menu. The number is replaced by words.

## In 1xSheet

- **With the button:** select cells with numbers and click Amount in Words. The words go into the empty cell to the right of each number. If that cell is not empty, it is skipped and counted in the message.
- **With functions:** `=DOCSO(number; "lẻ"|"linh")` reads a number, `=DOCTIEN(amount; unit)` reads an amount, with "đồng" as the default unit.

## How it reads {#reading}

- 105 is "một trăm lẻ năm" (DOCSO lets you choose "linh").
- Decimals are read with "phẩy". Amounts are rounded to whole units, capitalised and end with "đồng".
- Up to 18 integer digits.

## What it does not do {#limits}

- DOCSO and DOCTIEN are 1xAIoffice functions. Saved as .xlsx, Excel shows the last computed words but cannot recalculate them.
- It does not write numbers in English or read foreign currencies with their own sub-units (such as dollars and cents).
