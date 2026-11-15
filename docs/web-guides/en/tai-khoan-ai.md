---
title: 1xAIoffice: add an AI account, free tiers included
description: Add an API key (Groq, Gemini, OpenRouter and more have free tiers), sign in with your ChatGPT plan, or run AI on your own Mac. Keys stay in the Keychain.
headline: Add an AI account to 1xAIoffice
lead: Open AI Accounts, pick a provider (free tiers are listed first), paste a key or sign in, then choose a model. Keys are stored in the macOS Keychain.
order: 3
---

1xAIoffice uses your own AI account and does not sell AI plans. Open AI Accounts, pick a provider (those with a free tier come first), paste an API key or sign in, then choose a model; the key is stored in the macOS Keychain.

## Pick a provider

- **Free tier, API key:** Groq, Google Gemini, OpenRouter, Mistral, Cerebras, Hugging Face, NVIDIA, SambaNova, GitHub Models (the token needs `models:read`).
- **Pay as you go, API key:** OpenAI, Anthropic, DeepSeek, xAI, Together, Fireworks, Azure OpenAI.
- **Sign in:** ChatGPT (uses the Plus/Pro plan you already pay for), Google Vertex, Azure (Entra ID), your organisation's AI gateway (SSO).
- **On your Mac, no key:** Ollama, LM Studio, vLLM. Ollama and LM Studio send nothing over the network.

Free-tier limits are set by each provider and can change; check their site. Using ChatGPT from another app counts toward your plan's limits.

## Steps {#steps}

1. **Open AI Accounts:** on the AI tab, at the bottom of the AI sidebar, or Vietnamese menu ▸ AI Accounts.
2. **Pick a provider** by its number or name in the list.
3. **Get a key or sign in.** For key providers the app offers to open the provider's key page in your browser; create a key there and paste it into the masked field. For sign-in providers the browser opens the sign-in page; choose No to get a code to enter on another device instead.
4. **Choose a model.** The app fetches the provider's model list when it can; otherwise type the name.

From now on the AI sidebar shows the account and model in use.

## Where your key is kept {#privacy}

- API keys and sign-in tokens live in the macOS Keychain under items named `1xaioffice/<provider>`.
- The settings file in the app profile only holds the Keychain item names, never the keys.
- Browser sign-in uses PKCE and returns to 127.0.0.1 on your own Mac.

To remove a key, open Keychain Access, search for `1xaioffice` and delete the item.
