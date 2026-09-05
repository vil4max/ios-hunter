# Career search tracks

## Audit and scope

Production uses `collector/companies.py`: official company APIs and watchlist
career pages/ATS, plus optional Telegram. DOU provides watchlist metadata;
DOU and Djinni vacancy feeds are not production sources.
Previously most collectors filtered to iOS before normalization, while Sigma
already searched AI. `parser/normalize.py` already had an AI-augmented predicate.
`analytics/fit_score.py` used only iOS skills and compared all required years to
iOS tenure. Scoring is run through `scripts/score_inbox.py`, separately from
collection and Inbox eligibility; changing weights does not suppress collection.

## Matching and queries

`config/search_tracks.py` documents target titles and configures AI search terms
and positive relevance patterns. Titles are examples, not an exact whitelist:
Senior Software Engineer + AI; Applied AI Engineer; AI Software Engineer;
LLM Engineer; Agentic AI Engineer; Backend Engineer + AI; AI Platform Engineer;
AI Integration Engineer; AI Solutions Engineer.

The shared collector predicate preserves the existing iOS predicate and accepts
engineering titles with AI/LLM keywords regardless of word order, or existing
AI implementation signals in descriptions. This is deterministic keyword
matching, not embeddings or an external LLM. Existing AI coding-tool matching
is retained. Generic Python, Docker or SQL alone cannot establish an AI track.
Junior-only and location rules remain unchanged.

Sigma, Ciklum, N-iX, Intellias and GlobalLogic retain their iOS query and add
AI, LLM and agentic queries. EPAM sitemap discovery adds AI/LLM/agentic slugs.
Official watchlist parsers and other bespoke collectors share the expanded gate.
Existing pagination/detail caps remain: this is broader discovery, not a claim
of exhaustive market coverage. Title-only sources may lack enough detail for
negative signals until descriptions are available. Sigma reference vacancy was read on 2026-09-05. Other live endpoints have not
been revalidated as part of this offline change. Secondary query failures keep
primary results and report degraded coverage. Sigma fetches AI vacancy details;
failed detail fetches remain visible as degraded coverage.

## Scoring

Existing iOS weights and public profile remain unchanged. AI receives a 5-point
secondary-track adjustment. Its opportunity stack score is 4 + 3 per distinct
positive category, capped at 25: LLM APIs, agents/tool orchestration, RAG,
structured generation, evals, observability, reliability/fallbacks, backend
integration, cloud, Docker, SQL. These are opportunity signals, not claims of
proven candidate skills. AI experience contributes 7 points pending evidence;
iOS tenure never proves commercial Python/ML tenure.

Each distinct negative signal deducts 15 points: specialist Data Science,
research, CV/NLP or MLOps titles; explicitly primary/heavy research,
model-training or MLOps responsibilities; mandatory 3+ commercial/professional/
production years in Python or ML within the same sentence. Python alone and
explicit optional/preferred requirements do not incur a penalty. These are
conservative English keyword heuristics, not complete requirement parsing.
Existing pure ML/Data Scientist title exclusions remain in the parser.

For example, `Senior Software Engineer, AI` with LLM APIs, RAG, evals and
backend integration is eligible without the word Applied. `AI Software Engineer`
using Python remains eligible. A mandatory five-year commercial Python
requirement now excludes it from the AI collection/Inbox and marks it skip
when scored directly, without claiming iOS years cover it. Research-heavy AI roles rank lower. Scores remain 0–100 with strong
at 78, review at 62, weak below; existing domain/location blockers still skip.

## Compatibility and rollback

No schema, dependency, identity, deduplication, profile or CRM migration.
Existing callable iOS/AI predicates remain available. Revert this scoped diff
to restore the former discovery and score rules; existing CRM data is untouched.

## Requirement-aware eligibility

The updated requirement gate excludes mandatory strong/deep/advanced Python,
ML model development, specialist research roles, and hard commercial Python/ML
experience requirements. Optional sections (Nice to have, Bonus, Preferred
qualifications) and explicitly optional bullets are ignored by this gate.
RAG and embeddings alone are never blockers. iOS eligibility remains unchanged.
Unknown mandatory JavaScript, TypeScript, MCP, orchestration, multi-agent,
AI SDLC and consulting skills cap AI fit below strong and produce evidence
requests. This is conservative English text matching, not proof of fit.

The existing Telegram/Inbox delivery and AI label are retained. No new channel
or delivery action was created or executed during verification.

Reference: https://career.sigma.software/vacancy/ai-augmented-software-developer/
(read 2026-09-05). Its detailed requirements allow alternative programming
languages; Python is not mandatory. One year of extensive AI SDLC, hands-on
agents/orchestration/MCP and client-facing skills require evidence. RAG,
embeddings, MLOps and fine-tuning are optional. The summary labels JS/TS strong,
while the detailed requirements describe them as preferred: review this with
the recruiter instead of assuming a confirmed match.

The [full registry audit](company-ai-search-audit.md) covers 92 companies.
DataArt, Luxoft and Infopulse retain their primary pass and add broader
category/specialization or AI keyword passes. Generic HTML helpers use the
same two-track gate. Digis currently lacks a resolved official career URL.
