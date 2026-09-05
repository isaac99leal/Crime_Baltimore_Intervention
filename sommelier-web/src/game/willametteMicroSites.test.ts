import { describe, expect, it } from 'vitest';
import {
  findWillametteBlocks,
  findWillametteSite,
  validateWillametteMicroSites,
  willametteDataQualityFlagCount,
  willametteMicroSiteCount,
  willametteMicroSitePassCount,
  willametteNamedBlockCount,
  willametteSubSiteObservationCount,
} from './willametteMicroSites';

describe('Willamette vineyard micro-site research', () => {
  it('locks a granular but source-bounded vineyard/block library', () => {
    const report = validateWillametteMicroSites();
    expect(willametteMicroSitePassCount).toBe(2);
    expect(willametteMicroSiteCount).toBe(11);
    expect(willametteNamedBlockCount).toBeGreaterThanOrEqual(57);
    expect(willametteSubSiteObservationCount).toBeGreaterThanOrEqual(79);
    expect(willametteDataQualityFlagCount).toBeGreaterThanOrEqual(1);
    expect(report.issues).toEqual([]);
  });

  it('preserves Open Claim row, acreage, clone and rootstock detail by block', () => {
    const block6 = findWillametteBlocks('us-or-open-claim-vineyard', '6')[0];
    const block8 = findWillametteBlocks('us-or-open-claim-vineyard', '8')[0];
    expect(block6).toMatchObject({ variety: 'Pinot Noir', rows: 51, acres: 2.06, clone: '943', rootstock: '44-53' });
    expect(block8).toMatchObject({ variety: 'Pinot Noir', rows: 52, acres: 2.49, clone: '115', rootstock: '101-14' });
  });

  it('preserves Terry Family named blocks as actual named site records', () => {
    const block13 = findWillametteBlocks('us-or-terry-family-vineyard', '13')[0];
    expect(block13).toMatchObject({ name: 'Christmas Tree', variety: 'Pinot Noir', clone: '828', rootstock: '101-14' });
    expect(findWillametteSite('us-or-terry-family-vineyard')?.blocks).toHaveLength(13);
  });

  it('keeps Shea hill zones and same-number blocks contextually distinct', () => {
    const shea = findWillametteSite('us-or-shea-vineyard');
    const thirdHill = shea?.blocks?.find((block) => block.block === 'Third Hill Block 2');
    const zone = shea?.zones?.find((candidate) => candidate.name === 'Third Hill');
    expect(thirdHill).toMatchObject({ zone: 'Third Hill', variety: 'Pinot Noir', clone: 'Pommard', rootstock: '101-14' });
    expect((zone?.notes as string[]) ?? []).toContain('marine sedimentary soils over a basalt outcrop');
  });

  it('preserves exact Hirschy block acreage and planting material', () => {
    const blockG = findWillametteBlocks('us-or-hirschy-vineyard', 'G')[0];
    expect(blockG).toMatchObject({ acres: 3.89, clone: '777', rootstock: '3309' });
  });

  it('does not collapse Lingua Franca Block 3 into one clone identity', () => {
    const lingua = findWillametteSite('us-or-lingua-franca-estate');
    const block3 = lingua?.blockObservations?.filter((observation) => observation.block === '3') ?? [];
    expect(new Set(block3.map((observation) => observation.clone))).toEqual(new Set(['PN777', 'PN115']));
    expect(block3.every((observation) => Boolean(observation.evidenceContext))).toBe(true);
  });

  it('turns contradictory Knudsen Block 12 producer records into an explicit data-quality issue rather than picking a winner', () => {
    const knudsen = findWillametteSite('us-or-knudsen-vineyards');
    const block12 = knudsen?.blockObservations?.filter((observation) => observation.block === '12') ?? [];
    expect(new Set(block12.map((observation) => observation.clone))).toEqual(new Set(['4407', '828']));
    expect(new Set(block12.map((observation) => observation.plantedYear))).toEqual(new Set([2012, 2010]));
    expect(knudsen?.dataQualityFlags?.some((flag) => flag.id === 'knudsen-block12-clone-planting-conflict')).toBe(true);
  });

  it('stores Knudsen wine-vintage technical chemistry separately from block identity', () => {
    const knudsen = findWillametteSite('us-or-knudsen-vineyards');
    const vintages = knudsen?.vintageTechnicalObservations as Array<Record<string, unknown>>;
    const snapshot2022 = vintages.find((record) => record.vintage === 2022 && record.wine === 'Snapshot Pinot Noir');
    expect(snapshot2022).toMatchObject({ alcoholPct: 13.8, brix: 23.3, pH: 3.69, totalAcidityGPerL: 5.5, newFrenchOakPct: 28, ageingMonths: 16 });
  });

  it('preserves graft history rather than pretending Blakeslee Block 3B was always Chardonnay', () => {
    const block3b = findWillametteBlocks('us-or-blakeslee-vineyard', '3B')[0];
    expect(block3b).toMatchObject({ variety: 'Chardonnay', clone: 'Dijon 76 & 96', rootstock: '3309', plantedYear: 1997, acres: 0.91 });
    expect(String(block3b.history)).toContain('grafted');
    expect(String(block3b.history)).toContain('2012');
  });

  it('keeps adjacent iOTA founding blocks distinct by geology despite identical Pommard/rootstock material', () => {
    const yiayia = findWillametteBlocks('us-or-iota-pelos-sandberg-vineyard', 'Yiayia')[0];
    const pappou = findWillametteBlocks('us-or-iota-pelos-sandberg-vineyard', 'Pappou')[0];
    expect(yiayia).toMatchObject({ clone: 'Pommard', rootstock: '4453M', acres: 3 });
    expect(pappou).toMatchObject({ clone: 'Pommard', rootstock: '4453M', acres: 2 });
    expect(String(yiayia.soil)).toContain('volcanic');
    expect(String(pappou.soil)).toContain('marine sedimentary');
  });
});
