import { describe, expect, it } from 'vitest';
import {
  findWillametteBlocks,
  findWillametteSite,
  validateWillametteMicroSites,
  willametteMicroSiteCount,
  willametteNamedBlockCount,
  willametteSubSiteObservationCount,
} from './willametteMicroSites';

describe('Willamette vineyard micro-site research', () => {
  it('locks a granular but source-bounded vineyard/block library', () => {
    const report = validateWillametteMicroSites();
    expect(willametteMicroSiteCount).toBe(8);
    expect(willametteNamedBlockCount).toBeGreaterThanOrEqual(41);
    expect(willametteSubSiteObservationCount).toBeGreaterThanOrEqual(60);
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
});
