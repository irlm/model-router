# K2 — kernel edit probe

Can a model **fix real Linux kernel code**, verified by actually
compiling and running the kernel's own tests — and does irrelevant
context (noise) degrade its edits? K2 is the edit-task follow-up to
K1 (`benchmarks/kernel_probe/`), which only asked questions.

## Ground truth by construction

1. **Seeded bugs** (`mutate.py`): single-site operator mutations
   (`++`→`--`, `<=`→`<`, `==`→`!=`, …) in functions from `lib/string.c`,
   `lib/string_helpers.c`, `lib/cmdline.c`, `lib/siphash.c` of a pinned
   Linux v6.12 tree. A mutation is kept only if it (a) compiles,
   (b) makes its paired KUnit suite FAIL, and (c) the restored file
   passes again. 10 tasks survived (`results/kernel-edit/tasks.json`).
2. **Blind tasks**: the model sees the real failing KUnit output and
   the mutated function — never the pristine function, the diff, or
   the generator. `original_function` in tasks.json is oracle-only.
3. **Mechanical splice** (`kunit_lab.py`): the model replies with one
   complete C function; a brace-matching splicer (string/comment/char
   aware) replaces exactly the target function's span. Editing the
   tests, other functions, or headers is physically impossible.
4. **Grading = build + test** (`grade_edit.py`): each response is
   spliced into the mutated tree and the paired KUnit suite runs under
   UML (`tools/testing/kunit/kunit.py`). Outcomes: `fixed` |
   `still-failing` | `compile-or-boot-fail` | `abstained` |
   `unparseable` | `operational`. The oracle self-test (splicing the
   pristine functions) grades 10/10 `fixed`.

## Arms

- **B** — failing KUnit output + mutated function only (minimal packet).
- **A** — arm B plus real-but-irrelevant kernel source (K1's noise
  pool) up to `min(2·base + 20000, 70000)` chars.

Same no-tools sentence as K1 prompt v2; agent CLIs run from an empty
cwd so nothing can be looked up.

## Running

```
python3 mutate.py --tree ~/src/linux-6.12        # regenerate tasks
python3 run_edit.py --endpoint E --model M --arm B|A
python3 grade_edit.py                            # builds + runs KUnit
python3 tests/../tests/test_kernel_edit.py       # via pytest, 4 tests
```

Re-running `run_edit.py` resumes: records with `operational_error`
(timeouts, empty agy responses) are dropped and retried; graded
records are keyed per endpoint/model/arm/task in `grades.json`.

Notes: the kernel build needs `bc` on PATH; ollama is called with
free-form output here (K1's JSON mode would mangle the ```c fence).
