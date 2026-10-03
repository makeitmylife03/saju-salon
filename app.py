import os
from flask import Flask, render_template, request
from lunar_python import Solar

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-change-me')

SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://bjjqpmkvtmnecekdnzbf.supabase.co')
SUPABASE_PUBLISHABLE_KEY = os.getenv('SUPABASE_PUBLISHABLE_KEY', '')

PRODUCTS = {'saju_detail': {'name': '종합 사주 상세 리포트', 'amount': 9900}}

ELEMENTS = ('목', '화', '토', '금', '수')
ELEMENT_MAP = {'木': '목', '火': '화', '土': '토', '金': '금', '水': '수'}
GENDER_MAP = {'male': 1, 'female': 0}


def normalize_element(value):
    if not value:
        return ''
    for ch in value:
        if ch in ELEMENT_MAP:
            return ELEMENT_MAP[ch]
    return value


def calculate_saju(birth_date, birth_time, gender):
    if not birth_date:
        raise ValueError('생년월일을 입력해주세요.')

    try:
        year, month, day = [int(x) for x in birth_date.split('-')]
        hour, minute = (12, 0)
        if birth_time:
            hour, minute = [int(x) for x in birth_time.split(':')]

        solar = Solar.fromYmdHms(year, month, day, hour, minute, 0)
        eight = solar.getLunar().getEightChar()

        pillars = [
            {'key': 'year', 'label': '년주', 'gan': eight.getYearGan(), 'zhi': eight.getYearZhi(), 'pillar': eight.getYear()},
            {'key': 'month', 'label': '월주', 'gan': eight.getMonthGan(), 'zhi': eight.getMonthZhi(), 'pillar': eight.getMonth()},
            {'key': 'day', 'label': '일주', 'gan': eight.getDayGan(), 'zhi': eight.getDayZhi(), 'pillar': eight.getDay()},
            {'key': 'time', 'label': '시주', 'gan': eight.getTimeGan(), 'zhi': eight.getTimeZhi(), 'pillar': eight.getTime()},
        ]

        hide_getters = [
            eight.getYearHideGan,
            eight.getMonthHideGan,
            eight.getDayHideGan,
            eight.getTimeHideGan,
        ]
        for pillar, getter in zip(pillars, hide_getters):
            pillar['hidden_stems'] = getter()

        wuxing_raw = {
            'year': eight.getYearWuXing(),
            'month': eight.getMonthWuXing(),
            'day': eight.getDayWuXing(),
            'time': eight.getTimeWuXing(),
        }
        wuxing = {
            key: ''.join(ELEMENT_MAP.get(ch, ch) for ch in value)
            for key, value in wuxing_raw.items()
        }

        counts = {e: 0 for e in ELEMENTS}
        for value in wuxing_raw.values():
            for ch in value:
                if ch in ELEMENT_MAP:
                    counts[ELEMENT_MAP[ch]] += 1

        day_master = eight.getDayGan()
        day_master_element = normalize_element(eight.getDayWuXing())

        ten_gods = {
            'year_gan': eight.getYearShiShenGan(),
            'month_gan': eight.getMonthShiShenGan(),
            'day_gan': '일주(日主)',
            'time_gan': eight.getTimeShiShenGan(),
            'year_zhi': eight.getYearShiShenZhi(),
            'month_zhi': eight.getMonthShiShenZhi(),
            'day_zhi': eight.getDayShiShenZhi(),
            'time_zhi': eight.getTimeShiShenZhi(),
        }

        na_yin = {
            'year': eight.getYearNaYin(),
            'month': eight.getMonthNaYin(),
            'day': eight.getDayNaYin(),
            'time': eight.getTimeNaYin(),
        }

        twelve = {
            'year': eight.getYearDiShi(),
            'month': eight.getMonthDiShi(),
            'day': eight.getDayDiShi(),
            'time': eight.getTimeDiShi(),
        }

        extra = {
            'ming_gong': eight.getMingGong(),
            'shen_gong': eight.getShenGong(),
            'tai_yuan': eight.getTaiYuan(),
            'tai_xi': eight.getTaiXi(),
            'day_xun_kong': eight.getDayXunKong(),
            'month_xun_kong': eight.getMonthXunKong(),
        }

        daewoon = []
        if gender in GENDER_MAP:
            yun = eight.getYun(GENDER_MAP[gender], 1)
            for item in yun.getDaYun(9)[1:]:
                daewoon.append({
                    'gan_zhi': item.getGanZhi(),
                    'start_year': item.getStartYear(),
                    'end_year': item.getEndYear(),
                    'start_age': item.getStartAge(),
                    'end_age': item.getEndAge(),
                })

        strongest = max(counts, key=counts.get)
        weakest = min(counts, key=counts.get)
        names = {
            '목': '성장과 확장',
            '화': '표현과 추진',
            '토': '안정과 현실감',
            '금': '기준과 판단',
            '수': '유연함과 사고'
        }

        summary = [
            f'일간은 {day_master}({day_master_element})으로, 자신의 기준과 방식이 비교적 분명한 편으로 해석합니다.',
            f'겉으로 드러난 오행은 {strongest} 기운이 가장 많고, {names[strongest]}과 관련된 성향이 두드러집니다.',
            f'{weakest} 기운이 상대적으로 적어 {names[weakest]}과 관련된 부분을 의식적으로 살피면 균형을 보는 데 도움이 됩니다.'
        ]

        return {
            'birth_date': birth_date,
            'birth_time': birth_time,
            'gender': gender,
            'pillars': pillars,
            'wuxing': wuxing,
            'element_counts': counts,
            'day_master': day_master,
            'day_master_element': day_master_element,
            'ten_gods': ten_gods,
            'na_yin': na_yin,
            'twelve': twelve,
            'extra': extra,
            'daewoon': daewoon,
            'summary': summary,
        }

    except Exception as exc:
        print('SAJU CALC ERROR:', repr(exc))
        raise ValueError('생년월일 또는 출생시간을 확인해주세요.')


@app.context_processor
def inject_config():
    return {
        'supabase_url': SUPABASE_URL,
        'supabase_publishable_key': SUPABASE_PUBLISHABLE_KEY
    }


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/saju')
def saju():
    return render_template('saju_form.html')


@app.post('/saju/result')
def saju_result():
    birth_date = request.form.get('birth_date', '').strip()
    birth_time = request.form.get('birth_time', '').strip()
    gender = request.form.get('gender', '').strip()

    try:
        analysis = calculate_saju(birth_date, birth_time, gender)
    except ValueError as exc:
        return render_template('saju_form.html', error=str(exc)), 400

    reading = {
        'birth_date': birth_date,
        'birth_time': birth_time,
        'gender': gender,
        'bazi': {item['key']: item['pillar'] for item in analysis['pillars']},
        'pillars': analysis['pillars'],
        'wuxing': analysis['wuxing'],
        'element_counts': analysis['element_counts'],
        'day_master': analysis['day_master'],
        'day_master_element': analysis['day_master_element'],
        'ten_gods': analysis['ten_gods'],
        'na_yin': analysis['na_yin'],
        'twelve': analysis['twelve'],
        'extra': analysis['extra'],
        'daewoon': analysis['daewoon'],
    }

    return render_template(
        'saju_result.html',
        reading=reading,
        reading_id=None,
        summary=analysis['summary'],
        paid=False,
        fresh=True
    )


@app.route('/saju/result/<reading_id>')
def saved_saju_result(reading_id):
    return render_template(
        'saju_result.html',
        reading={},
        reading_id=reading_id,
        summary=[],
        paid=False,
        fresh=False
    )


@app.get('/checkout/<reading_id>')
def checkout(reading_id):
    return render_template(
        'checkout.html',
        reading_id=reading_id,
        product=PRODUCTS['saju_detail']
    )


@app.route('/my')
def my_page():
    return render_template('my.html')


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=True
    )
