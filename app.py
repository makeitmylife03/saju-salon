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
    elem = analysis['day_master_element']
    strongest = max(analysis['element_counts'], key=analysis['element_counts'].get)
    weakest = min(analysis['element_counts'], key=analysis['element_counts'].get)

    profiles = {
        '목': {
            'headline':'새로운 길이 보이면, 결국 직접 움직이는 사람',
            'intro':'사주 해석에서는 성장하려는 마음과 자기 방식대로 길을 만들어가려는 성향이 함께 나타나는 타입으로 읽습니다.',
            'inner':'겉으로는 괜찮아 보여도 마음속에서는 “이대로 가도 될까?”를 계속 생각할 수 있습니다.',
            'hook1':'그런데 이 성향이 사람을 만날 때는 전혀 다른 모습으로 나타날 수 있어요.',
        },
        '화': {
            'headline':'마음이 움직이면, 생각보다 빠르게 행동하는 사람',
            'intro':'사주 해석에서는 표현력과 추진력이 중요한 특징으로 읽히며, 관심이 생긴 일에는 에너지가 빠르게 모이는 편입니다.',
            'inner':'반대로 마음이 식은 일에는 억지로 힘을 쓰기보다 자연스럽게 거리를 두려는 모습도 나타날 수 있습니다.',
            'hook1':'그런데 이 성향이 돈과 일에서는 어떤 선택으로 이어질까요?',
        },
        '토': {
            'headline':'남들이 보는 것보다, 책임을 더 많이 짊어지는 사람',
            'intro':'사주 해석에서는 현실감각과 안정감을 중요하게 여기고, 쉽게 흔들리지 않으려는 성향이 눈에 띕니다.',
            'inner':'겉으로는 차분해 보여도 책임져야 할 일이 생기면 혼자 해결하려는 쪽으로 기울 수 있습니다.',
            'hook1':'그런데 이 성향이 오히려 돈과 인간관계에서는 부담이 될 때가 있습니다.',
        },
        '금': {
            'headline':'아무거나 선택하기보다, 납득이 되어야 움직이는 사람',
            'intro':'사주 해석에서는 기준과 판단이 비교적 분명하고, 사람이나 상황의 핵심을 빠르게 잡으려는 성향이 나타납니다.',
            'inner':'그래서 남들은 결단력이 있다고 보지만, 실제로는 스스로 납득할 때까지 오래 고민하는 경우도 있을 수 있습니다.',
            'hook1':'그런데 이 기준이 연애와 돈 문제에서는 어떤 차이를 만들까요?',
        },
        '수': {
            'headline':'겉으로는 차분한데, 머릿속에서는 계속 생각하는 사람',
            'intro':'사주 해석에서는 상황을 읽고 여러 가능성을 생각하는 유연한 성향이 눈에 띕니다.',
            'inner':'바로 결정하기보다 한 번 더 생각하고, 상대의 말이나 분위기를 혼자 정리한 뒤 움직이는 모습이 나타날 수 있습니다.',
            'hook1':'그런데 이 성향이 가까운 관계에서는 의외의 패턴으로 나타날 수 있어요.',
        }
    }
    p = profiles[elem]
    strongest_words = {
        '목':'새로운 기회가 생겼을 때 움직이고 확장하려는 힘',
        '화':'생각한 것을 표현하고 행동으로 옮기는 힘',
        '토':'현실적인 문제를 정리하고 안정시키는 힘',
        '금':'기준을 세우고 중요한 것을 골라내는 힘',
        '수':'정보를 모으고 상황에 맞게 방향을 바꾸는 힘'
    }
    weak_words = {
        '목':'새로운 시작과 장기적인 성장',
        '화':'표현과 실행',
        '토':'안정과 현실적인 정리',
        '금':'선택과 기준',
        '수':'유연한 대응과 생각의 전환'
    }
    return {
        'headline':p['headline'],
        'intro':p['intro'],
        'cards':[
            {'title':'겉으로 보이는 모습과 실제 속마음','text':p['inner'],'hook':p['hook1']},
            {'title':'돈과 일에서 눈여겨볼 부분', 'text':f'현재 원국에서는 {strongest_words[strongest]}이 비교적 두드러집니다. 이 힘이 잘 쓰일 때와 과해질 때의 차이가 중요합니다.', 'hook':'상세 리포트에서는 이 특징이 실제 돈과 일의 선택에서 어떻게 나타나는지 더 구체적으로 풀어드립니다.'},
            {'title':'당신에게 필요한 균형', 'text':f'{weak_words[weakest]}과 관련된 부분이 상대적으로 약하게 나타납니다. 좋고 나쁨의 문제가 아니라, 어떤 상황에서 이 차이가 크게 느껴지는지를 보는 것이 핵심입니다.', 'hook':'특히 이 부분이 직업·연애·재물의 흐름에서 어떻게 연결되는지는 무료 결과만으로는 다 보여드리기 어렵습니다.'}
        ],
        'question':'그렇다면 나는 왜 이런 선택과 관계 패턴을 반복하게 될까요?',
        'locked_points':['돈을 벌고 모으는 방식과 새기 쉬운 지점','직장·사업에서 강점이 살아나는 환경','연애와 인간관계에서 반복되기 쉬운 패턴','앞으로의 큰 흐름과 주목해서 볼 시기']
    }

def make_detailed_report(analysis):
    elem = analysis['day_master_element']
    strongest = max(analysis['element_counts'], key=analysis['element_counts'].get)
    weakest = min(analysis['element_counts'], key=analysis['element_counts'].get)
    day = analysis['day_master_label']

    personality = {
        '목':'새로운 가능성을 보면 스스로 방향을 만들어가려는 성향이 있습니다. 다만 마음속에서 다음 선택지를 여러 번 검토한 뒤 움직이기 때문에 겉에서 보는 것보다 결정까지 시간이 걸릴 수 있습니다.',
        '화':'관심이 생긴 일에는 에너지가 빠르게 모이고 표현과 행동으로 옮기려는 성향이 있습니다. 반대로 의미가 없다고 느끼는 일에는 에너지가 급격히 떨어질 수 있어 동기 관리가 중요합니다.',
        '토':'현실적인 조건과 책임을 중요하게 생각하는 성향이 있습니다. 주변에서는 안정적인 사람으로 볼 수 있지만, 책임을 혼자 떠안으면 피로가 누적되기 쉬운 면도 함께 살펴볼 필요가 있습니다.',
        '금':'기준과 판단이 비교적 분명한 편입니다. 쉽게 타협하기보다 스스로 납득할 수 있는 기준을 찾은 뒤 움직이려는 경향이 있어 중요한 선택에서는 신중함이 강점이 될 수 있습니다.',
        '수':'상황과 사람의 분위기를 읽고 여러 가능성을 생각하는 유연한 성향이 있습니다. 다만 생각할 수 있는 경우의 수가 많아질수록 결정을 미루거나 혼자 고민하는 패턴으로 이어질 수 있습니다.'
    }
    money = {
        '목':'돈을 단순히 모으는 것보다 새로운 기회와 성장에 연결하려는 성향을 살펴볼 필요가 있습니다. 확장할 때는 속도가 장점이지만, 계획보다 앞서가면 지출이 커질 수 있습니다.',
        '화':'돈을 쓰는 목적과 만족감이 분명할 때 지출이 커질 수 있습니다. 반대로 자신이 납득하는 목표가 생기면 추진력 있게 수입을 늘리는 방향으로 움직이기 쉬운 편입니다.',
        '토':'안정적인 현금흐름과 관리가 중요한 편입니다. 큰 한 번의 기회보다 꾸준히 남기는 구조를 만들었을 때 장점이 살아날 수 있습니다.',
        '금':'돈을 쓸 때도 기준과 효율을 따지는 편이지만, 한 번 필요하다고 판단하면 과감해질 수 있습니다. 계약·투자·사업에서는 숫자와 조건을 직접 확인하는 습관이 중요합니다.',
        '수':'정보와 타이밍을 읽는 능력을 활용해 돈을 만드는 방식이 잘 맞을 수 있습니다. 다만 너무 많은 선택지를 동시에 검토하면 좋은 기회를 늦게 잡는 패턴이 생길 수 있습니다.'
    }
    work = {
        '목':'정체된 환경보다 성장하고 변화할 여지가 있는 환경에서 동력이 살아날 가능성이 있습니다.',
        '화':'사람에게 영향을 주거나 직접 결과를 만들어내는 업무에서 추진력이 살아날 가능성이 있습니다.',
        '토':'운영·관리·책임이 필요한 환경에서 꾸준함과 현실감각을 활용하기 좋습니다.',
        '금':'기준을 세우고 문제를 정리하거나 품질을 관리하는 역할에서 강점을 활용하기 좋습니다.',
        '수':'정보를 다루고 상황에 따라 전략을 바꾸는 업무에서 유연함을 활용하기 좋습니다.'
    }
    relationship = {
        '목':'관계에서도 함께 성장할 수 있다는 느낌이 중요할 수 있습니다. 답답한 관계가 길어지면 마음이 먼저 멀어질 수 있습니다.',
        '화':'마음이 생기면 표현이 빠른 편일 수 있지만, 감정의 온도 차이가 생기면 상대가 변화를 크게 느낄 수 있습니다.',
        '토':'관계에서 책임감이 강해 상대의 문제까지 자신의 몫처럼 받아들이기 쉬울 수 있습니다.',
        '금':'상대에게도 일정한 기준과 약속을 기대하는 편일 수 있어 애매한 관계보다 명확한 관계에서 편안함을 느낄 가능성이 있습니다.',
        '수':'상대의 말과 분위기를 많이 읽는 편이라 작은 변화도 크게 받아들일 수 있습니다. 혼자 추측하기보다 확인하는 대화가 중요합니다.'
    }
    balance = {
        '목':'속도보다 방향을 먼저 정하고, 시작한 일은 작은 단위로라도 계속 이어가는 것이 도움이 됩니다.',
        '화':'하고 싶은 마음만으로 밀어붙이기보다 쉬는 구간과 우선순위를 함께 정하는 것이 도움이 됩니다.',
        '토':'모든 책임을 혼자 해결하려 하기보다 역할을 나누는 것이 장기적으로 더 안정적입니다.',
        '금':'완벽하게 납득될 때까지 기다리기보다 결정 기준을 미리 정해두면 선택이 빨라질 수 있습니다.',
        '수':'생각을 충분히 하는 것과 결정을 미루는 것을 구분하는 연습이 중요합니다.'
    }
    return {
        '한눈에 보는 핵심': f'{day} · {elem} 기운을 중심으로 보면, 당신의 핵심은 “{personality[elem][:55]}”입니다.',
        '타고난 성향': personality[elem],
        '돈과 재물': money[elem],
        '직업과 사업': work[elem],
        '연애와 인간관계': relationship[elem],
        '반복되기 쉬운 패턴': f'{strongest} 기운이 상대적으로 두드러지고 {weakest} 기운이 적게 나타나는 구조를 기준으로 보면, 강점이 과해질 때와 부족한 부분을 보완할 때의 차이를 함께 보는 것이 중요합니다.',
        '내가 조심할 부분': balance[weakest],
        '대운과 시기': '대운은 10년 단위의 큰 흐름으로 살펴봅니다. 실제 리포트에서는 현재 나이와 각 대운의 시작·종료 시점을 함께 놓고 중요한 변화를 설명합니다.',
        '현실적인 조언': f'당신에게 중요한 것은 “좋은 운을 기다리는 것”보다 현재 가진 {strongest}의 장점을 실제 선택에 활용하고 {weakest}와 관련된 약점을 의식적으로 보완하는 것입니다.',
        '마지막으로': '사주는 미래를 확정하는 예언이라기보다, 전통적인 해석 체계로 자신의 성향과 선택을 돌아보는 참고 자료로 활용하는 것이 좋습니다.'
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
        'na_yin':analysis['na_yin'],'twelve':analysis['twelve'],'extra':analysis['extra'],'daewoon':analysis['daewoon'],'teaser':analysis['teaser']
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
