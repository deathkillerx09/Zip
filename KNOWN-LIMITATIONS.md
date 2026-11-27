# Known limitations

Honest list of what this build does **not** do, so nothing here is mistaken for a
finished commercial product.

## AI and content quality

1. **Quality depends entirely on your installed local model.** `qwen3.5:0.8b`
   produces short, sometimes shallow work. Product-file generation (a valid,
   useful HTML application) usually needs a larger model such as `qwen3:4b`; set
   `OLLAMA_MODEL_PRODUCT`. A small model will often fail validation, and the task
   then records a real failure instead of a fake product.
2. **Speed is hardware-bound.** An i5-1145G7 with Iris Xe and 16 GB RAM runs the
   tiny models comfortably but is slow with 4B+ models. The worker runs one model
   call at a time by design; a queue will build up if each call takes a minute.
3. **No live market research.** The system is offline by design and never invents
   competitors or statistics. Research briefs are structured reasoning, and the
   customer simulation is a deterministic heuristic over generated profiles —
   not evidence of demand, pricing or willingness to pay.
4. **No real customers, revenue or outreach.** Nothing is published, emailed,
   posted or sold. There is no CRM, no payment processor and no analytics.
5. **Product files are prototypes.** They are single-file, offline HTML apps with
   a validated structure. They are not audited for accessibility, security,
   scalability or legal compliance, and they are not deployed anywhere.
6. **Idea throughput is a target, not a guarantee.** "50 ideas per hour" is
   aspirational. Actual output depends on model speed, valid JSON, duplicates and
   queue pressure. Failures are reported, never padded.

## Scope of the town

7. **The visible town is an isometric 2.5D Canvas map**, not a full 3D world.
   The Three.js scene is included but opt-in and known to render poorly on this
   laptop's integrated GPU; it is a future milestone, not a feature claim.
8. **Employees are simulated collaborators.** Morale, XP, trophies, career levels
   and "feelings" are virtual statistics. There is no sentience claim anywhere.
9. **8 employees, fixed roles.** Adding a ninth role requires code and schema work.
10. **Single-process, single-user.** The scheduler is one asyncio loop in the web
    process. SQLite is fine for one user; it is not a multi-tenant database.
    Running two server processes against one database is not supported.

## Financial boundaries

11. **The ledger is not a bank.** There is no payout provider, card, bank
    connection, subscription or purchase. Withdrawal requests are recorded only
    and are never executed.
12. **Settlement is manual and self-attested.** When you reconcile a pending
    receipt with an evidence reference, the app trusts that reference. It does not
    verify a bank statement.
13. **No personal money, ever.** Spending requires verified town earnings *and* a
    non-zero owner limit. There is no loan, credit, or top-up mechanism.

## Operations

14. **The Windows launcher and stop script were written for Windows 11 but could
    not be executed in the Linux environment where this build was tested.** They
    are straightforward `cmd` scripts; if `py` is missing the launcher falls back
    to `python`, and both paths are guarded with error messages.
15. **Ollama must be installed and running** for any AI work. Offline, the town
    still opens, the dashboard stays accurate, and the queue explains exactly what
    is blocked.
16. **Cloud deployment is prepared, not performed.** No server, domain or TLS
    certificate has been provisioned. Nothing is publicly reachable. The compose
    stack assumes you bring a domain and a host, and it runs Ollama inside the
    compose network (`AI_MONEY_TOWN_ALLOW_REMOTE_OLLAMA=1`) — never expose that
    port publicly.
17. **Backups are your responsibility.** The launcher makes a one-time
    `town.db.prelaunch.bak`. Nothing schedules backups after that.
18. **No authentication beyond the site gate and owner token.** There are no user
    accounts, roles or sessions. That is appropriate for one owner on localhost or
    behind Basic Auth; it is not a multi-user product.
19. **Generated product files are not scanned for malicious code.** They come from
    your own local model and are served in a sandboxed CSP preview, but read the
    file before hosting it anywhere.

## UI

20. **The map is canvas-rendered**, so its labels are not accessible text to
    screen readers. The dashboard below it is plain, labelled HTML and is the
    accessible equivalent.
21. **Mobile layout is responsive but untested on real phones.** The town is
    designed for a desktop browser at 1280×700 or larger.

## Not implemented (deliberately)

* Automatic public launch of a business.
* Real payment processing, invoicing or tax handling.
* Customer contact, email sending, social posting or advertising.
* Multi-agent negotiation, hiring, or org-chart changes.
* Retrieval over your documents (the town has no knowledge base ingestion).
