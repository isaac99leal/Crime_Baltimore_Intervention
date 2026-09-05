import productData from '../data/research/product_resolution_rules.json';
import { legalAgeingRules, type AgeingArchetype } from './ageing';
import { findGrape, type RawGrape, type ReferencePlace } from './reference';
import { researchProfileById, type ResearchProfile } from './research';
import { decisionOption, winemakingDecisionById, type WinemakingDecision, type DecisionOption } from './winemaking';

export type ProductGenerationStatus = 'generation-safe' | 'conditional' | 'reference-only';

export type ProductCompositionRule = {
  grape: string;
  minPct?: number;
  maxPct?: number;
  maxCombinedPct?: number;
  group?: string;
};

export type ProductPracticeRule = {
  decisionId: string;
  optionIds: string[];
};

export type ProductResolutionRule = {
  id: string;
  profileId?: string;
  country: string;
  designation: string;
  designationAliases?: string[];
  productName: string;
  family: string;
  color?: string;
  colorAny?: string[];
  matchTerms: string[];
  generationStatus: ProductGenerationStatus;
  ageingArchetype: AgeingArchetype;
  composition?: ProductCompositionRule[];
  requiredPractices?: ProductPracticeRule[];
  permittedPractices?: ProductPracticeRule[];
  prohibitedPractices?: ProductPracticeRule[];
  ageingRuleIds?: string[];
  minimumLeesMonths?: number;
  minimumOakMonths?: number;
  minimumOxidativeAgeingMonths?: number;
  minimumResidualSugarGPerL?: number;
  effectiveFromYear?: number;
  effectiveThroughYear?: number;
  notes?: string[];
};

type ProductResolutionFile = {
  schemaVersion: number;
  updatedAt: string;
  method: string;
  records: ProductResolutionRule[];
};

const file = productData as unknown as ProductResolutionFile;
export const productResolutionMethod = file.method;
export const productResolutionRules = file.records;
export const productResolutionRuleById = new Map(productResolutionRules.map((record) => [record.id, record]));

export type ProductResolutionRequest = {
  country: string;
  designation: string;
  vintage?: number;
  color?: string;
  requestedTerms?: string[] | string;
  grape?: string;
  blend?: Array<{ grape: string; percent: number }>;
};

export type LegalEraStatus =
  | 'current-rule-version'
  | 'historical-rule-version-explicit'
  | 'product-resolved-historical-law-unverified';

export type ProductResolution = {
  status: 'resolved' | 'ambiguous' | 'unresolved';
  rule?: ProductResolutionRule;
  alternatives: ProductResolutionRule[];
  profile?: ResearchProfile;
  legalEraStatus?: LegalEraStatus;
  exactProductGenerationSafe: boolean;
  historicalComplianceVerified: boolean;
  issues: string[];
  provenanceSourceIds: string[];
};

const norm = (value: string) => value
  .normalize('NFKD')
  .replace(/[\u0300-\u036f]/g, '')
  .toLowerCase()
  .replace(/[^a-z0-9]+/g, ' ')
  .trim();

function designationTokens(rule: ProductResolutionRule): string[] {
  return [rule.designation, ...(rule.designationAliases ?? []), ...rule.designation.split(/\s*\/\s*/)]
    .map(norm)
    .filter(Boolean);
}

function designationMatches(rule: ProductResolutionRule, country: string, designation: string): boolean {
  if (norm(rule.country) !== norm(country)) return false;
  const target = norm(designation);
  return designationTokens(rule).some((candidate) => target === candidate || target.includes(candidate) || candidate.includes(target));
}

function colorMatches(rule: ProductResolutionRule, color?: string): boolean {
  if (!color) return true;
  const target = norm(color);
  if (rule.color) return norm(rule.color) === target;
  if (rule.colorAny?.length) return rule.colorAny.some((candidate) => norm(candidate) === target);
  return true;
}

function requestedText(requested?: string[] | string): string {
  if (!requested) return '';
  return norm(Array.isArray(requested) ? requested.join(' ') : requested);
}

function termScore(rule: ProductResolutionRule, termsText: string): number {
  if (!termsText) return 0;
  let best = -1;
  for (const term of rule.matchTerms) {
    const normalized = norm(term);
    if (!normalized) continue;
    if (termsText === normalized) best = Math.max(best, 1000 + normalized.length);
    else if (termsText.includes(normalized)) best = Math.max(best, 100 + normalized.length);
  }
  return best;
}

function blendMap(request: ProductResolutionRequest): Map<string, number> | undefined {
  if (request.blend?.length) {
    return new Map(request.blend.map((item) => [findGrape(item.grape)?.name ?? item.grape, item.percent]));
  }
  if (request.grape) return new Map([[findGrape(request.grape)?.name ?? request.grape, 100]]);
  return undefined;
}

function compositionIssues(rule: ProductResolutionRule, request: ProductResolutionRequest): string[] {
  if (!rule.composition?.length) return [];
  const blend = blendMap(request);
  if (!blend) return [];
  const issues: string[] = [];

  for (const constraint of rule.composition) {
    const canonical = findGrape(constraint.grape)?.name ?? constraint.grape;
    const pct = blend.get(canonical) ?? 0;
    if (constraint.minPct !== undefined && pct < constraint.minPct) {
      issues.push(`${canonical} ${pct}% is below ${constraint.minPct}% minimum for ${rule.productName}.`);
    }
    if (constraint.maxPct !== undefined && pct > constraint.maxPct) {
      issues.push(`${canonical} ${pct}% exceeds ${constraint.maxPct}% maximum for ${rule.productName}.`);
    }
  }

  const groups = new Map<string, ProductCompositionRule[]>();
  for (const constraint of rule.composition) {
    if (!constraint.group || constraint.maxCombinedPct === undefined) continue;
    const values = groups.get(constraint.group) ?? [];
    values.push(constraint);
    groups.set(constraint.group, values);
  }
  for (const [group, constraints] of groups) {
    const limit = constraints.find((item) => item.maxCombinedPct !== undefined)?.maxCombinedPct;
    if (limit === undefined) continue;
    const total = constraints.reduce((sum, item) => sum + (blend.get(findGrape(item.grape)?.name ?? item.grape) ?? 0), 0);
    if (total > limit) issues.push(`${group} totals ${total}% and exceeds ${limit}% maximum for ${rule.productName}.`);
  }

  return issues;
}

function profileForRule(rule: ProductResolutionRule): ResearchProfile | undefined {
  return rule.profileId ? researchProfileById.get(rule.profileId) : undefined;
}

function legalEra(rule: ProductResolutionRule, vintage?: number): { status: LegalEraStatus; verified: boolean } {
  if (vintage === undefined) return { status: 'current-rule-version', verified: true };
  const from = rule.effectiveFromYear;
  const through = rule.effectiveThroughYear;
  if (from !== undefined && vintage >= from && (through === undefined || vintage <= through)) {
    return { status: 'historical-rule-version-explicit', verified: true };
  }
  return { status: 'product-resolved-historical-law-unverified', verified: false };
}

function provenanceFor(rule: ProductResolutionRule): string[] {
  const sourceIds = new Set<string>();
  const profile = profileForRule(rule);
  for (const sourceId of profile?.sourceRefs ?? []) sourceIds.add(sourceId);
  for (const ageingId of rule.ageingRuleIds ?? []) {
    const ageing = legalAgeingRules.find((candidate) => candidate.id === ageingId);
    for (const sourceId of ageing?.sourceRefs ?? []) sourceIds.add(sourceId);
  }
  for (const practice of [...(rule.requiredPractices ?? []), ...(rule.permittedPractices ?? []), ...(rule.prohibitedPractices ?? [])]) {
    const decision = winemakingDecisionById.get(practice.decisionId);
    for (const sourceId of decision?.sourceRefs ?? []) sourceIds.add(sourceId);
  }
  return [...sourceIds];
}

export function productRulesForDesignation(country: string, designation: string, color?: string): ProductResolutionRule[] {
  return productResolutionRules.filter((rule) => designationMatches(rule, country, designation) && colorMatches(rule, color));
}

export function resolveWineProduct(request: ProductResolutionRequest): ProductResolution {
  const termsText = requestedText(request.requestedTerms);
  const candidates = productRulesForDesignation(request.country, request.designation, request.color)
    .map((rule) => ({ rule, score: termScore(rule, termsText), issues: compositionIssues(rule, request) }))
    .filter((candidate) => candidate.issues.length === 0);

  if (!candidates.length) {
    return {
      status: 'unresolved',
      alternatives: [],
      exactProductGenerationSafe: false,
      historicalComplianceVerified: false,
      issues: [`No exact product rule resolves ${request.country} / ${request.designation}${request.color ? ` / ${request.color}` : ''}.`],
      provenanceSourceIds: [],
    };
  }

  const usable = termsText ? candidates.filter((candidate) => candidate.score >= 0) : candidates;
  if (!usable.length) {
    return {
      status: 'unresolved',
      alternatives: candidates.map((candidate) => candidate.rule),
      exactProductGenerationSafe: false,
      historicalComplianceVerified: false,
      issues: [`Designation resolves, but requested product terms do not match a researched product for ${request.designation}.`],
      provenanceSourceIds: [],
    };
  }

  const ranked = [...usable].sort((a, b) => b.score - a.score || b.rule.matchTerms.join(' ').length - a.rule.matchTerms.join(' ').length);
  const top = ranked[0];
  const tied = termsText ? ranked.filter((candidate) => candidate.score === top.score) : ranked;

  if (!termsText && ranked.length > 1) {
    return {
      status: 'ambiguous',
      alternatives: ranked.map((candidate) => candidate.rule),
      exactProductGenerationSafe: false,
      historicalComplianceVerified: false,
      issues: [`${request.designation} contains multiple researched products; product terms are required for an exact resolution.`],
      provenanceSourceIds: [],
    };
  }

  if (termsText && tied.length > 1 && tied[0].score === tied[1].score) {
    return {
      status: 'ambiguous',
      alternatives: tied.map((candidate) => candidate.rule),
      exactProductGenerationSafe: false,
      historicalComplianceVerified: false,
      issues: [`Requested terms match multiple product rules for ${request.designation}.`],
      provenanceSourceIds: [],
    };
  }

  const rule = top.rule;
  const profile = profileForRule(rule);
  const era = legalEra(rule, request.vintage);
  const exactProductGenerationSafe = rule.generationStatus === 'generation-safe' && Boolean(profile && profile.generationStatus === 'candidate');
  const issues: string[] = [];
  if (rule.generationStatus !== 'generation-safe') issues.push(`${rule.productName} is ${rule.generationStatus}; exact production legality is not fully extracted.`);
  if (rule.profileId && !profile) issues.push(`Referenced research profile ${rule.profileId} is missing.`);
  if (!era.verified && request.vintage !== undefined) issues.push(`Product identity resolves, but the exact legal rule version for vintage ${request.vintage} is not yet versioned.`);

  return {
    status: 'resolved',
    rule,
    alternatives: [],
    profile,
    legalEraStatus: era.status,
    exactProductGenerationSafe,
    historicalComplianceVerified: era.verified,
    issues,
    provenanceSourceIds: provenanceFor(rule),
  };
}

export function generationProductCandidates(place: ReferencePlace, grape: RawGrape): ProductResolutionRule[] {
  const designationText = [place.name, ...place.path].join(' / ');
  return productResolutionRules.filter((rule) => {
    if (rule.generationStatus !== 'generation-safe') return false;
    if (!designationMatches(rule, place.country, designationText)) return false;
    if (!colorMatches(rule, grape.color)) return false;
    const request: ProductResolutionRequest = { country: place.country, designation: designationText, grape: grape.name, color: grape.color };
    if (compositionIssues(rule, request).length) return false;
    const profile = profileForRule(rule);
    return Boolean(profile && profile.generationStatus === 'candidate');
  });
}

export function productWinemakingLegality(
  rule: ProductResolutionRule,
  decision: WinemakingDecision,
  option: DecisionOption,
): boolean | undefined {
  const prohibited = rule.prohibitedPractices?.find((item) => item.decisionId === decision.id);
  if (prohibited?.optionIds.includes(option.id)) return false;

  const required = rule.requiredPractices?.find((item) => item.decisionId === decision.id);
  if (required) return required.optionIds.includes(option.id);

  const permitted = rule.permittedPractices?.find((item) => item.decisionId === decision.id);
  if (permitted) return permitted.optionIds.includes(option.id);

  return decision.requiresDesignationCheck ? undefined : true;
}

export function strictProductWinemakingLegalCheck(rule: ProductResolutionRule) {
  return (decision: WinemakingDecision, option: DecisionOption) => productWinemakingLegality(rule, decision, option) === true;
}

export function validateProductResolver() {
  const issues: string[] = [];
  const unresolvedGrapes = new Set<string>();
  const ids = new Set<string>();
  for (const rule of productResolutionRules) {
    if (ids.has(rule.id)) issues.push(`Duplicate product rule id: ${rule.id}`);
    ids.add(rule.id);
    if (!rule.country || !rule.designation || !rule.productName || !rule.family || !rule.matchTerms.length) issues.push(`Incomplete product rule: ${rule.id}`);
    const profile = profileForRule(rule);
    if (rule.profileId && !profile) issues.push(`Unknown research profile ${rule.profileId} in ${rule.id}`);
    if (rule.generationStatus === 'generation-safe' && (!profile || profile.generationStatus !== 'candidate')) issues.push(`Generation-safe product lacks candidate profile: ${rule.id}`);
    for (const ageingId of rule.ageingRuleIds ?? []) if (!legalAgeingRules.some((candidate) => candidate.id === ageingId)) issues.push(`Unknown ageing rule ${ageingId} in ${rule.id}`);
    for (const constraint of rule.composition ?? []) if (!findGrape(constraint.grape)) unresolvedGrapes.add(constraint.grape);
    for (const practice of [...(rule.requiredPractices ?? []), ...(rule.permittedPractices ?? []), ...(rule.prohibitedPractices ?? [])]) {
      const decision = winemakingDecisionById.get(practice.decisionId);
      if (!decision) {
        issues.push(`Unknown winemaking decision ${practice.decisionId} in ${rule.id}`);
        continue;
      }
      for (const optionId of practice.optionIds) if (!decisionOption(practice.decisionId, optionId)) issues.push(`Unknown winemaking option ${practice.decisionId}/${optionId} in ${rule.id}`);
    }
  }
  return {
    records: productResolutionRules.length,
    generationSafe: productResolutionRules.filter((rule) => rule.generationStatus === 'generation-safe').length,
    conditional: productResolutionRules.filter((rule) => rule.generationStatus === 'conditional').length,
    referenceOnly: productResolutionRules.filter((rule) => rule.generationStatus === 'reference-only').length,
    countries: new Set(productResolutionRules.map((rule) => rule.country)).size,
    designations: new Set(productResolutionRules.map((rule) => `${rule.country}|${rule.designation}`)).size,
    issues,
    unresolvedGrapes: [...unresolvedGrapes].sort(),
  };
}
