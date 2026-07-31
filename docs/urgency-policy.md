# Urgency policy

**Status:** decided, pending application to labels
**Applies to:** `expected_urgency` in `evals/dataset/tickets.json` and the urgency
rubric in `SYSTEM_PROMPT`
**Constraint:** this document contains no reference to any case in the eval suite.
It was written to be applicable to tickets outside the dataset, and validated
against tickets outside the dataset before being applied to any label.

---

## 1. Scope

This document is the single source of truth for what `urgency` means in this
system. Two artifacts depend on it:

- the dataset labels, which are the answer key the harness measures against
- the rubric text in `SYSTEM_PROMPT`, which is what the agent is instructed with

If those two disagree, the eval measures nothing useful. See section 7.

---

## 2. Policy

<!-- BEGIN PROMPT BLOCK: lift verbatim into SYSTEM_PROMPT -->

**Urgency answers WHEN a ticket must be worked.** It does not say how bad the
situation is, and it does not say who works it.

The question to ask: **how fast does this get worse if nobody touches it?**

That is a question about the *rate* at which harm accrues, not the *amount* of
harm already present.

### Bands

| Band | Test |
|---|---|
| `high` | Harm accrues, or a window closes, within hours. Delay past the current shift makes the outcome materially worse or unrecoverable. |
| `medium` | Harm accrues, or a window closes, within days. Delay past the current shift is tolerable. Delay past the week is not. |
| `low` | No clock is running. The outcome is the same whether this is worked today or next week. |

Where more than one clock applies, the shortest one sets the band.

Where the ticket does not carry enough information to identify a clock, the
outcome is `unresolved` and NO band is assigned. A forced band is worse than a
recorded gap, because a gap stays visible while a forced value enters the answer
key as though it had been decided.

### What starts a clock

1. **Ongoing accrual.** Harm is still being added while the ticket sits: a
   failure that repeats, a loss that continues, a service still degraded.
2. **A closing window.** An action becomes impossible or substantially more
   costly after a fixed point: dispute and refund windows, scheduled deletions,
   effective dates, statutory deadlines.
3. **Active exploitation.** A security concern being exercised now, as distinct
   from a weakness that exists but is not currently being used.
4. **A stated external deadline.** A date by which the customer must have the
   outcome. The date sets the band. Stating a deadline does not by itself make
   something `high`.

### What does not set urgency

1. **Tone.** Anger, threats, escalation language, and repeated follow-ups do not
   move the band. Tone is a communication input, not a time input.
2. **Harm already completed.** A finished one-time loss does not get more urgent
   with delay. Recovering it is time-critical only where a window is closing.
3. **Whether a human is required.** `needs_human` answers WHO. `urgency` answers
   WHEN. Neither field implies the other, in either direction.
4. **Absolute magnitude.** A large dollar figure or a large affected-user count
   describes size, not rate. Breadth may raise a band only where harm is already
   accruing, because there breadth changes how fast it accrues. Breadth never
   starts a clock on its own.
5. **Account tier.** Commercial value belongs to queue priority, which is a
   separate concern from time sensitivity and is out of scope for this field.

<!-- END PROMPT BLOCK -->

---

## 3. Why time sensitivity, and not the alternatives

Two other anchors were considered and rejected.

- **Consequence severity.** Rejected because it collapses into `needs_human`. A
  ticket severe enough to matter is a ticket a human should see, so the two
  fields would measure one thing while an eval scoring both would look twice as
  broad as it is.
- **Observable ticket features.** Rejected because a keyword-to-band mapping is a
  lookup table, not judgment. This repo exists to demonstrate that an agent can
  apply policy, so encoding the policy as string matching removes the thing being
  demonstrated.

Time sensitivity survives both objections: it is orthogonal to `needs_human`, and
it requires reading the situation rather than the vocabulary.

### Orthogonality check

All four quadrants must be reachable. If any one is unpopulatable, the two fields
are measuring one thing.

| | no human needed | human needed |
|---|---|---|
| **not urgent** | product feature question | contract language review |
| **urgent** | password reset blocking a live demo | payment failing right now on an enterprise account |

All four populate, using situations from outside the eval suite.

---

## 4. Decisions of record

Each of these is a support-policy call, not a technical one. Each is stated with
the position taken, the alternative, and what switching would cost.

**4.1 Customer-stated deadlines start a clock, and the date sets the band.**

- *Alternative:* ignore stated deadlines entirely, on the grounds that they are
  self-reported and therefore a form of tone.
- *Why not:* a stated date is the most common form of time information a customer
  actually supplies. Discarding it throws away the field's best signal.
- *Why the date and not the statement:* honoring "I need this by X" as `high`
  regardless of when X falls lets the customers who write urgently set the band,
  which is tone through the back door. A deadline four days out is `medium`.
- *Cost of switching:* affects any label where the ticket names a date.

**4.2 Breadth raises a band only where a clock is already running.**

- *Alternative:* breadth never affects the band, since it is size and not rate.
- *Why not, quite:* more affected users means harm accruing faster per hour, which
  is a rate claim rather than a size claim. That argument is legitimate.
- *Why the restriction:* letting breadth act alone turns the field into "big
  things are urgent," which is the severity anchor rejected in section 3.
- *Cost of switching:* affects labels on wide-blast-radius tickets only.

**4.3 Account tier is excluded from urgency.**

- *Alternative:* include it, since real support organizations do prioritize by
  contract value.
- *Why not:* it makes the field a blend of elapsed-time risk and commercial value,
  which are incommensurable. It also breaks the orthogonality argument in section
  3, because tier correlates with escalation.
- *Where it belongs:* queue priority, which this system does not model.
- *Cost of switching:* this is the decision most likely to conflict with an
  existing label rationale, so expect it to surface during application.

---

## 5. Validation on tickets outside the dataset

A rubric that classifies every case in the suite may still be transcription of the
answer key. The only real test is whether it classifies tickets it was not written
against. Six, none of which appear in the eval suite:

| Ticket | Band | Governing rule |
|---|---|---|
| Nightly export has failed since Tuesday, file is needed for a Thursday board meeting | `medium` | stated deadline, days out; ongoing accrual also days |
| GDPR deletion request, 30-day statutory deadline, 26 days remain | `low` | window exists but is distant; becomes `high` as it closes |
| Phishing mail spoofing our support address, reports arriving now | `high` | active exploitation |
| Does your API support webhook retries? | `low` | no clock |
| Sole admin left the company, nobody can add or remove users | `medium` | blocked operations compound over days, nothing degrading hourly |
| Third mail about a typo in the invoice template, service described as appalling | `low` | tone does not move the band |

Six for six with no case-specific rule invoked.

The GDPR row is the load-bearing one. A statutory deadline with real legal weight
yields `low` because the clock, while genuine, is distant. Any severity-anchored
rubric gets that wrong, which is evidence the anchor is doing work rather than
decorating a set of per-case rules.

---

## 6. Non-goals

- **Queue priority.** Urgency is one input to it. This document does not define it.
- **SLA mapping.** No band is claimed to correspond to a contractual response time.
- **Routing.** Where a ticket goes is `category` and `needs_human`, not this field.

---

## 7. Synchronization with SYSTEM_PROMPT

The prompt block in section 2 is duplicated into `SYSTEM_PROMPT`, which is the
same shape of problem as the JSON `input_schema` enum duplicating the Pydantic
`Literal`: two copies of one truth, drifting silently.

That duplication is accepted for the same reason, and it needs the same kind of
protection. Options, decided in step 7 of the build plan:

- a sync test asserting the prompt block and the prompt string match
- generating the prompt string from this file at import time
- accepting the drift risk and documenting it as a known gap

Until one is chosen, editing either copy requires editing the other in the same
commit.

---

## 8. Change control

The labels are part of the measuring instrument. Changing this document changes
the labels, and changing the labels voids the current baseline.

- Changing a band definition or a clock rule: re-apply to **all** cases, not the
  ones that currently fail. An audit whose sample was chosen by agent behavior is
  not an independent audit.
- Any label that moves: the baseline is void and must be re-taken before further
  deltas mean anything.
- Adjudicate on this policy alone. Do not read agent output for a case before
  deciding that case's label.