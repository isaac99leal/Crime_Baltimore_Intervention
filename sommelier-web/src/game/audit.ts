import { legalAgeingRules } from './ageing';
import { productResolutionRuleById } from './productResolver';
import { findGrape, placeAllowsGrape, referencePlaces } from './reference';
import { researchSourceById } from './research';
import type { WineDefinition } from './types';

export type AuditSeverity = 'info' | 'warning' | 'error' | 'critical';
export type AuditCategory =
  | 'identity'
  | 'gi-grape-legality'
  | 'product-resolution'
  | 'historical-law'
  | 'provenance'
  | 'ageing-law'
  | 'chronology';

export type AuditFinding = {
  id: string;
  category: AuditCategory;
  severity: AuditSeverity;
  title: string;
  detail: string;
};

export type WineProvenanceAudit = {
  wineId: string;
  riskScore: number;
  band: 'low' | 'moderate' | 'high' | 'critical';
  findings: AuditFinding[];
  passedHardIdentityChecks: boolean;
};

export type AuditChallenge = {
  wineId: string;
  prompt: string;
  options: string[];
  correctOption: string;
  finding?: AuditFinding;
  explanation: string;
};

const severityRank: Record<AuditSeverity, number> = { info: 0, warning: 1, error: 2, critical: 3 };
const clamp01 = (value: number) => Math.max(0, Math.min(1, value));
const norm = (value: string) => value.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase();

function resolvedReferencePlace(wine: WineDefinition) {
  const referencePath = wine.referencePath?.map(norm).join(' / ');
  if (referencePath) {
    const exact = referencePlaces.find((place) =>
      place.country === wine.country && place.path.map(norm).join(' / ') === referencePath,
    );
    if (exact) return exact;
  }

  if (wine.appellation) {
    const target = norm(wine.appellation);
    const candidates = referencePlaces.filter((place) => place.country === wine.country && norm(place.name) === target);
    if (candidates.length === 1) return candidates[0];
  }

  return undefined;
}

function addFinding(findings: AuditFinding[], finding: AuditFinding) {
  if (!findings.some((candidate) => candidate.id === finding.id)) findings.push(finding);
}

export function auditWineProvenance(wine: WineDefinition, currentYear = 2026): WineProvenanceAudit {
  const findings: AuditFinding[] = [];
  let risk = clamp01(wine.provenanceRisk ?? 0.08);
  let hardIdentity = true;

  const grape = findGrape(wine.grape);
  if (!grape) {
    hardIdentity = false;
    risk += 0.55;
    addFinding(findings, {
      id: 'unknown-grape', category: 'identity', severity: 'critical',
      title: 'Cultivar identity does not resolve',
      detail: `${wine.grape} does not resolve to the curated grape master. Do not infer a synonym or prime variety.`,
    });
  }

  const place = resolvedReferencePlace(wine);
  if (!place) {
    risk += 0.18;
    addFinding(findings, {
      id: 'unresolved-reference-place', category: 'identity', severity: 'warning',
      title: 'Reference geography is not independently resolved',
      detail: 'The displayed geography does not resolve to a generation-safe place record through the stored reference path/appellation.',
    });
  } else if (grape && !placeAllowsGrape(place, grape.name)) {
    hardIdentity = false;
    risk += 0.65;
    addFinding(findings, {
      id: 'gi-grape-mismatch', category: 'gi-grape-legality', severity: 'critical',
      title: 'GI/grape legality mismatch',
      detail: `${grape.name} is not allowed by the resolved grape set for ${place.country} / ${place.path.join(' / ')}.`,
    });
  }

  if (wine.vintage !== undefined && wine.vintage > currentYear) {
    hardIdentity = false;
    risk += 0.70;
    addFinding(findings, {
      id: 'future-vintage', category: 'chronology', severity: 'critical',
      title: 'Impossible future vintage',
      detail: `Vintage ${wine.vintage} is later than model year ${currentYear}.`,
    });
  }

  if (wine.productResolutionStatus === 'unresolved') {
    risk += 0.22;
    addFinding(findings, {
      id: 'product-unresolved', category: 'product-resolution', severity: 'warning',
      title: 'Exact product identity unresolved',
      detail: 'The geography/grape may be valid, but an exact legal product has not been resolved. Product-specific ageing and winemaking claims require caution.',
    });
  } else if (wine.productResolutionStatus === 'ambiguous') {
    risk += 0.30;
    addFinding(findings, {
      id: 'product-ambiguous', category: 'product-resolution', severity: 'error',
      title: 'Multiple product identities remain plausible',
      detail: 'Product-level claims are ambiguous and should not be treated as exact until a product term/style resolves them.',
    });
  }

  if (wine.productRuleId) {
    const rule = productResolutionRuleById.get(wine.productRuleId);
    if (!rule) {
      hardIdentity = false;
      risk += 0.55;
      addFinding(findings, {
        id: 'unknown-product-rule', category: 'product-resolution', severity: 'critical',
        title: 'Product rule reference is broken',
        detail: `Stored product rule ${wine.productRuleId} is absent from the product resolver registry.`,
      });
    }
  } else if (wine.productName) {
    risk += 0.18;
    addFinding(findings, {
      id: 'product-name-no-rule', category: 'product-resolution', severity: 'warning',
      title: 'Product name lacks a resolver rule',
      detail: `${wine.productName} is displayed without a stored product-rule identity.`,
    });
  }

  if (wine.vintage !== undefined && wine.legalEraStatus?.includes('historical-law-unverified')) {
    risk += 0.20;
    addFinding(findings, {
      id: 'historical-law-unverified', category: 'historical-law', severity: 'warning',
      title: 'Historical legal version unverified',
      detail: `The product identity may resolve, but the rule set in force for vintage ${wine.vintage} has not been explicitly versioned. Current law must not be projected backward.`,
    });
  }

  const sourceIds = wine.productSourceIds ?? [];
  if (wine.productRuleId && sourceIds.length === 0) {
    risk += 0.22;
    addFinding(findings, {
      id: 'missing-product-provenance', category: 'provenance', severity: 'error',
      title: 'Resolved product has no attached provenance sources',
      detail: 'The bottle carries a product-rule identity but no product source IDs. This should be quarantined for data review.',
    });
  }
  const unknownSources = sourceIds.filter((sourceId) => !researchSourceById.has(sourceId));
  if (unknownSources.length) {
    hardIdentity = false;
    risk += 0.45;
    addFinding(findings, {
      id: 'broken-source-refs', category: 'provenance', severity: 'critical',
      title: 'Broken provenance references',
      detail: `Unknown research source IDs: ${unknownSources.join(', ')}.`,
    });
  }

  const ageingIds = wine.legalAgeingRuleIds ?? [];
  const unknownAgeing = ageingIds.filter((id) => !legalAgeingRules.some((rule) => rule.id === id));
  if (unknownAgeing.length) {
    hardIdentity = false;
    risk += 0.45;
    addFinding(findings, {
      id: 'broken-ageing-rules', category: 'ageing-law', severity: 'critical',
      title: 'Broken legal-ageing references',
      detail: `Unknown ageing-rule IDs: ${unknownAgeing.join(', ')}.`,
    });
  }

  for (const flag of wine.provenanceFlags ?? []) {
    const lower = flag.toLowerCase();
    if (lower.includes('unresolved') || lower.includes('unverified') || lower.includes('missing')) {
      risk += 0.03;
    }
  }

  if (wine.dataConfidence === 'derived') {
    addFinding(findings, {
      id: 'derived-simulation-layer', category: 'provenance', severity: 'info',
      title: 'Derived simulation values present',
      detail: 'Some bottle behavior is simulation-derived. This is valid when labeled as derived, but must not be represented as a published measurement.',
    });
  }

  findings.sort((a, b) => severityRank[b.severity] - severityRank[a.severity] || a.title.localeCompare(b.title));
  const riskScore = clamp01(risk);
  const band: WineProvenanceAudit['band'] = !hardIdentity || riskScore >= 0.80
    ? 'critical'
    : riskScore >= 0.55
      ? 'high'
      : riskScore >= 0.28
        ? 'moderate'
        : 'low';

  return { wineId: wine.id, riskScore, band, findings, passedHardIdentityChecks: hardIdentity };
}

const optionForCategory: Record<AuditCategory, string> = {
  identity: 'Identity/reference mismatch',
  'gi-grape-legality': 'GI/grape legality mismatch',
  'product-resolution': 'Exact-product resolution problem',
  'historical-law': 'Historical-law version problem',
  provenance: 'Provenance/source problem',
  'ageing-law': 'Legal-ageing rule problem',
  chronology: 'Chronology/vintage problem',
};

const allAuditOptions = [
  'GI/grape legality mismatch',
  'Exact-product resolution problem',
  'Historical-law version problem',
  'Provenance/source problem',
  'Legal-ageing rule problem',
  'Chronology/vintage problem',
  'Identity/reference mismatch',
  'No material provenance issue',
];

export function createAuditChallenge(wine: WineDefinition, currentYear = 2026): AuditChallenge {
  const audit = auditWineProvenance(wine, currentYear);
  const materialFinding = audit.findings.find((finding) => finding.severity !== 'info');
  const correctOption = materialFinding ? optionForCategory[materialFinding.category] : 'No material provenance issue';
  const distractors = allAuditOptions.filter((option) => option !== correctOption).slice(0, 3);
  const options = [correctOption, ...distractors].sort((a, b) => a.localeCompare(b));
  return {
    wineId: wine.id,
    prompt: `Audit ${wine.label}: which issue should be escalated first?`,
    options,
    correctOption,
    finding: materialFinding,
    explanation: materialFinding
      ? `${materialFinding.title}: ${materialFinding.detail}`
      : 'No material identity, product, law, chronology or provenance defect was found by the current audit rules.',
  };
}
