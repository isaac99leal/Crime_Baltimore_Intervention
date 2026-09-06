# Simulation matrix model

The simulator keeps four modeling layers separate:

`grape baseline × place modifier × vintage modifier × winemaking modifier`

This file defines how those layers should be interpreted when research data is added.

## 1. Grape baseline

The baseline comes from the original curated grape data and remains on the legacy structural scale:

- acidity: 1–5
- tannin: 1–5
- body: 1–5
- sweetness: 1–5
- fruit intensity: 1–5
- earth intensity: 1–5
- alcohol: actual percentage/range where present

Other grape traits such as climate preference, vigor, yield potential, frost/drought/disease tolerance and winemaking affinities remain varietal attributes rather than place or vintage facts.

## 2. Place modifier

Environmental profiles use researched place facts such as:

- macroclimate and mesoclimate
- annual/growing-season rainfall when published
- altitude and slope
- aspect and exposure
- geology and parent material
- soil texture and depth
- limestone/clay/sand/gravel/slate/volcanic composition
- drainage and water-holding behavior
- maritime/river/mountain influences
- frost, drought, wind and disease pressure
- botrytis-supporting mesoclimate where documented

The environmental matrix is a bounded `-1..+1` simulation transform. It is not an analytical result published by the source.

Current place matrix axes:

- acidity
- tannin
- body
- alcohol
- fruit intensity
- earth intensity
- aromatic freshness
- drought stress
- disease pressure
- frost risk
- botrytis suitability

## 3. Vintage modifier

Historical vintage observations record sourced facts before any simulation number is assigned. Relevant fields include:

- winter conditions
- budbreak and flowering
- frost and hail
- heatwaves and sunburn
- drought and water reserves
- rainfall timing
- mildew/disease pressure
- veraison/ripening pace
- harvest start/end
- fruit health
- crop/yield effects
- must weight or potential alcohol when published
- acidity/pH commentary when published
- selective-picking or botrytis conditions
- authority assessment or official categorical vintage rating

Vintage matrix axes are also bounded `-1..+1`:

- acidity
- ripeness
- concentration
- tannin ripeness
- aromatic freshness
- disease pressure
- yield
- ageability
- botrytis suitability

A vintage without sourced year-specific observations receives no invented weather modifier.

## 4. Winemaking modifier

Winemaking is intentionally separate from terroir and vintage. Future/expanded matrices should model choices such as:

- harvest maturity and sorting
- whole cluster / destemming
- skin contact and extraction
- fermentation temperature
- vessel type
- oak age, size, origin and toast
- lees contact / bâtonnage
- malolactic fermentation
- oxidative versus reductive handling
- appassimento/drying
- botrytis selection
- fortification
- flor/biological ageing
- solera/fractional blending
- sparkling-wine press fraction, secondary fermentation and lees ageing
- skin-contact/amphora/qvevri production

Legal production rules constrain which choices are permitted. The matrix models sensory consequences only after legality is established.

## Combination rule

Place and vintage modifiers are incremental, not replacements for the grape baseline. Runtime transforms are deliberately conservative and clamped to the existing profile scale. A derived value is never displayed as if it were a laboratory measurement, official vintage score or regulatory fact.

Measured observations remain stored in their original units where possible. Examples include rainfall in millimetres/inches, elevation in metres, yield in kg/ha or hl, must weight in °Oechsle, temperature in °C and harvest dates as dates/text from the authority source.

## Confidence

Derived place/vintage matrices use a confidence value from 1–5. Confidence reflects how directly and specifically the available source material supports the simulation transform, not the prestige or quality of the wine region.

- 5: strong place/year-specific official observations with direct viticultural implications
- 4: strong official regional research with limited inferential steps
- 3: useful official evidence but meaningful within-region variability remains
- 2: partial observations; use small effects
- 1: preliminary; reference only until better supported

## Prohibited shortcuts

Do not:

- import the legacy unsourced `VINTAGE_QUALITY` number as factual vintage quality;
- generate fake historical rainfall, temperature or frost events;
- infer authorized grapes from planting statistics;
- infer a legal appellation from a statistical growing region;
- convert official categorical vintage labels into arbitrary numeric critic-style scores;
- apply a regional environmental profile to a materially different subregion when a better researched profile exists;
- let soil/climate matrices override legal identity;
- present a derived matrix value as a source quotation or physical measurement.
