import os
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-change-me')

SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://bjjqpmkvtmnecekdnzbf.supabase.co')
SUPABASE_PUBLISHABLE_KEY = os.getenv('SUPABASE_PUBLISHABLE_KEY', '')

PRODUCTS = {'saju_detail': {'name': '종합 사주 상세 리포트', 'amount': 9900}}

FREE_SUMMARY = [
    '신중하게 관찰한 뒤 움직이는 편이며, 한번 결정한 일에는 꾸준함이 있습니다.',
    '사람을 대할 때 신뢰와 안정감을 중요하게 생각하고 가까운 관계에 깊게 마음을 쓰는 성향입니다.',
    '변화가 필요할 때도 무작정 뛰어들기보다 현실적인 조건을 확인한 뒤 선택하는 타입입니다.'
]

@app.context_processor
def inject_config():
    return {
        'supabase_url': SUPABASE_URL,
        'supabase_publishable_key': SUPABASE_PUBLISHABLE_KEY,
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
    data = {
        'birth_date': request.form.get('birth_date', ''),
        'birth_time': request.form.get('birth_time', ''),
        'gender': request.form.get('gender', ''),
    }
    return render_template(
        'saju_result.html',
        reading=data,
        reading_id=None,
        summary=FREE_SUMMARY,
        paid=False,
        fresh=True,
    )

@app.route('/saju/result/<reading_id>')
def saved_saju_result(reading_id):
    return render_template(
        'saju_result.html',
        reading={},
        reading_id=reading_id,
        summary=[],
        paid=False,
        fresh=False,
    )

@app.get('/checkout/<reading_id>')
def checkout(reading_id):
    return render_template('checkout.html', reading_id=reading_id, product=PRODUCTS['saju_detail'])

@app.route('/my')
def my_page():
    return render_template('my.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=True)
