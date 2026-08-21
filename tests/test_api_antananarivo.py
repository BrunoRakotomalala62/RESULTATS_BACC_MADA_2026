import unittest
from unittest.mock import patch

from api import index


class ApiAntananarivoTests(unittest.TestCase):
    def setUp(self):
        self.client = index.app.test_client()

    def test_province_is_available(self):
        response = self.client.get('/api/bacc/provinces')
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        antananarivo = next(item for item in payload['provinces'] if item['code'] == 'antananarivo')
        self.assertTrue(antananarivo['disponible'])
        self.assertIn('univ-antananarivo.mg/resultats-bac', antananarivo['api'])

    @patch('api.index.search_antananarivo_results')
    def test_search_route_keeps_common_contract(self, search_mock):
        search_mock.return_value = {
            'status': 'OK',
            'province': 'antananarivo',
            'mode': 'nom',
            'search_term': 'RAKOTO',
            'annee': '2026',
            'count': 1,
            'results': [{
                'matricule': '1420000',
                'fullname': 'RAKOTO Miora',
                'nom': 'RAKOTO',
                'prenoms': 'Miora',
                'annee': '2026',
                'admis': 1,
                'admis_label': 'Admis(e)',
            }],
        }
        response = self.client.get('/api/bacc/recherche?nom=RAKOTO&province=antananarivo&annee=2026&per_page=10')
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload['results'][0]['matricule'], '1420000')
        self.assertEqual(payload['pagination']['total'], 1)
        search_mock.assert_called_once_with(index.session, 'RAKOTO', 'nom', '2026')


if __name__ == '__main__':
    unittest.main()
