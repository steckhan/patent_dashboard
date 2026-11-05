import sys
import tempfile
import unittest
from pathlib import Path

from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from data_utils import load_orbit_fampat_data, load_patent_data


class OrbitSourceTests(unittest.TestCase):
    def test_combined_sources(self):
        data = load_patent_data()
        families = data[data['source'] == 'Orbit/FAMPAT']
        self.assertFalse(families.empty)
        self.assertTrue(families['record_level'].eq('Patent Family').all())
        self.assertTrue(families['patent_id'].notna().all())
        self.assertIn('Google Patents', set(data['source']))

    def test_links_remain_aligned_when_a_row_has_no_number(self):
        source = Path(__file__).resolve().parents[1] / 'data' / 'Anlage 1 - KI im Arbeitsschutz_Ergebnisse.xlsx'
        workbook = load_workbook(source)
        sheet = workbook['Patentfamilie']
        sheet['B4'] = None
        sheet['C5'].hyperlink = 'https://example.org/second'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'source.xlsx'
            workbook.save(path)
            workbook.close()
            families = load_orbit_fampat_data(path)
        self.assertEqual(families.iloc[0]['url'], 'https://example.org/second')


if __name__ == '__main__':
    unittest.main()
