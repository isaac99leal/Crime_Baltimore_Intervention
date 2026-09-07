import unittest
from types import SimpleNamespace as NS
from scripts.reconcile_astra_handoff import site_mapping


class ReconciliationSourceBindingTests(unittest.TestCase):
    def test_partial_source_match_cannot_claim_a_binding(self):
        site = NS(id='site', country='France', parent='Rully', classification='Premier Cru',
                  name='Example', site_type='climat', legal_status='verified', source_ids=('a',))
        rule = NS(id='rule', parent_appellation='Rully', country='France', site_type='climat',
                  required_site_legal_status='verified', required_site_source_ids=('a', 'b'),
                  allowed_site_names=(), excluded_site_names=(), allowed_wine_variants=('white',))
        catalog, claims = NS(named_sites=[site]), NS(rules=[rule])
        self.assertEqual(site_mapping(catalog, claims, 'Rully', 'Example')['structural_claim_bindings'], [])
        site.source_ids = ('a', 'b')
        self.assertEqual(len(site_mapping(catalog, claims, 'Rully', 'Example')['structural_claim_bindings']), 1)
