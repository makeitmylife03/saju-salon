import unittest
from datetime import date

from app import calculate_saju, make_detailed_report


class SajuCalculationTests(unittest.TestCase):
    def test_calculation_returns_four_pillars_and_eight_visible_elements(self):
        result = calculate_saju('1990-05-17', '14:30', 'male')
        self.assertEqual(len(result['pillars']), 4)
        self.assertEqual(set(result['element_counts']), {'목', '화', '토', '금', '수'})
        self.assertEqual(sum(result['element_counts'].values()), 8)
        self.assertTrue(result['day_master_label'])

    def test_multiple_birth_dates_produce_valid_four_pillars(self):
        for birth_date, birth_time, gender in [
            ('1988-02-29', '00:05', 'male'),
            ('2000-01-01', '23:55', 'female'),
            ('2024-02-29', '12:00', 'male'),
        ]:
            with self.subTest(birth_date=birth_date, birth_time=birth_time):
                result = calculate_saju(birth_date, birth_time, gender)
                self.assertEqual(len(result['pillars']), 4)
                self.assertEqual(sum(result['element_counts'].values()), 8)

    def test_invalid_birth_date_and_time_are_rejected(self):
        for birth_date, birth_time in [
            ('1990-02-30', '14:30'),
            ('1990-13-01', '14:30'),
            ('1990-05-17', '25:00'),
            ('1990-05-17', '12:99'),
        ]:
            with self.subTest(birth_date=birth_date, birth_time=birth_time):
                with self.assertRaises(ValueError):
                    calculate_saju(birth_date, birth_time, 'male')

    def test_missing_birth_time_is_recorded_as_unknown(self):
        result = calculate_saju('1990-05-17', '', 'female')
        self.assertEqual(result['birth_time'], '')
        self.assertEqual(len(result['pillars']), 4)
        report = make_detailed_report(result)
        self.assertIn('출생시간을 입력하지 않아 정오를 임시 기준으로 계산했습니다', report['내 사주의 구조'])

    def test_report_uses_current_year_for_daewoon_range(self):
        year = date.today().year
        analysis = {
            'day_master_element': '수',
            'element_counts': {'목': 1, '화': 1, '토': 2, '금': 2, '수': 2},
            'day_master_label': '임(壬)',
            'birth_date': '1990-05-17',
            'birth_time': '14:30',
            'daewoon': [{
                'gan_zhi_label': '갑자',
                'start_age': 1,
                'end_age': 10,
                'start_year': year,
                'end_year': year,
            }],
            'pillars': [],
        }
        report = make_detailed_report(analysis)
        self.assertIn('갑자 대운', report['대운과 시기'])


if __name__ == '__main__':
    unittest.main()
