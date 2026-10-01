# Sample corpus: mid-market accounts-payable automation

**Everything in this folder is synthetic.** The companies, people, publications, deals and numbers
are invented to exercise the pipeline. Northwind, Contoso and Fabrikam are Microsoft's long-standing
fictional sample-company names, used here for the same reason Microsoft uses them: nobody mistakes
them for real businesses.

- **Product under study:** Northwind AP, a fictional invoice-approval and exception-routing layer
  that sits on top of a mid-market company's existing ERP.
- **Named alternatives:** the Contoso Finance Suite AP module (ERP-native), Fabrikam Payables
  Services (outsourced AP), and the status quo (spreadsheets, shared inboxes and email approvals).

Each document carries frontmatter the provenance layer reads: `source_type`, `source_platform`,
`author_type`, and `published`. Document 08 is deliberately promotional, so the provenance penalty
has something to catch.
