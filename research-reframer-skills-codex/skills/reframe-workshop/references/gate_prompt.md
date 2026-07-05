# Codex Gate Prompt Reference

Use this reference when presenting v0.7 human selection gates in Codex. Do not use chat-typed
selection ids, custom channels, `sendPrompt`, or `AskUserQuestion`.

Default display language is Simplified Chinese. Internal JSON may keep technical English field names,
but user-facing gate options must be rewritten as lightweight Chinese selection cards and saved in
`05_gate_cards.json`.

## Display Rules

1. Show only 3-4 short lines per option by default.
2. Do not add "innovation type" labels or forced category groups.
3. Keep full JSON fields available for traceability, but hide them behind details or omit them from
   the default gate card.
4. Use a two-layer display:
   - Reader layer: default card text. Use plain Simplified Chinese, short sentences, and explain the
     point before showing provenance.
   - Technical layer: raw schema fields, ids, operators, audit scores, source quotes, and dense paper
     terminology. Put this behind collapsed details.
5. Technical English terms are allowed only when they are explained in plain Chinese. Do not let
   jargon carry the meaning.
6. Every selected id must also be recorded in `05_human_selection.json`.

## Gate 1: Select System Cuts

Use `02_leverage_points.json`. Candidate ids start with `LP-`.

```text
LP-### | short Chinese title

原来的默认想法:
...

问题卡在哪里:
...

选它后会生成什么:
...
```

Target length: 70-110 Chinese characters per card.

## Gate 2: Select Lateral Schemes

Use `03_lateral_reframes.json`. Candidate ids start with `LR-`.

```text
LR-### | short Chinese title

原来怎么想 -> 现在怎么想:
...

人话方案:
...

看点:
...

风险:
...
```

If the page or chat becomes too long, use the three-line version:

```text
LR-### | short Chinese title
原来怎么想 -> 现在怎么想: ...
方案: ...
风险: ...
```

Do not display raw field names such as `operator`, `old_frame`, `lateral_move`, `new_frame`,
`scheme`, `why_interesting`, `changed_assumption`, or `bad_use_to_avoid` as the default UI.

## Gate 3: Select Audited Schemes

Use `04_vertical_audits.json`. Candidate ids start with `VA-`. Show `keep`, `revise`, and
`needs_human` audits as selectable. Both-judge rejects are non-selectable context.

`needs_human` audits may only become idea cards when the Gate 3 selection includes an explicit
human resolution of `keep` or `revise`. Record that resolution in both `05_human_selection.json`
and the corresponding idea card trace.

```text
VA-### | short Chinese title | verdict

保留下来的核心:
...

最小实验:
...

最大风险:
...
```

Do not show the full audit by default. Hide or omit `causal_mechanism`, `critical_assumptions`,
full `reasons`, full `novelty_risk`, and detailed audit-score dimensions unless the user asks for
details.
