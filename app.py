import os
from flask import Flask, render_template, request
from lunar_python import Solar

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-change-me')

SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://bjjqpmkvtmnecekdnzbf.supabase.co')
SUPABASE_PUBLISHABLE_KEY = os.getenv('SUPABASE_PUBLISHABLE_KEY', '')

PRODUCTS = {'saju_detail': {'name': '종합 사주 상세 리포트', 'amount': 9900}}
ELEMENTS = ('목', '화', '토', '금', '수')

def calculate_saju(birth_date, birth_time):
    if not birth_date:
        raise ValueError('생년월일을 입력해주세요.')
    try:
        year, month, day = [int(x) for x in birth_date.split('-')]
        hour, minute = (12, 0)
        if birth_time:
            hour, minute = [int(x) for x in birth_time.split(':')]
        solar = Solar.fromYmdHms(year, month, day, hour, minute, 0)
        eight = solar.getLunar().getEightChar()
        pillars = {
            'year': eight.getYear(),
            'month': eight.getMonth(),
            'day': eight.getDay(),
            'time': eight.getTime(),
        }
        wuxing = {
            'year': eight.getYearWuXing(),
            'month': eight.getMonthWuXing(),
            'day': eight.getDayWuXing(),
            'time': eight.getTimeWuXing(),
        }
        counts = {e: 0 for e in ELEMENTS}
        for value in wuxing.values():
            for e in ELEMENTS:
                counts[e] += value.count(e)
        day_master = eight.getDayGan()
        day_master_element = eight.getDayWuXing()[0]
        strongest = max(counts, key=counts.get)
        weakest = min(counts, key=counts.get)
        names = {'목':'성장과 확장','화':'표현과 추진','토':'안정과 현실감','금':'기준과 판단','수':'유연함과 사고'}
        summary = [
            f'일간은 {day_master}({day_master_element})으로, 자신의 기준과 방식이 비교적 분명한 편으로 해석할 수 있습니다.',
            f'원국에서는 {names[strongest]} 성향을 나타내는 {strongest} 기운이 상대적으로 두드러집니다.',
            f'{weakest} 기운이 상대적으로 적어 {names[weakest]}과 관련된 부분을 의식적으로 살피면 균형을 보는 데 도움이 됩니다.'
        ]
        return pillars, wuxing, counts, day_master, day_master_element, summary
    except Exception as exc:
        print('SAJU CALC ERROR:', repr(exc))
        raise ValueError('생년월일 또는 출생시간을 확인해주세요.')

@app.context_processor
def inject_config():
    return {'supabase_url': SUPABASE_URL, 'supabase_publishable_key': SUPABASE_PUBLISHABLE_KEY}

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
        pillars, wuxing, counts, day_master, day_master_element, summary = calculate_saju(birth_date, birth_time)
    except ValueError as exc:
        return render_template('saju_form.html', error=str(exc)), 400
    reading = {
        'birth_date': birth_date,
        'birth_time': birth_time,
        'gender': gender,
        'bazi': pillars,
        'wuxing': wuxing,
        'element_counts': counts,
        'day_master': day_master,
        'day_master_element': day_master_element,
    }
    return render_template('saju_result.html', reading=reading, reading_id=None, summary=summary, paid=False, fresh=True)

@app.route('/saju/result/<reading_id>')
def saved_saju_result(reading_id):
    return render_template('saju_result.html', reading={}, reading_id=reading_id, summary=[], paid=False, fresh=False)

@app.get('/checkout/<reading_id>')
def checkout(reading_id):
    return render_template('checkout.html', reading_id=reading_id, product=PRODUCTS['saju_detail'])

@app.route('/my')
def my_page():
    return render_template('my.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=True)
