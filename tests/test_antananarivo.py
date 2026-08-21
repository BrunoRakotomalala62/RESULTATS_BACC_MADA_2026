import unittest

from api import antananarivo


class FakeResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            error = antananarivo.requests.HTTPError(response=self)
            raise error


class FakeSession:
    def __init__(self, page_html, script_text=""):
        self.page_html = page_html
        self.script_text = script_text
        self.urls = []

    def get(self, url, timeout=None):
        self.urls.append(url)
        if url == antananarivo.SOURCE_URL:
            return FakeResponse(self.page_html)
        return FakeResponse(self.script_text)


class AntananarivoScraperTests(unittest.TestCase):
    def setUp(self):
        antananarivo.clear_cache()

    def test_parse_embedded_json_results(self):
        script = (
            'const Qm=[{"annee":"2026","matricule":"1420000",'
            '"nom":"RAKOTO","prenoms":"Miora","observation":"VRAI",'
            '"mention":"Bien","serie":"A2"}];'
        )
        parsed = antananarivo.parse_embedded_results(script)
        self.assertEqual(parsed[0]["matricule"], "1420000")
        self.assertEqual(parsed[0]["observation"], "VRAI")

    def test_parse_embedded_javascript_objects(self):
        script = (
            "const data=[{annee:'2025',matricule:'123',nom:'RABE',"
            "prenoms:'Lala',observation:'FAUX',mention:null,serie:'C'}];"
        )
        parsed = antananarivo.parse_embedded_results(script)
        self.assertEqual(parsed[0]["nom"], "RABE")
        self.assertIsNone(parsed[0]["mention"])

    def test_parse_html_results(self):
        html = """
        <table><thead><tr><th>Numéro d'inscription</th><th>Nom</th>
        <th>Prénoms</th><th>Observation</th><th>Mention</th><th>Série</th></tr></thead>
        <tbody><tr><td>1420000</td><td>RAKOTO</td><td>Miora</td>
        <td>VRAI</td><td>Bien</td><td>A2</td></tr></tbody></table>
        """
        results = antananarivo.parse_html_results(html)
        normalized = antananarivo.normalize_result(results[0])
        self.assertEqual(normalized["matricule"], "1420000")
        self.assertEqual(normalized["fullname"], "RAKOTO Miora")
        self.assertEqual(normalized["admis"], 1)
        self.assertEqual(normalized["serie"], "A2")

    def test_scrape_and_filter_by_name(self):
        page = '<html><head><script src="/assets/app.js"></script></head></html>'
        script = (
            'const Qm=[{"annee":"2026","matricule":"1420000",'
            '"nom":"RAKOTO","prenoms":"Miora","observation":"VRAI"}];'
        )
        session = FakeSession(page, script)
        result = antananarivo.search_results(session, "miora", "nom", "2026")
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["results"][0]["matricule"], "1420000")
        self.assertEqual(session.urls, [antananarivo.SOURCE_URL, "https://www.univ-antananarivo.mg/assets/app.js"])

    def test_scrape_and_filter_by_matricule(self):
        page = '<html><head><script src="/assets/app.js"></script></head></html>'
        script = (
            'const Qm=[{"annee":"2025","matricule":"123",'
            '"nom":"RABE","prenoms":"Lala","observation":"FAUX"}];'
        )
        result = antananarivo.search_results(FakeSession(page, script), "123", "matricule", "2025")
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["results"][0]["admis"], 0)


if __name__ == "__main__":
    unittest.main()
