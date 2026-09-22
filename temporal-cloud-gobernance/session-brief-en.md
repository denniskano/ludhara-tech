# Session brief — Temporal Cloud for BCP and Yape

**MSA** = Master Service Agreement. That is the main contract with Temporal (support fee, legal terms). It is **not** a Temporal Cloud account.

**Goal:** BCP and Yape work on their own: create namespaces, see metrics, see billing. They should not see each other. We still pay **one** monthly support fee.

---

## What to say first

The contract can cover two companies. The **product** cannot hide two companies inside **one** Cloud account.

The isolation unit is the **Account**, not the namespace and not the contract.

Adam’s links (internal runbooks, `prod.cp`) are Temporal’s internal docs. For us, the public tools are: Billing API, Usage page, Invoices page, OpenMetrics. Those tools work **inside one account**. They are good for cost by namespace (for example APOQ vs NREM). They do **not** give Yape a separate company.

---

## One account vs two accounts

| What we need | One shared account | Two accounts (BCP + Yape) under one MSA |
|---|---|---|
| Each team creates namespaces without the other seeing them | No. Account Owner / Global Admin see everything. | Yes. |
| Independent metrics | No. One metrics API key sees all namespaces. | Yes. Two keys, two scrapes. |
| Independent billing in the UI | No. One invoice. Tags are only internal chargeback. | Yes. Each account has Usage + Invoices. |
| One support fee | The contract does not create accounts. | Ask sales/support to attach **both** Account IDs. Adam already said: open a ticket for you **and Yape**. |

Also: one email address can belong to **only one** account. Same email domain is OK (two SAML setups). People who need both accounts need two emails.

**Ask for this shape:**

```text
One contract (MSA + monthly support)
   ├── Account BCP  → BCP namespaces → BCP metrics → BCP invoice
   └── Account Yape → Yape namespaces → Yape metrics → Yape invoice
```

Do not put both companies in one account with a tag `org=bcp` / `org=yape`. That is chargeback, not independence.

---

## Questions for this session (read these)

1. Please confirm in writing: the MSA covers **two Account IDs** (BCP and Yape) with **one** support fee. Share both Account IDs and the legal name on each invoice.
2. Does Yape use the same support SLA and ticket quota as BCP?
3. Usage invoices: one combined invoice, or two? Are Action commits and credits **shared** or **per account**?
4. Limits (namespaces, RPS, TRU): per account or shared?
5. Please create (or confirm) a **separate Yape account**: their Account Owner, their SAML.
6. Can corporate finance pull Billing API from **both** accounts without being Yape Account Owner? If not, we will sum two CSV files.
7. Confirm metrics: two Metrics Read-Only keys. No cross-account scrape.
8. Please turn on Billing API on **each** account, and explain it with **customer** steps (UI / Cloud Ops API), not internal runbooks.
9. PrivateLink / mTLS: per account or per namespace?
10. Before we leave: write down Account IDs, how support is billed vs usage, and the onboarding ticket number.

---

## If they talk about tags and Billing API

That answers “how does BCP split cost across namespaces?”  
That does **not** answer “how does Yape stay independent from BCP?”
