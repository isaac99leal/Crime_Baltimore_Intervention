# Site-claim name filters

`SiteClaimRule` supports two optional site-name conditions:

- `allowed_site_names`: an explicit positive set. If present, all other site names fail closed.
- `excluded_site_names`: an explicit deny set applied after any positive set.

Names are compared with the catalog's normalized-name function. A rule that lists the same normalized name in both sets is rejected at load time.

This supports legal climat-by-color matrices without creating broad parent-level claims that authorize impossible label combinations.
