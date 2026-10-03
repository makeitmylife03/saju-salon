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

STEM_KR = {'甲':'갑','乙':'을','丙':'병','丁':'정','戊':'무','己':'기','庚':'경','辛':'신','壬':'임','癸':'계'}
BRANCH_KR = {'子':'자','丑':'축','寅':'인','卯':'묘','辰':'진','巳':'사','午':'오','未':'미','申':'신','酉':'유','戌':'술','亥':'해'}
ELEMENT_HANJA = {'목':'木','화':'火','토':'土','금':'金','수':'水'}
TEN_GOD_KR = {
    '比肩':'비견', '劫财':'겁재', '食神':'식신', '伤官':'상관',
    '偏财':'편재', '正财':'정재', '偏官':'편관(칠살)', '正官':'정관',
    '偏印':'편인', '正印':'정인', '日主':'일주(日主)'
}
TEN_GOD_DESC = {
    '비견':'나와 비슷한 성향 · 독립성 · 경쟁',
    '겁재':'경쟁 · 추진력 · 관계에서의 주도권',
    '식신':'표현 · 생산성 · 여유 · 재능',
    '상관':'표현력 · 창의성 · 자유로운 사고',
    '편재':'활동성 · 사업 감각 · 유동적인 재물',
    '정재':'안정적인 재물 · 관리 · 현실감각',
    '편관(칠살)':'도전 · 책임 · 압박을 이겨내는 힘',
    '정관':'규칙 · 책임감 · 조직 · 사회적 역할',
    '편인':'직관 · 탐구 · 독특한 관심사',
    '정인':'학습 · 보호 · 안정 · 자격과 지식'
}
TWELVE_KR = {
    '长生':'장생','沐浴':'목욕','冠带':'관대','临官':'임관','帝旺':'제왕',
    '衰':'쇠','病':'병','死':'사','墓':'묘','绝':'절','胎':'태','养':'양'
}

def normalize_element(value):
    if not value:
        return ''
    for ch in value:
        if ch in ELEMENT_MAP:
            return ELEMENT_MAP[ch]
    return value

def gan_label(gan):
    return f'{STEM_KR.get(gan, gan)}({gan})'

def zhi_label(zhi):
    return f'{BRANCH_KR.get(zhi, zhi)}({zhi})'

def pillar_label(gan, zhi):
    return f'{gan_label(gan)} {zhi_label(zhi)}'

def ten_god_label(value):
    if not value:
        return ''
    kr = TEN_GOD_KR.get(value, value)
    desc = TEN_GOD_DESC.get(kr, '')
    return f'{kr} · {desc}' if desc else kr

def make_teaser(analysis):
    day = analysis['day_master_label']
    elem = analysis['day_master_element']
    strongest = max(analysis['element_counts'], key=analysis['element_counts'].get)
    weakest = min(analysis['element_counts'], key=analysis['element_counts'].get)
    day_words = {
        '목': ('성장 욕구가 강하고, 한번 방향을 잡으면 스스로 길을 만들어가려는 면','사람과 환경의 변화에 민감하게 반응하면서도 결국 자기 방식으로 정리하려는 면'),
        '화': ('표현력과 추진력이 살아 있고, 분위기를 움직이려는 면','마음이 움직이면 빠르게 행동하지만 관심이 식으면 속도가 크게 달라질 수 있는 면'),
        '토': ('현실감각과 안정감을 중요하게 보고, 쉽게 흔들리지 않으려는 면','겉으로는 차분해 보여도 책임져야 할 일이 생기면 혼자 짊어지려는 면'),
        '금': ('기준이 분명하고, 사람이나 일을 볼 때 핵심을 빠르게 잡으려는 면','대충 넘어가기보다 스스로 납득할 만한 기준을 세우려는 면'),
        '수': ('상황을 읽는 힘과 유연함이 있고, 여러 가능성을 생각하는 면','겉으로 드러내기 전에 혼자 생각을 충분히 정리하려는 면')
    }
    strongest_words = {'목':'새로운 기회나 변화가 생겼을 때 움직이려는 힘','화':'표현하고 행동으로 옮기는 힘','토':'현실적으로 안정시키고 관리하는 힘','금':'기준을 세우고 선택하는 힘','수':'정보를 모으고 상황에 맞게 움직이는 힘'}
    weak_words = {'목':'새로운 시작과 장기적인 성장','화':'표현과 실행','토':'안정과 현실적인 정리','금':'선택과 기준','수':'유연한 대응과 생각의 전환'}
    return {
        'headline': f'{day} · {elem} 기운에서 눈에 띄는 두 가지',
        'intro': f'사주 해석의 관점에서 보면, 당신은 {day_words[elem][0]}이 눈에 띕니다.',
        'cards': [
            {'title':'① 겉으로 보이는 모습과 속마음','text':f'{day_words[elem][1]}이 함께 나타날 수 있습니다. 그래서 주변에서는 당신을 한 가지 모습으로만 보기 어려울 수 있어요.','hook':'그런데 이 성향이 가까운 사람과의 관계에서는 어떻게 나타날까요?'},
            {'title':'② 돈과 일에서 반복될 수 있는 패턴','text':f'원국에서는 {strongest_words[strongest]}이 비교적 두드러집니다. 이것을 잘 활용하면 강점이 될 수 있지만, 과해질 때 나타나는 패턴도 함께 살펴볼 필요가 있습니다.','hook':'특히 돈을 벌고 쓰는 방식에서 어떤 모습으로 나타나는지는 상세 분석에서 더 구체적으로 볼 수 있어요.'},
            {'title':'③ 지금 당신에게 필요한 균형','text':f'{weak_words[weakest]}과 관련된 기운이 상대적으로 적게 나타납니다. 단순히 좋고 나쁜 문제가 아니라, 어떤 상황에서 이 부분이 약점처럼 느껴질 수 있는지를 보는 게 중요합니다.','hook':'이 부분이 직업·연애·재물운에서 어떻게 연결되는지가 핵심입니다.'}
        ],
        'question':'당신의 사주에는 왜 이런 패턴이 나타날까요?',
        'locked_points':['돈을 벌고 모으는 방식','직업·사업에서 강점이 살아나는 환경','연애와 인간관계에서 반복되는 패턴','앞으로 10년 단위 흐름에서 주목할 시기']
    }

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
            {'key':'year','label':'년주','gan':eight.getYearGan(),'zhi':eight.getYearZhi(),'pillar':eight.getYear(),'label_full':pillar_label(eight.getYearGan(), eight.getYearZhi())},
            {'key':'month','label':'월주','gan':eight.getMonthGan(),'zhi':eight.getMonthZhi(),'pillar':eight.getMonth(),'label_full':pillar_label(eight.getMonthGan(), eight.getMonthZhi())},
            {'key':'day','label':'일주','gan':eight.getDayGan(),'zhi':eight.getDayZhi(),'pillar':eight.getDay(),'label_full':pillar_label(eight.getDayGan(), eight.getDayZhi())},
            {'key':'time','label':'시주','gan':eight.getTimeGan(),'zhi':eight.getTimeZhi(),'pillar':eight.getTime(),'label_full':pillar_label(eight.getTimeGan(), eight.getTimeZhi())},
        ]

        hide_getters = [eight.getYearHideGan, eight.getMonthHideGan, eight.getDayHideGan, eight.getTimeHideGan]
        for pillar, getter in zip(pillars, hide_getters):
            pillar['hidden_stems'] = getter()
            pillar['hidden_stems_label'] = ' · '.join(gan_label(x) for x in pillar['hidden_stems'])

        wuxing_raw = {'year':eight.getYearWuXing(),'month':eight.getMonthWuXing(),'day':eight.getDayWuXing(),'time':eight.getTimeWuXing()}
        wuxing = {k: ''.join(ELEMENT_MAP.get(ch,ch) for ch in v) for k,v in wuxing_raw.items()}

        counts = {e:0 for e in ELEMENTS}
        for value in wuxing_raw.values():
            for ch in value:
                if ch in ELEMENT_MAP:
                    counts[ELEMENT_MAP[ch]] += 1

        day_master = eight.getDayGan()
        day_master_element = normalize_element(eight.getDayWuXing())

        ten_raw = {
            'year_gan':eight.getYearShiShenGan(),'month_gan':eight.getMonthShiShenGan(),'day_gan':'日主',
            'time_gan':eight.getTimeShiShenGan(),'year_zhi':eight.getYearShiShenZhi(),
            'month_zhi':eight.getMonthShiShenZhi(),'day_zhi':eight.getDayShiShenZhi(),'time_zhi':eight.getTimeShiShenZhi()
        }
        ten_gods = {
            'year_gan':ten_god_label(ten_raw['year_gan']),
            'month_gan':ten_god_label(ten_raw['month_gan']),
            'day_gan':'일주(日主)',
            'time_gan':ten_god_label(ten_raw['time_gan']),
            'year_zhi':[ten_god_label(x) for x in ten_raw['year_zhi']],
            'month_zhi':[ten_god_label(x) for x in ten_raw['month_zhi']],
            'day_zhi':[ten_god_label(x) for x in ten_raw['day_zhi']],
            'time_zhi':[ten_god_label(x) for x in ten_raw['time_zhi']]
        }

        na_yin = {'year':eight.getYearNaYin(),'month':eight.getMonthNaYin(),'day':eight.getDayNaYin(),'time':eight.getTimeNaYin()}
        twelve_raw = {'year':eight.getYearDiShi(),'month':eight.getMonthDiShi(),'day':eight.getDayDiShi(),'time':eight.getTimeDiShi()}
        twelve = {k: f'{TWELVE_KR.get(v,v)}({v})' for k,v in twelve_raw.items()}

        extra = {
            'ming_gong': eight.getMingGong(),
            'ming_gong_label': pillar_label(eight.getMingGong()[0], eight.getMingGong()[1]),
            'shen_gong': eight.getShenGong(),
            'shen_gong_label': pillar_label(eight.getShenGong()[0], eight.getShenGong()[1]),
            'tai_yuan': eight.getTaiYuan(),
            'tai_xi': eight.getTaiXi(),
            'day_xun_kong': eight.getDayXunKong(),
            'month_xun_kong': eight.getMonthXunKong()
        }

        daewoon = []
        if gender in GENDER_MAP:
            yun = eight.getYun(GENDER_MAP[gender], 1)
            for item in yun.getDaYun(9)[1:]:
                gz = item.getGanZhi()
                daewoon.append({
                    'gan_zhi':gz,
                    'gan_zhi_label':pillar_label(gz[0], gz[1]),
                    'start_year':item.getStartYear(),'end_year':item.getEndYear(),
                    'start_age':item.getStartAge(),'end_age':item.getEndAge()
                })

        strongest = max(counts,key=counts.get)
        weakest = min(counts,key=counts.get)
        names = {'목':'성장과 확장','화':'표현과 추진','토':'안정과 현실감','금':'기준과 판단','수':'유연함과 사고'}

        summary = [
            f'일간은 {gan_label(day_master)} · {day_master_element}({ELEMENT_HANJA[day_master_element]}) 기운으로, 자신의 기준과 방식이 비교적 분명한 편으로 해석합니다.',
            f'겉으로 드러난 오행은 {strongest}({ELEMENT_HANJA[strongest]}) 기운이 가장 많고, {names[strongest]}과 관련된 성향이 두드러집니다.',
            f'{weakest}({ELEMENT_HANJA[weakest]}) 기운이 상대적으로 적어 {names[weakest]}과 관련된 부분을 의식적으로 살피면 균형을 보는 데 도움이 됩니다.'
        ]

        return {
            'birth_date':birth_date,'birth_time':birth_time,'gender':gender,'pillars':pillars,
            'wuxing':wuxing,'element_counts':counts,'day_master':day_master,
            'day_master_element':day_master_element,'day_master_label':gan_label(day_master),
            'ten_gods':ten_gods,'na_yin':na_yin,'twelve':twelve,'extra':extra,
            'daewoon':daewoon,'summary':summary,'teaser':make_teaser({'day_master_label':gan_label(day_master),'day_master_element':day_master_element,'element_counts':counts})
        }

    except Exception as exc:
        print('SAJU CALC ERROR:',repr(exc))
        raise ValueError('생년월일 또는 출생시간을 확인해주세요.')

@app.context_processor
def inject_config():
    return {'supabase_url':SUPABASE_URL,'supabase_publishable_key':SUPABASE_PUBLISHABLE_KEY}

@app.route('/')
def index(): return render_template('index.html')

@app.route('/login')
def login(): return render_template('login.html')

@app.route('/saju')
def saju(): return render_template('saju_form.html')

@app.post('/saju/result')
def saju_result():
    birth_date=request.form.get('birth_date','').strip()
    birth_time=request.form.get('birth_time','').strip()
    gender=request.form.get('gender','').strip()
    try:
        analysis=calculate_saju(birth_date,birth_time,gender)
    except ValueError as exc:
        return render_template('saju_form.html',error=str(exc)),400
    reading={
        'birth_date':birth_date,'birth_time':birth_time,'gender':gender,
        'bazi':{item['key']:item['pillar'] for item in analysis['pillars']},
        'pillars':analysis['pillars'],'wuxing':analysis['wuxing'],'element_counts':analysis['element_counts'],
        'day_master':analysis['day_master'],'day_master_element':analysis['day_master_element'],
        'day_master_label':analysis['day_master_label'],'ten_gods':analysis['ten_gods'],
        'na_yin':analysis['na_yin'],'twelve':analysis['twelve'],'extra':analysis['extra'],'daewoon':analysis['daewoon']
    }
    return render_template('saju_result.html',reading=reading,reading_id=None,summary=analysis['summary'],paid=False,fresh=True)

@app.route('/saju/result/<reading_id>')
def saved_saju_result(reading_id):
    return render_template('saju_result.html',reading={},reading_id=reading_id,summary=[],paid=False,fresh=False)

@app.get('/checkout/<reading_id>')
def checkout(reading_id):
    return render_template('checkout.html',reading_id=reading_id,product=PRODUCTS['saju_detail'])

@app.route('/my')
def my_page(): return render_template('my.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=int(os.getenv('PORT',5000)),debug=True)
