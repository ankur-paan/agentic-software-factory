# Spec Standard

Every task specification obeys this standard. Before a lane starts a task, a context-free **Spec Reader** checks the spec against this standard. A spec that fails the check does not start.

---

## 1. Required Sections

Every spec must contain these five sections in order:

1. **Task.** One line that states what the task does and why.
2. **Behaviour.** What a user or client sees when the task is done. Write at the level of observable behaviour. Put code-level detail in section 3 only.
3. **Files.** Every file that the task creates, changes, or deletes, one per line, with the reason:
   - `src/api/actions.py: change: validate state before starting action`
   Use `create`, `change`, or `delete`. Pseudocode, API shapes, and schemas are permitted. Full implementation code is not.
4. **Not in scope.** Things the task must not do or change. A reviewer finding that asks for one of these is not a defect of the task.
5. **Done when.** The tests that prove the task—each through the real production entrypoint—and the deterministic checks that must pass.

---

## 2. Rules

- **No contradiction.** The spec agrees with `rules/RULEBOOK.md` and any project brief or API reference. Where a spec must differ, it names the human/CTO ruling that permits it.
- **One meaning.** Two engineers who read the spec build the same thing. Where more than one design is defensible and the choice matters, the spec states the choice.
- **Bounded.** Anything that accumulates (queues, caches, retries, logs, buffers) has an explicit bound and a default.
- **ASD-STE100.** Write in clear, imperative Simplified Technical English with short sentences and zero fluff.

---

## 3. The Spec Check Output

The Spec Reader writes, in this exact order:

1. `PARAPHRASE:` the task in its own words, in five lines or less.
2. `FILES:` the files it expects the task to touch (from the spec and from the codebase), each with `create`, `change`, or `delete` and a reason.
3. `CONTRADICTIONS:` each conflict with the rulebook, brief, or API reference, one line each quoting both sides, or `none`.
4. `GAPS:` each missing section, unclear requirement, or unstated assumption, marked `Blocker`, `Major`, or `Nit`, or `none`.
5. A final line: `SPECCHECK: ready` or `SPECCHECK: not-ready`.

A spec is `not-ready` when there is any contradiction, `Blocker`, or `Major` gap.
A `not-ready` spec gets at most one revision and one re-check. A contradiction or a spec that is still `not-ready` is escalated to `.factory/inbox/escalations/`.
