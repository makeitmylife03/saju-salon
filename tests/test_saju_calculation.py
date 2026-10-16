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

    def test_date_and_time_format_must_be_canonical(self):
        for birth_date, birth_time in [
            ('1990-5-17', '14:30'),
            ('1990-05-17', '2:30'),
            ('1990-05-17', '14:3'),
        ]:
            with self.subTest(birth_date=birth_date, birth_time=birth_time):
                with self.assertRaises(ValueError):
                    calculate_saju(birth_date, birth_time, 'male')

    def test_unselected_gender_does_not_generate_daewoon(self):
        result = calculate_saju('1990-05-17', '14:30', 'other')
        self.assertEqual(result['daewoon'], [])

    def test_daewoon_ranges_are_ordered_and_non_overlapping(self):
        result = calculate_saju('1990-05-17', '14:30', 'male')
        periods = result['daewoon']
        self.assertTrue(periods)
        for period in periods:
            self.assertLessEqual(period['start_year'], period['end_year'])
            self.assertLessEqual(period['start_age'], period['end_age'])
        for previous, current in zip(periods, periods[1:]):
            self.assertLessEqual(previous['start_year'], current['start_year'])
            self.assertLessEqual(previous['start_age'], current['start_age'])

    def test_invalid_date_and_time_have_specific_messages(self):
        cases = [
            ('1990-02-30', '14:30', '생년월일을 올바른 날짜로 입력해주세요.'),
            ('1990-05-17', '25:00', '출생시간을 올바르게 입력해주세요.'),
            ('1990-5-17', '14:30', '생년월일 형식이 올바르지 않습니다.'),
            ('1990-05-17', '2:30', '출생시간 형식이 올바르지 않습니다.'),
        ]
        for birth_date, birth_time, expected in cases:
            with self.subTest(birth_date=birth_date, birth_time=birth_time):
                with self.assertRaisesRegex(ValueError, expected):
                    calculate_saju(birth_date, birth_time, 'male')

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

    def test_invalid_form_input_shows_specific_validation_message(self):
        from app import app

        client = app.test_client()
        response = client.post('/saju/result', data={
            'birth_date': '1990-05-17',
            'birth_time': '2:30',
            'gender': 'male',
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn('출생시간 형식이 올바르지 않습니다.'.encode(), response.data)

    def test_invalid_form_input_returns_validation_error(self):
        from app import app

        client = app.test_client()
        response = client.post('/saju/result', data={
            'birth_date': '1990-02-30',
            'birth_time': '14:30',
            'gender': 'male',
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn('생년월일을 올바른 날짜로 입력해주세요.'.encode(), response.data)

    def test_missing_birth_time_is_recorded_as_unknown(self):
        result = calculate_saju('1990-05-17', '', 'female')
        self.assertEqual(result['birth_time'], '')
        self.assertEqual(len(result['pillars']), 4)
        report = make_detailed_report(result)
        self.assertIn('출생시간을 입력하지 않아 정오를 임시 기준으로 계산했습니다', report['내 사주의 구조'])

    def test_report_explains_daewoon_omission_when_gender_not_selected(self):
        analysis = {
            'day_master_element': '수',
            'element_counts': {'목': 1, '화': 1, '토': 2, '금': 2, '수': 2},
            'day_master_label': '임(壬)',
            'birth_date': '1990-05-17',
            'birth_time': '',
            'gender': 'other',
            'daewoon': [],
            'pillars': [],
        }
        report = make_detailed_report(analysis)
        self.assertIn('성별 정보를 선택하지 않아 대운', report['대운과 시기'])

    def test_report_uses_current_year_for_daewoon_range(self):
        year = date.today().year
        analysis = {
            'day_master_element': '수',
            'element_counts': {'목': 1, '화': 1, '토': 2, '금': 2, '수': 2},
            'day_master_label': '임(壬)',
            'birth_date': '1990-05-17',
            'birth_time': '14:30',
            'gender': 'male',
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
