# Vineyard registry evidence model

The Sommelier World Registry keeps vineyard/site identity separate from legal wine
authorization and from simulation priors.

## Evidence levels

- `official_appellation_climat`: a named climat listed by the relevant appellation
  authority or authoritative interprofessional registry.
- `official_appellation_lieu_dit`: a named lieu-dit listed for an appellation.
- `protected_appellation_named_site`: a protected origin whose protected name is
  itself a named vineyard/lieu-dit system, such as the Alsace Grand Cru names.
- `official_additional_geographical_mention` / `official_additional_geographical_unit`:
  the existing Italian MGA/UGA systems.
- `monopole` and `block` remain separate physical/control concepts.

A site record does not imply that all wines from the parent region may use that
name. Legal claim eligibility is still handled by the legal-rule layer.

## Missing data policy

Owner, ownership history, parcel area, coordinates, slope, aspect, elevation,
soil terms, and permitted grapes remain empty unless a cited source states the
specific fact for the specific site. Appellation-level geology or elevation is
not copied onto every site.

The schema now has fields for these dimensions so they can be added piecemeal
without changing site identity.

## 2026 expansion tranche

The materialized expansion adds BIVB-listed Premier Cru Climats and lieux-dits
for a large set of Côte de Nuits, Côte de Beaune, Côte Chalonnaise, and Chablis
appellations, plus the 51 INAO Alsace Grand Cru names.

The source registry also records bulk sources that were researched but are not
yet materialized:

- Bourgogne Maps: BIVB reports 11,541 identified Climats/lieux-dits and 296,663
  mapped parcels. The map is informational; official parcel delimitations remain
  the deposited INAO/municipal plans.
- Landwirtschaftskammer Rheinland-Pfalz Weinbergsrolle: over 1,600 Einzellagen
  plus registered Gewannen, with official names, municipalities, cadastral areas,
  and planted area.
- Land Niederösterreich open data: official Ried/Subriede GIS attributes and
  geometries, explicitly marked by the state as not yet statewide complete.
- Stadt Wien Riedenkarte: all 140 Vienna Weinbaurieden with parcel-level
  delineation.

These discovered bulk sources are kept as non-materialized targets until an
ingest can preserve their jurisdiction-specific semantics and source version.
