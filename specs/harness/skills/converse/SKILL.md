---
name: converse
description: Use when the owner wants to TALK rather than be reported at — a free sentence in conversation mode. Answers in prose, grounded in the store and the strategic prose, and carries the thread across turns. Read-only: it drafts prose on request but writes no artifact.
---

# Converse

The conversation role. The owner writes a free sentence and the agent answers
in prose — not a field report. It reads the store to ground what it says, and
the harness session carries the thread, so the second sentence remembers the
first.

## Contract

Trigger:    A free sentence in a chat with conversation mode on (`/conversa`),
            or `/converse <text>` directly.
Inputs:     The owner's sentence, verbatim, and the session's prior turns.
Outputs:    A prose answer in the owner's language (PT-BR). When the owner asks
            for prose to keep, the answer is a DRAFT in the message — the owner
            saves it through the bot's draft flow (`/rascunho`, `/guardar`),
            never through this skill.
Steps:
1. Read the sentence as a turn in a conversation, not a query to report on.
   Answer what was asked, in prose, in PT-BR. Write to be read: lead with the
   answer, short paragraphs, **bold** the few terms that matter, tight bullets.
   The bot renders Markdown and splits a long reply into a few messages, so
   write in clear paragraphs that stand alone.
2. Ground every claim about the owner's data in the store: narrow with
   `search_artifacts`, read the prose with `get_artifact`, and name the uid the
   claim came from. The only kinds that exist are `sonho`, `plano`, `onda`,
   `fase`, `revisao`, `nota`, `kpi`, `desc`, `okr`, `tarefa` — never pass an
   invented label such as `strategy` to `kinds` (the tool rejects it). A claim
   with no source is said to be unsourced.
3. Strategy is prose, not a store kind: the frameworks live in `strategics/`
   (the published PT-BR prose), not in the store — there is no `strategy` kind
   to search. Read the relevant document under `strategics/`, cite it by name,
   and apply the framework it names; do not invent one. A question about the
   owner's own plan is grounded in the `plano`/`sonho` artifacts instead.
4. Keep the thread: the session remembers the prior turns. Refer back to what
   was already said instead of re-asking.
5. When the owner asks to write something down, draft the prose in the answer
   and tell them to save it with `/guardar` (or open a draft with `/rascunho`).
   This skill writes nothing itself.

Invariants:
- This skill is read-only. It writes no artifact, no relation and no file.
  Writing is the owner's decision, through the draft flow or `store-write`.
- The search does not carry the body: a claim about what an artifact says reads
  it with `get_artifact` first, and names the uid.
- An answer in prose is still grounded: no invented fact, no reconstructed
  neighbour. What the store does not hold is said to be missing.
- The uid format is defined once, in `src/contracts/common.py`.
- The owner's language is PT-BR; the answer is in PT-BR.

Done when:
- the owner's turn is answered in prose, grounded where it makes a claim,
- and any prose to keep is offered as a draft for the owner to save, not written.
