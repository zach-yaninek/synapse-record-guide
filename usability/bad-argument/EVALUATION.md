# Part 3: name the argument a refusal is about

November 15th, 2026. Part 3 of the usability test: test one limitation, make one improvement, then rerun it and add regression tests.

## Result

The limitation is reproduced, the improvement works as designed on this branch, and regression tests guard it.

On the hosted record and on `main` alike, ten malformed calls, each breaking a different rule, got the same refusal: `{"ok": false, "reason": "invalid_request"}`. On this branch the same ten calls get ten different refusals. The nine that break a rule of the published input schema now name the argument and the rule. The one that breaks a rule the schema does not publish still gets a bare refusal, as the amended contract requires.

The hosted record still runs `main`, so the "after" run is local. A live rerun needs a redeploy.

November 16th, 2026: the hosted record now runs contract revision 5, and the same probe against it gets the same refusals as the local run for all ten malformed calls (The hosted rerun, below). This replaces "A live rerun needs a redeploy" above, which is kept as written.

## The limitation

The agent guide lists it under known limits: an `invalid_request` refusal doesn't say which argument failed. A caller that sends a malformed request learns only that something in it broke the tool's schema. It then has to compare every argument with `tools/list` by hand. With nested arguments, that is a long search: `check_claims` takes claims, which hold cited entries, which hold their source text.

The cold-start run in part 2 didn't hit this, because its agent sent well-formed calls. Part 2 listed it as a candidate for part 3.

## The test

`probe_refusals.py` sends a fixed set of calls as the facility's shift agent, the identity part 2 used:

- one well-formed call (`my_grants`), to show the caller's access works;
- nine calls that each break one rule of a published input schema, the kinds of mistake an agent starting cold can make:
  - a purpose that isn't published;
  - a capitalized item kind;
  - a required argument left out;
  - an array sent as a string;
  - an argument the tool doesn't take;
  - an empty array;
  - a repeated item;
  - a negative cursor;
  - a cited entry id sent as text, three levels down in `check_claims`;
- one call that passes the schema but breaks a rule the schema does not publish: a date in the published format that doesn't exist (February 30th).

Each `check_claims` case starts from the eating claim the hosted record returned in part 2 and changes one field.

The probe ran three times:

| Run | Record | Code | Started (UTC) |
|---|---|---|---|
| Before, hosted | The hosted record, through the shift agent's token proxy and part 2's recorder | `main` at 64a9465 (contract revision 4) | 2026-11-16 00:06:24 |
| Before, local | This checkout on loopback, with the synthetic household | `main` at 64a9465, unchanged | 2026-11-16 00:05:49 |
| After, local | The same | This branch | 2026-11-16 00:20:23 |

## Before and after

| Call | Tool | Rule broken | Before (hosted and local) | After |
|---|---|---|---|---|
| A well-formed call (control) | `my_grants` | none (control) | ok | ok |
| Purpose is not a published purpose | `request_brief` | `enum` | `invalid_request` | `invalid_request`, `purpose`, `enum` |
| Item kind capitalized | `request_brief` | `enum` | `invalid_request` | `invalid_request`, `item_kinds[0]`, `enum` |
| Purpose left out | `request_brief` | `required` | `invalid_request` | `invalid_request`, `purpose`, `required` |
| Item kinds sent as a string | `request_brief` | `type` | `invalid_request` | `invalid_request`, `item_kinds`, `type` |
| An argument the tool does not take | `request_brief` | `additionalProperties` | `invalid_request` | `invalid_request`, `""`, `additionalProperties` |
| No item kinds | `request_brief` | `minItems` | `invalid_request` | `invalid_request`, `item_kinds`, `minItems` |
| An item kind twice | `request_brief` | `uniqueItems` | `invalid_request` | `invalid_request`, `item_kinds`, `uniqueItems` |
| A negative cursor | `request_brief` | `minimum` | `invalid_request` | `invalid_request`, `since_cursor`, `minimum` |
| A cited entry id sent as text | `check_claims` | `type` | `invalid_request` | `invalid_request`, `claims[0].entries[1].entry_id`, `type` |
| A date in the published format that does not exist | `check_claims` | none published | `invalid_request` | `invalid_request` |

**Before.** The hosted record and local `main` gave the same answer to every malformed call. The control call's grants differ only because the two records hold different grants. Ten malformed calls produced one distinct refusal.

**After.** Ten malformed calls produce ten distinct refusals. Every refusal is still HTTP 200 with MCP's `isError` set, as before.

## Why it was so: five whys

1. **Why didn't the refusal say which argument failed?** The service returned only the reason class for every `invalid_request`.
2. **Why?** The validator knew which rule failed, but not where in the arguments it was. The handler also treated every validation failure alike and dropped the rule.
3. **Why?** The rule "a refusal returns a reason class only, never a record value" was applied to every refusal by its shape. That included refusals whose only content is the caller's own mistake.
4. **Why does that distinction matter?** A schema failure is decided by the request and the published schema alone. Naming it tells the caller nothing it couldn't work out itself, and nothing about the record. Many other checks can depend on what the record holds: whether an entry exists, whose it is, and what the caller's grant covers.
5. **Root cause:** the rule was written about the refusal's shape, not about what a refusal can reveal. The simplest fix that keeps what the rule protects is to let a refusal name a schema failure, and nothing else.

## The improvement: contract revision 5

The project owner approved this on November 15th, 2026. It amends the rule above, scoped to schema checks only.

- **What a schema refusal carries.** An `invalid_request` for arguments that fail the tool's published input schema also carries two fields:
  - `argument`: where the arguments failed, as a path in the schema's own terms, such as `item_kinds[0]` or `claims[0].entries[1].entry_id`. `""` is the arguments object itself.
  - `problem`: the JSON Schema keyword that failed. It is one of twelve: `type`, `enum`, `required`, `additionalProperties`, `minItems`, `maxItems`, `uniqueItems`, `minLength`, `maxLength`, `pattern`, `minimum`, or `maximum`.
- **Never the caller's value.** Neither field ever holds a value the caller sent. For a missing argument, the path names that argument, a name from the schema. For an argument the tool doesn't take, the path names the object holding it, never the caller's name for it.
- **One failure, in a fixed order.** The first failure is reported, in a fixed order, so the same request is always refused the same way.
- **Every other refusal stays bare.** That includes an `invalid_request` from any check the schema doesn't publish:
  - a date that doesn't exist;
  - an entry the store won't accept;
  - a withdrawal of an entry the record doesn't hold;
  - an upload body that is empty or too large.

  Some of these, such as the date, depend on the request alone and could be named safely. They stay bare so the rule stays one a test can check: detail comes from the published schema, or not at all.
- **Only after authentication.** Validation runs after authentication, so a caller without a valid token learns nothing about its arguments.
- **The audit is unchanged.** It records the reason alone, as before.

Changed files:
- `record_service/server.py`: the validator tracks its path and names the keyword, and only its failures carry detail.
- `record_service/contracts.py`: the revision note, `ARGUMENT_PROBLEMS`, `ARGUMENT_PATH_PATTERN`, and `is_refusal_plain`, which states the exact rule.
- `clients/http.py` and `scenarios/runner.py`: the two consumers in this repository that checked a refusal's shape. They now use `is_refusal_plain`. Without that change, the HTTP client would have turned every named refusal into `unavailable`.

## Regression tests

- **`tests/test_revision_5.py`.** One test for each rule the revision states: 158 cases, run against both stores where a store is involved. They check that:
  - every keyword is named at its path, on both surfaces and on the media endpoints;
  - the path and the problem resolve in the published schema;
  - the twelve problems are exactly the keywords the validator checks and the schemas use;
  - no refusal holds a value the caller sent;
  - the refusal is the same whatever the record holds;
  - these stay bare: checks the schema doesn't publish, a check that depends on the record, an unknown tool, and every refusal made before validation;
  - the schema validator is the only code that can raise a named refusal;
  - the audit is unchanged;
  - the refusal crosses MCP over HTTP and the HTTP client intact.

  One test runs this probe's own calls against the branch over loopback.
- **Existing pins.** 67 existing test cases in `tests/test_server.py` and `tests/test_revision_3.py` pinned the bare refusal for schema failures. Each now pins the exact named refusal, so they are stricter than before. The pins for checks outside the schema still pin the bare refusal, and still pass.
- **Mutation check.** Eleven deliberate breaks, made one at a time; the tests caught all eleven:
  1. drop the detail;
  2. add detail to every `invalid_request`;
  3. name the caller's extra argument;
  4. echo the caller's value;
  5. report the last missing argument instead of the first;
  6. lose array indexes;
  7. report one keyword as another;
  8. allow detail on another reason class;
  9. drop a keyword from the vocabulary;
  10. restore the old strict check in the client;
  11. restore it in the scenario runner.
- **The whole suite:** 1,955 passed and 5 skipped, on Python 3.13.17.

## What this does not show

- **No agent ran against the improved record.** The evidence is this probe, a script. It shows what the record now says, not that an agent recovers faster because of it. A second cold-start run after a redeploy would test that, and it would cost model calls.
- **Only the first failure is named.** A request with several faults takes one round trip per fault.
- **A failure outside the schema still gets no hint.** February 30th is refused bare, by design.
- **The hosted record hasn't changed.** It stays as it is until it is redeployed, and until then the guide's known-limits line remains true of it.
  - November 16th, 2026: it has since been redeployed (The hosted rerun, below), and the guide's known-limits line was narrowed in its version 1.1.

## Evidence

- `probe_refusals.py` and `run_local_probe.py`: the probe and its local runner. Both use the standard library only, and neither makes a model call.
- `before/hosted-probe.json` and `before/hosted-wire.jsonl`: the hosted run, as the probe saw it and as the recorder logged each exchange.
  - No request through the recorder carried an Authorization header; the token proxy added it beyond the recorder.
  - Two WorkOS identifiers in the control call's grant are replaced with placeholders. `before/MANIFEST.json` gives each file's SHA-256 before and after redaction, and the number of replacements.
- `before/local-main-probe.json` and `after/local-branch-probe.json`: the local runs.

**Cost.** No model calls. The hosted run made eleven calls as the shift agent. Ten failed validation before the record was read, and one was a read. By construction, then, the only change to the hosted record is its audit log. That was not checked against the hosted database.

## To repeat

From the repository root, on this branch:

```
python usability/bad-argument/run_local_probe.py --out after.json
python -m pytest -q tests/test_revision_5.py
```

On `main`, the first command gives the "before" answers.

To probe a hosted record:
1. Start part 2's harness, `usability/cold-start/harness/serve_harness.sh`, which is on its own branch until merged.
2. Run `python usability/bad-argument/probe_refusals.py --url http://127.0.0.1:8798/mcp --out <file>`.

November 16th, 2026: this change and part 2's harness are both on `main` now. So `main` gives the "after" answers, and the "before" answers come from 64a9465. This replaces "On `main`, the first command gives the "before" answers" and "which is on its own branch until merged" above, which are kept as written.

## The hosted rerun

November 16th, 2026. After this change was merged, the hosted record was backed up and redeployed from `main` at ff88f66 (contract revision 5). The deployed `server.py`, `contracts.py`, and `store.py` match `main` by SHA-256. The stored data came through unchanged: every table holds the same number of rows, and an integrity check passes. The probe then ran against the hosted record again, the same way as the "before" run.

| Run | Record | Code | Started (UTC) |
|---|---|---|---|
| After, hosted | The hosted record, through the shift agent's token proxy and part 2's recorder | `main` at ff88f66 (contract revision 5) | 2026-11-16 04:10:13 |

**Result.** Each of the ten malformed calls got exactly the answer in the After column above, with the same HTTP status and the same `isError`. Nine name the argument and the rule, and the date that doesn't exist is still refused bare. The control call's answer is the same as in the "before" run, so the caller's grants hadn't changed.

**Cost.** No model calls, and eleven calls as the shift agent, as before. This time the hosted database was checked afterwards: the only change was eleven new audit rows, one for each call, timed from 04:10:15 to 04:10:19 UTC.

**Evidence.**
- `after/hosted-probe.json` and `after/hosted-wire.jsonl`: the hosted rerun, as the probe saw it and as the recorder logged each exchange. As before, no request through the recorder carried an Authorization header.
- The same two WorkOS identifiers are replaced with the same placeholders. `after/MANIFEST.json` gives each file's SHA-256 before and after redaction, and four replacements in each.

**What this still does not show.** No agent has run against the improved record. A second cold-start run would test whether a named refusal helps an agent recover, and it would cost model calls.
