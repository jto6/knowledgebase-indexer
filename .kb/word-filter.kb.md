---
id: c8e016ad-cf59-45b9-acff-88cecf116d77
slug: word-filter
title: Significant Word Filter
source: ../word_filter.py
domain: technical
tags: [kbi, word-index, python, indexer]
created: 2026-06-11
updated: 2026-06-11
---

# Significant Word Filter

> `word_filter.py` implements `SignificantWordFilter`, which strips common English stop words, code tokens, and boilerplate from text to leave only meaningful technical terms for the word index.

## Core Concepts

- **`SignificantWordFilter`**: builds comprehensive stop-word sets at construction time; exposes `get_significant_words(text)` → list of retained words
- **Stop-word categories**
	- English grammar: articles, pronouns, prepositions, conjunctions, auxiliary verbs, common verbs, temporal terms, number words
	- Programming boilerplate: `def`, `class`, `import`, `return`, `if`, `for`, `while`, `True`, `False`, `None`, etc. — prevents code comments from polluting the word index
	- Generic document words: `figure`, `table`, `section`, `chapter`, `example`, `note`, `see`, etc.
- **Processing pipeline**: tokenize by whitespace → strip punctuation → lowercase → filter stop words → apply minimum length threshold
- **Consumer**: `KnowledgebaseIndexer` calls this to populate the opt-in word view (`VIEW_WORD`) — maps significant words to the files they appear in, sorted alphabetically
