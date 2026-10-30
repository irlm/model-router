# Prefix test: what every headless session pays before any work (Haiku 5.5, low effort, 2026-10-29)

Trivial prompts, measured with `claude -p --output-format json`. `write` = cache_creation_input_tokens (billed at 2x input, 1-hour TTL), `read` = cache_read_input_tokens. `turn-1` columns come from `usage.iterations[0]`; the remainder belongs to the later API calls of the same session.

| Run | turns | total write | total read | turn-1 write | turn-1 read | cost $ |
|---|---|---|---|---|---|---|
| gitrepo-1 | 1 | 29640 | 12944 | 29640 | 12944 | 0.0061 |
| gitrepo-2 | 1 | 0 | 42584 | 0 | 42584 | 0.0004 |
| kernel-1 | 1 | 26856 | 15529 | 26856 | 15529 | 0.0055 |
| kernel-2 | 1 | 24343 | 16116 | 24343 | 16116 | 0.0050 |
| kernel-3 | 1 | 0 | 42385 | 0 | 42385 | 0.0004 |
| plain-1 | 1 | 27465 | 12944 | 27465 | 12944 | 0.0056 |
| plain-2 | 1 | 0 | 40409 | 0 | 40409 | 0.0004 |
| tool-allowedlist-1 | 2 | 27046 | 55999 | 2169 | 40438 | 0.0061 |
| tool-allowedlist-2 | 2 | 0 | 83045 | 0 | 42607 | 0.0009 |
| tool-default-1 | 2 | 29663 | 50258 | 2169 | 38876 | 0.0065 |
| tool-default-2 | 2 | 0 | 79921 | 0 | 41045 | 0.0009 |

## Reading

- `baseline1/2`, `plain-1/2`, `gitrepo-1/2`, `kernel-1/3`: a one-turn session in a given directory pays about 27k tokens of cache write the first time, and the next identical session reads about 40k and writes nothing. The prefix is stable across sessions.
- `noagents1/2`: the same call with a config dir that has no `agents/` folder writes about 10.7k instead of 27.5k. The 184 agent files are about 17k tokens of every session on every model.
- `tool-allowedlist-1`, `tool-default-1`: a two-turn session (one tool call, then the answer) writes about 27k in total even when turn 1 read the whole 40k prefix and wrote only the prompt (2.2k). The second API call of the session has a different prefix from the first beyond about 15.6k tokens, so it rewrites about 25k. Repeating the identical conversation (`-2` runs) reads everything and writes nothing, so both prefixes cache; a new conversation pays the second write once.
- Every cell-1 receipt shows this pattern: turn 1 reads about 42k and writes the prompt; the session total adds about 26k of write and 16k of read from the second call.

## Consequence for routing

Per new multi-turn session, before any task work: about 27k tokens written and 68k read. At list prices that is about $0.0055 on Haiku 5.5, $0.11 on Sonnet 5.5, $0.22 on Opus 5.5 and $0.55 on Fable 5.1. For tasks of a few hundred tokens this overhead is over 90% of the bill, so the number of sessions opened on an expensive model matters more than the model price of the task itself. Trimming the prefix (unused agent files) is a saving on every model and comes before model choice.
