# Night-shift handoff: person-a (mobility and eating)

Source: Synapse record, shift_handoff brief read 2026-11-15T23:02:25Z (verification passed). Only the record was used. Each statement cites its entry id and author. The record reports where accounts differ; it does not say which is right.

## Mobility: accounts differ (both are observed)
- Entry 14, Example General Hospital PT evaluation, effective 2026-10-15 (source discharge-note:EGH-2026-10-16): needs one-person assist to stand from a chair or bed. Walks about 20 feet with a walker and standby assistance. Advised to use the walker at all times.
- Entry 10, Example Gardens aide note (aide-note:EXG-2026-10-12-0900), about 2026-10-10: she walked to and from breakfast with her walker, without assistance. The note is a correction of an earlier Oct 10 note.
- Entry 10 is the older of the two. Entry 14 is the later, clinical evaluation. I did not resolve the difference.
- Cautious practice until someone with authority confirms otherwise: keep the walker with her. Give standby help when she walks and a one-person assist for standing. That follows entry 14.
- No fall or other mobility entries stand in this brief.

## Eating: accounts differ
- Entry 1, daughter (family), reported, 2026-09-20: eats a full breakfast most days. Lunch is small. Dislikes spicy food. Drinks about four glasses of water a day when reminded.
- Entry 7, Example Gardens aide, observed, 2026-10-10 13:00 (aide-note:EXG-2026-10-10-1300): ate most of breakfast and about half of lunch. Drank two cups of water.
- These are old (about 5 to 8 weeks). The record holds nothing more recent on eating. Please observe and record intake tonight.

## Day-shift relayed claim: NOT used
- The day shift's agent sent an eating claim in relayed-claim.json. I checked it against the record with check_claims. The result was differs_from_record (value_mismatch).
- Its entry 7 says she ate "all of lunch". The record's entry 7 says "about half of lunch". Entry 1 and the other fields matched.
- The relayed claim overstates her lunch intake. Do not rely on it. Use the entry 7 wording above.
- The cause is unknown. It could be an alteration or a transcription error.

## Not covered
Medications, sleep and other kinds were outside this note's scope.
