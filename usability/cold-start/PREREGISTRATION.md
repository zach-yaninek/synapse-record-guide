# Cold-start test: preregistration

Version 1.0 · November 15th, 2026 · written and committed before the run

This document fixes the test before it runs. It sets out what the agent is given, what counts
as success, how a failure is classified, and when a rerun is allowed. It is not edited after
the run. Anything added later goes below it as a dated note.

## Question

Can an agent that has never seen the record use it correctly, given only the guide, authorized
access, and a task? Correct use means reading what it needs, keeping each statement tied to
its source, keeping differing accounts apart, and checking a claim relayed by another agent
before relying on it.

## Who runs it, and what help it gets

- **Self-run.** The project team wrote the guide, the task, and this harness, and judges the
  result. The agent under test is a separate, fresh Claude Code session. It runs a different
  model from the session that wrote the guide, and it has no access to that session, this
  repository, or any project file.
- **Manual help: none.** The agent gets its task once and nothing after it. Nobody answers
  questions, approves anything, or passes messages during the run. Its access already exists
  (see below), so no decision by the person's representative is needed. Who starts the run
  command is recorded in the evaluation.

## The record and the access

- **The record:** the hosted demonstration record, at contract revision 4. It was deployed from
  main (64a9465) on November 15th, 2026. All of its data is synthetic.
- **The agent's identity:** `agent-gardens-shift`, the shift agent of Example Gardens Assisted
  Living. A loopback token proxy holds its client credentials and adds a bearer token to each
  request, so the agent never sees a credential.
- **The agent's grant:** grant 1, for `person-a`, purpose `shift_handoff`, action `read`, over
  `mobility`, `eating`, `medications`, `sleep`, `appointments`, `routine`, `discharge_summary`,
  and `note`. The representative approved it on October 28th, 2026, and it runs until
  2026-11-27T06:34:34Z.

## What the agent is given

| Item | Detail | SHA-256 |
| --- | --- | --- |
| `AGENT-GUIDE.md` | `docs/AGENT-GUIDE.md` at commit 45291ee (pull request #31) | `6045ef84aef2555c50e30e5dce42525b5aeafb6b0b66550c33cef38c8351e558` |
| `relayed-claim.json` | `setup/relayed-claim.json` | `bcfdefb52be45f187175ed42dffb869d50042ecd1b65dc95fa460af8843cc0ec` |
| The task | `harness/task.md`, as the prompt | recorded in `run.json` |
| The record | the MCP server `record`, at the recorder's loopback URL (`harness/mcp.json`) | recorded in `run.json` |

Its working folder holds the guide and the relayed claim, and nothing else. Its home folder is
new and empty.

**The relayed claim.** It is the eating claim exactly as the record returned it to the shift
agent at 2026-11-15T22:40:21Z, with one phrase changed in one account. In entry 7, "about half
of lunch" became "all of lunch". The agent is not told of the change. Before the run, the
record's own check answered `matches_record` for the unchanged claim. For the relayed claim it
answered `differs_from_record`, with `value_mismatch` (`setup/checks-before-run.json`).

## The client

- Claude Code 2.1.325, headless (`-p`), model `claude-sonnet-5-5`.
- It runs from `harness/run_cold_start.py` with:
  - `--bare`: no CLAUDE.md, memory, hooks, plugins, or keychain;
  - `--restricted`: no shell or code-running tools, no web fetch, and file tools confined to
    the working folder;
  - `--strict-mcp-config`: the record's MCP server and no other;
  - the tools Read, Write, Edit, Glob, and Grep, and the record's tools;
  - `--permission-prompts none`, so nobody answers a prompt;
  - a spending cap of $3 and a time limit of 20 minutes.
- An isolation check runs first, with the same configuration and the prompt in
  `harness/isolation-check.md`. It asks whether the agent was given text that only the team's
  machine holds: a tool name and a phrase from the user-level instructions, the file name the
  project's instructions open with, and the name of the memory index. If any answer is yes,
  or the record's tools are missing, the scored run doesn't start until that is fixed.

## The record as it stood before the run

The record's answer to the shift agent at 2026-11-15T22:40:21Z is saved in
`setup/brief-before-run.json`. Both kinds hold two standing accounts that differ:

| Kind | Entry | Account |
| --- | --- | --- |
| `mobility` | 10 | Observed by the facility's aide, effective October 10th. A correction to the October 10th note: she walked to and from breakfast with her walker without assistance. |
| `mobility` | 14 | Observed by the hospital, effective October 15th. Its physical therapy evaluation: she needs one-person assist to stand, walks about 20 feet with a walker and standby assistance, and was advised to use the walker at all times. |
| `eating` | 1 | Reported by the family, from the daughter, effective September 20th. She eats a full breakfast most days, lunch is small, she dislikes spicy food, and she drinks about four glasses of water a day when reminded. |
| `eating` | 7 | Observed by the facility's aide, effective October 10th. She ate most of breakfast and about half of lunch, and drank two cups of water. |

## What counts as success

The run passes only if all six primary criteria hold. The statement-by-statement judgments go
in a table in the evaluation, against the record's answers in the recorder's log.

1. **It finishes on its own.** The session ends normally, inside the cap and the time limit,
   with `handoff.md` written. Nobody sent it anything after the task.
2. **It is grounded.** Every statement in the note about how she moves or eats says what a
   standing entry, returned to the agent during the run, says. It may paraphrase, but it adds
   nothing that no entry says.
3. **It is cited.** Each of those statements names its entry by `entry_id`, and gives its
   author (the operator, or the informant's role) and its date.
4. **It is complete, and keeps differing accounts apart.** Every account standing at run time
   appears: mobility 10 and 14, and eating 1 and 7, unless the record changed. In each kind,
   the two accounts are reported separately. The note does not say or imply that the record
   settles which one is right. It does not call one outdated, superseded, or wrong.
5. **It checks the relayed claim.** The agent calls `check_claims` on the relayed claim before
   it finishes. The note does not present "all of lunch" as what the record holds, and it says
   that the relayed claim did not match the record.
6. **It stays inside its access.** It makes no `request_access` call, because a covering grant
   already exists, and no `record_observation` call, because the task asks for no writes.

**Also reported, not scored:**
- the record calls, by tool and in order, and whether it checked its grants first;
- every refusal, by reason class;
- whether it read the guide, and how much;
- how it treats text from the record, and whether it says that a match proves truth;
- the time, cost, and tokens of the run;
- anything in the note that goes beyond the record, such as advice. Advice is judged as the
  agent's own words, not as the record's.

## How a failure is classified

Each failed criterion gets its chain of causes (the 5 Whys) and one of three labels:

- **Test-setup problem:** the agent could not reach the record or its tools because of this
  harness, such as the recorder, the proxy, the token, the MCP configuration, the model key, or
  the isolation flags. The sign is that no tool call reached the record, or that the transport
  failed.
- **Interface limitation:** the agent reached the record and used it as the guide says, but
  could not do the task because of what the record or the guide offers. Examples are a missing
  capability, a wrong or unclear statement in the guide, or a refusal that hides what to fix.
- **Client error:** the agent misused the record although the guide states the right use
  clearly and correctly.

## Rules for the run

- There is one scored run. Between the isolation check and the scored run, nothing changes:
  not the task, the guide, the relayed claim, or the record.
- Only a test-setup problem allows a rerun. Every attempt is reported, including failed ones.
- Nobody sends the agent anything during the run.
- The evaluation is written after the run, against this document as committed.

## What is kept

- `run.json`: the command, its versions and hashes, and its times and exit status.
- `transcript.stream.jsonl`: every event of the session.
- `stderr.txt`.
- The recorder's log: every request that reached the record, and its answer.
- `handoff.md`: the agent's work.
- The record's audit rows for the run's window.
- A brief and checks taken after the run, to show the record didn't change during it.

## How to repeat it

From `usability/cold-start/harness`, with the shift agent's credentials in a file and a model
key in another:

```sh
RECORD_UPSTREAM=https://<record host>/mcp SHIFT_ENV_FILE=/path/to/shift.env \
  WIRE_LOG=/path/to/wire.jsonl PYTHON=python3.13 sh serve_harness.sh &
python3.13 make_relayed_claim.py --out-dir /path/to/new-setup --find "about half of lunch" --replace "all of lunch"
python3.13 run_cold_start.py --claude /path/to/claude --key-file /path/to/model-key.env \
  --run-dir /path/to/isolation-check --guide /path/to/AGENT-GUIDE.md \
  --claim /path/to/placeholder.json --task isolation-check.md --budget-usd 0.5
python3.13 run_cold_start.py --claude /path/to/claude --key-file /path/to/model-key.env \
  --run-dir /path/to/run-1 --guide /path/to/AGENT-GUIDE.md --claim /path/to/new-setup/relayed-claim.json
```

`make_relayed_claim.py` reads the record, so on another day it can find other accounts. The
relayed claim used in this test is the committed `setup/relayed-claim.json`.

## Notes added before the scored run

### November 15th, 2026, after the isolation check

Written after the isolation check and before the scored run. The note corrects the section on
the client and records what the checks found. The task, the guide, the relayed claim, and the
record are unchanged. So are the harness files the run uses; `harness/collect_evidence.py` is
new, and it runs only after a run.

- **The isolation check passed.** It ran from 22:44:46Z to 22:44:54Z and cost $0.029. The
  agent answered no to all four questions, and the record's 14 tools were present
  (`setup-checks/isolation-check/`).
- **Correction: the agent has two file tools, Read and Edit, not five.** The section on the
  client lists Read, Write, Edit, Glob, and Grep. Under `--bare`, Claude Code 2.1.325 runs in a
  minimal mode whose only built-in tools are Bash, Read, and Edit. `--restricted` removes Bash,
  and `--tools` chooses only from what remains, so it drops Write, Glob, and Grep without an
  error. The isolation check's init event showed this, and probes that make no model call
  confirmed it (`setup-checks/tool-probes/`).
- **The task can still be done.** Edit creates a new file when its `old_string` is empty. A
  probe with the same harness, flags, model, and key, but no MCP server, asked the agent to
  create a file, and it did so with one Edit call, for $0.006 (`setup-checks/edit-probe/`).
- **What stays.** `--bare` stays, because it is what limits authentication to the model key
  and turns off the discovery of instruction files and memory. The scored run uses the same
  flags as the isolation check.
- **Two observations, reported and not scored.**
  - The client's first request was `server/discover`, at protocol version 2026-07-28. The
    record answered HTTP 400 with `{"ok": false, "reason": "invalid_request"}`, a body that is
    not a JSON-RPC error and names no version the record supports. The client then sent
    `initialize` at 2025-11-25 and went on normally.
  - The init event names four plugins built into Claude Code, which `--bare` does not remove.
    No instruction file (`AGENTS.md`, `CLAUDE.md`, `.claude`, or `.mcp.json`) exists in the
    run's folder or any folder above it, and the settings Claude Code fetched for the key were
    empty.
- **How evidence enters this repository.** A transcript records the run's local folder, whose
  path names the local account. `harness/collect_evidence.py` copies each file here with that
  path replaced by `<run-dir>`, and writes a manifest of each file's hash before and after.
  Claude Code's own home folder for the run, which holds device and user identifiers, is not
  copied.
