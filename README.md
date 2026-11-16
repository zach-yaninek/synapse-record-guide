# The Synapse record: agent guide and usability evidence

The Synapse record is a service that holds care records, each kept for one person, for other
agents to call over MCP. This repository holds two things: the record's guide for calling
agents, and the evidence from a three-part usability test of that guide. The service's code is
private and is not here.

Every person, household, organization, and value in the record and in this evidence is
invented.

## Start here

[`docs/AGENT-GUIDE.md`](docs/AGENT-GUIDE.md) is the interface guide: what the record offers,
how to connect, what each tool takes and returns, what is refused and why, and a worked
example. It is version 1.2, for contract revision 5.

## The usability test

| Part | What | Where | Result |
| --- | --- | --- | --- |
| 1 | Document the interface for a calling agent | [`docs/AGENT-GUIDE.md`](docs/AGENT-GUIDE.md) | The guide, version 1.2 |
| 2 | A preregistered cold-start test: a fresh agent gets only the guide, a grant, and a task | [`usability/cold-start/`](usability/cold-start/) | Passed all six preregistered criteria in its one scored run |
| 3 | Test one limitation, improve it, and rerun | [`usability/bad-argument/`](usability/bad-argument/) | Ten malformed calls all drew the same bare refusal before the change, and ten distinct refusals after it, on the hosted record as well as locally |

### Part 2: the cold-start test

The agent under test was a fresh Claude Code session on `claude-sonnet-5-5`. Its only tools
were `Read`, `Edit`, and the record's own tools. It got the guide, a grant to read the record
for a shift handoff, a task, and a claim relayed by another agent in which one value had been
altered. It had to write a handoff note from the record.

- **Result.** It passed all six criteria. It finished on its own. Every statement it made about
  how the person moves or eats rests on a record entry, and each account names its entry, its
  author, and its date. It kept two pairs of differing accounts apart, checked the relayed
  claim and caught the altered value, and stayed inside its access. The evaluation flags one
  line of the note without changing the result. The run took 7 turns, 27 seconds, and $0.098
  of model spend.
- **Who ran it.** Self-run. The team that wrote the guide, the task, the harness, and the
  criteria also ran the test and judged it. The Claude Code session that wrote the guide and
  the harness (`claude-opus-5-5`) started the run.
- **Manual help.** None. Nobody answered a question, approved a step, or passed a message
  during the run, and no permission prompt was raised.
- **Limits.** One run, one task, one model, and a self-run test. The agent met no refusal from
  a tool, wrote nothing to the record, and met no injected text. See "What this run shows, and what it
  does not" in [`EVALUATION.md`](usability/cold-start/EVALUATION.md).

Read [`PREREGISTRATION.md`](usability/cold-start/PREREGISTRATION.md) first. It was written and
pushed before the run, and it holds the criteria and the commands to repeat the test. Then read
[`EVALUATION.md`](usability/cold-start/EVALUATION.md), and the agent's own note,
[`run-1/handoff.md`](usability/cold-start/run-1/handoff.md).

### Part 3: name the argument a refusal is about

Before the change, a call whose arguments broke the published schema got only
`{"ok": false, "reason": "invalid_request"}`, so a calling agent had to find its own mistake by
comparing each argument with the schema. Contract revision 5 adds two fields to a
refusal for arguments that fail the tool's published input schema: `argument`, where they
failed, and `problem`, which schema keyword failed. Neither ever holds a value the caller sent,
and every other refusal stays bare.

A fixed probe of ten malformed calls and one well-formed control ran before and after the
change, locally and against the hosted record. After the change, nine of the ten name the
argument and the rule. The tenth, a date that does not exist (February 30th), breaks no rule
the schema publishes, so it stays bare, by design. See
[`usability/bad-argument/EVALUATION.md`](usability/bad-argument/EVALUATION.md).

## What changed in this export

This repository was exported, with fresh history, from the private repository at commit
`6ed3e09` on November 16th, 2026 (UTC). Every file is byte-identical to that commit, with two
exceptions.

1. **Three identifiers are replaced with placeholders.** The deployment's authorization server
   assigned them to two organizations and one test user. They are identifiers, not
   credentials. Five files under `usability/cold-start/` held them, 26 times in all:
   - `<workos-organization-id>`: the organization of the facility's shift agent, the caller in
     parts 2 and 3;
   - `<workos-organization-id-discharge>`: the organization of the hospital's discharge agent,
     which wrote entry 14;
   - `<workos-user-id>`: the test user who approved the shift agent's grant.

   [`EXPORT-MANIFEST.json`](EXPORT-MANIFEST.json) gives each changed file's SHA-256 in the
   private repository and here, and the count of each replacement. For the four changed files
   in `run-1/`, the private SHA-256 equals the `sha256_copy` that `run-1/MANIFEST.json`
   recorded when the evidence was collected. Part 3's evidence was redacted when it was collected, with the same
   placeholders for the same identifiers, and its `MANIFEST.json` files record that.
2. **One file is added.**
   [`usability/cold-start/guide-as-read/AGENT-GUIDE.md`](usability/cold-start/guide-as-read/AGENT-GUIDE.md)
   is the guide as the agent read it in part 2, from private commit `45291ee`. Its SHA-256 is
   the one in `run-1/run.json`. The guide in `docs/` has changed since, so check the run against
   this copy.

Earlier redactions, made when the evidence was collected, are recorded in each evidence
folder's own `MANIFEST.json`. For example, the local run folder's path reads `<run-dir>`.

## What you can repeat from here

- **Check the evidence as it stands.** The transcripts, the wire logs, the probe's answers, and
  the hashes need nothing but this repository.
- **Probe a record.** [`probe_refusals.py`](usability/bad-argument/probe_refusals.py) uses the
  Python standard library only and handles no credentials. It sends its calls to a URL that
  adds an admitted caller's token, such as the harness below. For the demonstration
  deployment, that needs credentials this repository does not hold.
- **Rerun the cold start.** [`run_cold_start.py`](usability/cold-start/harness/run_cold_start.py)
  needs the Claude Code CLI, a model key, and the harness that `serve_harness.sh` starts: a
  recorder and a token proxy. The token proxy (`agents.token_proxy`) is in the private
  repository.
- **Rerun part 3 locally.** [`run_local_probe.py`](usability/bad-argument/run_local_probe.py)
  starts the record on loopback, so it needs the private service code
  (`demo.run_worked_example`).

Paths and modules under `record_service/`, `tests/`, `clients/`, `scenarios/`, `agents/`, and
`demo/` refer to the private repository. Part 3's regression tests are there too.

## When the preregistration was fixed

The preregistration was pushed to a branch of the private repository 19 minutes before the
run's first call, and its dated note 47 seconds before. GitHub's activity log records those
push times. This repository's history is fresh, so
[`provenance/github-activity.json`](usability/cold-start/provenance/github-activity.json) keeps
a copy of the log's entries with the query that returns them. Only someone with access to the
private repository can check that copy against GitHub.

## Context

Prepared for the agent-usability assignment of MIT AI Studio (HW9).
