# Search admission regression benchmark

Run `.venv/bin/python scripts/evaluate_search_quality.py` locally. It reads only
`tests/fixtures/search_quality.json`; it does not collect, notify, read CRM or
change runtime state. CI runs it and includes its JSON report in the summary.
Any admission, missing-location warning or duplicate-selection mismatch fails
the command. Unit tests also prove that incorrect expectations are detected.

The initial set contains 25 admission cases and three duplicate groups tested
in both discovery orders. It covers native iOS, Kyiv/remote/unknown geography,
foreign remote restrictions, cross-platform and desktop roles, semantic AI
titles, absent details, required versus optional Python, RAG, embeddings and
specialist ML/research roles. Duplicate checks require the eligible URL to win
over a foreign variant and retain distinct roles.

Two cases paraphrase public vacancy requirements, with source URLs and capture
dates inside the fixture. Other cases are explicitly synthetic boundary cases;
company names and application URLs are placeholders. No recruiter contacts,
candidate profile, CRM contents or full vacancy pages are stored.

The Sigma example is admitted for review, not certified as a candidate match.
It still requires evidence of substantial AI SDLC experience, hands-on agent
orchestration and client communication. Its optional languages and RAG context
must not trigger a mandatory Python/ML exclusion. The AltexSoft example requires
Python specialization and lists restricted countries, so it is excluded.

Precision and recall describe only this curated admission dataset. They do not
measure unseen vacancies, live discovery coverage, source availability, profile
fit scores, company-domain exclusions or actual hiring eligibility. The initial
baseline is 11 true positives, 14 true negatives, zero false positives and zero
false negatives; duplicate groups have no mismatches. Operational source health
and liveness diagnostics remain separate evidence.

For a confirmed false admission or missed role, add the smallest paraphrased
case that preserves the relevant requirements and its provenance. Set the
expected outcome from the owner's search policy before changing matching code.
Do not weaken labels merely to turn CI green. Re-check dated public examples
when policy changes; saved fixtures are not claims that those jobs remain open.
