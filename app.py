import os
import base64
import uuid
import requests
from flask import Flask, render_template, request, redirect, url_for
from lunar_python import Solar
from supabase import create_client

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-change-me')

SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://bjjqpmkvtmnecekdnzbf.supabase.co')
SUPABASE_PUBLISHABLE_KEY = os.getenv('SUPABASE_PUBLISHABLE_KEY', '')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')
TOSS_CLIENT_KEY = os.getenv('TOSS_CLIENT_KEY', '')
TOSS_SECRET_KEY = os.getenv('TOSS_SECRET_KEY', '')
SUPABASE_ADMIN = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY) if SUPABASE_SERVICE_ROLE_KEY else None

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
    elem = analysis.get('day_master_element', '토')
    counts = analysis.get('element_counts', {})
    strongest = max(counts, key=counts.get) if counts else elem
    weakest = min(counts, key=counts.get) if counts else elem
    day = analysis.get('day_master_label', '')
    birth_year = int(str(analysis.get('birth_date','2000-01-01'))[:4])
    current_year = 2026
    age = current_year - birth_year + 1
    daewoon = analysis.get('daewoon') or []
    current_daewoon = next((d for d in daewoon if d.get('start_age', 999) <= age <= d.get('end_age', -1)), None)

    profiles = {
        '목': {
            'theme':'성장·확장·새로운 시도',
            'core':'새로운 가능성이 보이면 스스로 길을 만들어가려는 힘이 있습니다. 남이 정해준 답을 그대로 따르기보다 더 나은 방법을 찾고, 한 번 방향을 잡으면 실제 행동으로 옮기려는 성향이 있습니다.',
            'shadow':'다만 선택지가 많아질수록 시작 전에 여러 가능성을 비교할 수 있습니다. 이미 충분히 괜찮은 선택을 해놓고도 더 좋은 답을 찾느라 속도가 늦어지는 모습이 나타날 수 있습니다.',
            'money':'돈에서는 성장과 확장을 향한 욕구가 중요한 변수입니다. 단순히 아끼는 것보다 돈이 다시 기회를 만들어내는 구조를 선호할 수 있습니다. 다만 확장 속도가 현금흐름보다 빨라지지 않도록 투자·사업·소비를 분리해 보는 기준이 필요합니다.',
            'work':'변화와 개선의 여지가 있는 환경에서 장점이 살아납니다. 직접 기획하거나 새로운 것을 만들고, 기존 방식을 더 나은 방식으로 바꾸는 역할에서 몰입하기 쉽습니다. 지나치게 반복적인 환경에서는 성취감이 떨어질 수 있습니다.',
            'love':'함께 성장하고 있다는 느낌이 중요합니다. 상대의 영역을 존중하면서도 서로의 미래를 이야기할 수 있는 관계에서는 마음을 오래 쓰는 편입니다. 반대로 통제받는 느낌이 강하면 겉으로는 참고 있어도 마음이 먼저 멀어질 수 있습니다.',
            'pattern':'새로운 가능성을 많이 열어두다 하나를 깊게 가져가는 시점이 늦어질 수 있습니다.',
            'advice':'더 좋은 선택만 찾기보다 지금 선택한 것을 일정 기간 직접 키워보는 방식이 잘 맞습니다.'
        },
        '화': {
            'theme':'표현·추진·실행력',
            'core':'마음이 움직이면 행동으로 옮기는 속도가 빠르고 중요한 일에는 에너지를 집중합니다. 주변에서도 의욕과 추진력이 보이기 쉬워서 일을 시작하는 순간에는 자연스럽게 중심 역할을 맡을 수 있습니다.',
            'shadow':'반대로 의미가 없다고 느끼는 일에는 에너지가 급격히 떨어질 수 있습니다. 시작할 때의 열정과 오래 유지하는 힘이 다르게 나타날 수 있으므로, 의욕보다 반복 가능한 시스템을 만들어두는 것이 중요합니다.',
            'money':'만족감과 추진력이 함께 움직일 수 있습니다. 목표가 분명하면 수입을 늘리기 위해 적극적으로 움직이지만, 기분이 좋아진 순간의 소비나 확신이 생긴 투자를 구분할 장치가 필요합니다. 돈을 벌 수 있는 능력과 돈을 지키는 규칙을 따로 만드는 편이 좋습니다.',
            'work':'사람에게 영향을 주거나 직접 결과가 보이는 업무에서 에너지가 살아날 가능성이 큽니다. 성과가 눈에 보이고 피드백이 빠른 환경에서는 장점이 커지지만, 결과가 너무 늦게 나타나는 일에서는 중간에 흥미가 떨어지지 않도록 작은 목표가 필요합니다.',
            'love':'좋아하는 마음은 비교적 분명하게 표현할 수 있습니다. 관계가 잘 풀릴 때는 따뜻하고 적극적이지만 감정의 온도 차이가 생기면 상대가 변화를 크게 느낄 수 있습니다. 감정이 올라온 순간의 결론보다 하루 정도 지나 다시 이야기하는 습관이 관계에 도움이 됩니다.',
            'pattern':'시작할 때의 열정과 장기적으로 유지하는 힘 사이에 차이가 생길 수 있습니다.',
            'advice':'크게 시작하기보다 오래 유지할 수 있는 크기로 시작하고, 반복되는 루틴을 만드는 편이 좋습니다.'
        },
        '토': {
            'theme':'안정·현실감·책임',
            'core':'현실적인 조건과 책임을 중요하게 생각하고 문제가 생기면 스스로 정리하려는 힘이 있습니다. 주변에서는 믿고 맡길 수 있는 사람으로 보이기 쉽고, 급한 상황에서도 해야 할 일을 먼저 챙기는 쪽에 가깝습니다.',
            'shadow':'겉으로는 안정적으로 보여도 실제로는 책임을 많이 짊어질 수 있습니다. 혼자 해결하려는 습관이 쌓이면 어느 순간 피로가 크게 올라올 수 있고, 참고 있던 불만이 한꺼번에 드러나는 패턴도 조심할 필요가 있습니다.',
            'money':'한 번의 큰 기회보다 안정적인 흐름을 만드는 방식이 잘 맞을 가능성이 있습니다. 고정비와 현금흐름을 관리하면서 조금씩 규모를 키우는 전략이 유리합니다. 남을 돕거나 책임을 대신 지느라 계획보다 지출이 커지지 않는지도 확인할 필요가 있습니다.',
            'work':'운영·관리·책임이 필요한 환경에서 꾸준함이 강점으로 나타납니다. 일을 맡으면 끝까지 정리하려는 성향 때문에 신뢰를 얻기 쉽지만, 모든 문제를 직접 해결하려고 하면 성장 속도가 오히려 느려질 수 있습니다.',
            'love':'관계에서 책임감이 강해 상대의 문제까지 자신의 몫처럼 받아들일 수 있습니다. 오래 가는 관계를 중요하게 여기기 때문에 쉽게 끊지는 않지만, 그만큼 서운함도 오래 쌓일 수 있습니다. 상대가 스스로 해결해야 할 영역을 존중하는 것이 중요합니다.',
            'pattern':'내가 조금 더 참으면 된다는 방식으로 문제를 해결하려는 패턴이 반복될 수 있습니다.',
            'advice':'책임지는 것과 대신 해결해주는 것은 다릅니다. 자신의 몫과 상대의 몫을 구분하는 것이 중요합니다.'
        },
        '금': {
            'theme':'기준·판단·정리',
            'core':'기준과 판단이 비교적 분명하고 중요한 것과 그렇지 않은 것을 구분하려는 성향이 있습니다. 애매한 상태를 오래 두기보다 핵심을 찾아 정리하려는 힘이 있고, 결과의 품질을 높이는 데 관심이 많을 수 있습니다.',
            'shadow':'스스로 납득할 때까지 기다리다가 결정이 늦어지거나, 한번 실망하면 관계와 일에서 거리를 크게 둘 수 있습니다. 기준이 높은 것이 장점이지만 그 기준이 자신에게도 너무 엄격해지지 않는지 살펴볼 필요가 있습니다.',
            'money':'효율과 결과를 중요하게 봅니다. 숫자와 조건을 확인하는 능력이 장점이지만 확신이 생기면 오히려 과감해질 수 있습니다. 큰돈을 움직일 때는 본인의 판단과 별개로 한 번 더 검토하는 절차를 만들어두면 균형이 좋아집니다.',
            'work':'기준을 세우고 문제를 정리하거나 품질을 관리하는 역할에서 강점을 활용하기 좋습니다. 업무의 허점을 찾아 개선하는 능력이 있지만, 다른 사람에게도 같은 기준을 요구하면 관계에서 피로가 생길 수 있습니다.',
            'love':'서로 원하는 것을 분명히 말하는 관계에서 편안함을 느끼기 쉽습니다. 애매한 태도보다 행동으로 신뢰를 보여주는 사람에게 마음이 안정될 가능성이 큽니다. 다만 실망한 순간 바로 결론을 내리기보다 상대의 의도를 확인하는 과정이 필요합니다.',
            'pattern':'완벽한 답을 기다리다가 타이밍을 놓치거나 한번 실망하면 너무 빨리 정리할 수 있습니다.',
            'advice':'모든 선택을 완벽하게 만들기보다 충분히 좋은 선택의 기준을 미리 정해두는 것이 좋습니다.'
        },
        '수': {
            'theme':'유연함·정보·사고',
            'core':'상황과 사람의 분위기를 읽고 여러 가능성을 생각하는 유연한 성향이 있습니다. 같은 문제도 한 가지 방법으로만 보지 않고 다른 선택지를 찾아내는 능력이 장점으로 나타날 수 있습니다.',
            'shadow':'생각할 수 있는 경우의 수가 많아질수록 결정이 늦어질 수 있습니다. 겉으로는 차분해도 혼자 여러 번 결론을 바꾸거나 상대의 말에 숨은 의미를 계속 해석하면서 피로가 커질 수 있습니다.',
            'money':'정보와 타이밍을 읽는 능력을 활용할 수 있습니다. 다양한 기회를 발견하는 것은 장점이지만 선택지를 너무 많이 비교하면 좋은 기회를 늦게 잡을 수 있습니다. 돈과 관련해서는 정보 수집의 종료 시점을 정하는 것이 중요합니다.',
            'work':'정보를 다루고 상황에 따라 전략을 바꾸는 업무에서 유연함을 활용하기 좋습니다. 변화가 많은 환경에 적응하는 힘이 있지만, 기준 없이 여러 일을 동시에 잡으면 집중력이 분산될 수 있습니다.',
            'love':'상대의 작은 변화를 빠르게 감지할 수 있습니다. 그래서 말하지 않은 의미까지 추측하지 않도록 확인하는 대화가 중요합니다. 상대를 이해하려는 마음이 큰 만큼 혼자 결론을 내리지 않는 것이 관계의 안정에 도움이 됩니다.',
            'pattern':'생각을 충분히 하는 것과 결정을 미루는 것이 섞이면 기회를 놓치거나 마음의 피로가 커질 수 있습니다.',
            'advice':'결정에 필요한 핵심 정보 세 가지만 정하고 나머지는 실행하면서 확인하는 방식이 도움이 됩니다.'
        }
    }
    p = profiles.get(elem, profiles['토'])
    labels = {'목':'성장과 확장','화':'표현과 추진','토':'안정과 현실감','금':'기준과 판단','수':'유연함과 사고'}
    pillar_text = ' · '.join(x.get('label_full','') for x in analysis.get('pillars', []))
    count_text = ', '.join(f'{k} {v}' for k,v in counts.items())
    daewoon_text = '대운 자료가 계산되지 않았습니다.'
    if current_daewoon:
        daewoon_text = f"현재 나이 기준으로는 {current_daewoon.get('gan_zhi_label','')} 대운({current_daewoon.get('start_age')}~{current_daewoon.get('end_age')}세, {current_daewoon.get('start_year')}~{current_daewoon.get('end_year')}) 구간에 해당합니다. 이 시기는 삶의 모든 일이 반드시 바뀐다는 뜻이 아니라, 특정 주제에 관심과 선택이 커질 수 있는 구간으로 참고하는 것이 좋습니다."
    elif daewoon:
        daewoon_text = f"계산된 대운은 {daewoon[0].get('start_year')}년부터 이어지며, 각 10년 구간의 성격을 현재 상황과 함께 비교해보는 방식으로 참고할 수 있습니다."

    return {
        '한눈에 보는 핵심': f"{day} · {elem} 기운을 중심으로 보면, {p['core']}\n\n현재 사주에서 가장 눈에 띄는 {strongest} 기운은 '{labels[strongest]}' 쪽으로 읽을 수 있고, 상대적으로 적은 {weakest} 기운은 '{labels[weakest]}' 영역을 의식적으로 보완할 때 참고가 됩니다.",
        '타고난 성향': f"{p['core']} {p['shadow']}\n\n특히 이 성향은 사람을 대할 때와 혼자 판단할 때 차이가 날 수 있습니다. 겉으로 보이는 행동만 보면 단순해 보이지만 실제 선택 과정에서는 자신의 기준과 여러 조건을 함께 따져보는 편으로 볼 수 있습니다. 그래서 본인을 이해할 때 '나는 왜 이러지?'라고 단순화하기보다 어떤 상황에서 에너지가 올라가고 떨어지는지를 보는 것이 더 유용합니다.",
        '돈과 재물': f"{p['money']}\n\n오행 분포상 {strongest} 기운이 상대적으로 강하게 나타나기 때문에 돈을 다룰 때도 '{labels[strongest]}' 성향이 개입하기 쉽습니다. 반대로 {weakest} 기운은 상대적으로 약하게 나타나므로 그 영역을 보완하는 규칙을 따로 만드는 것이 좋습니다. 예를 들어 큰돈을 결정할 때는 감정과 별개로 예산 상한선, 보류 기간, 고정비 기준을 정해두면 판단의 흔들림을 줄일 수 있습니다.\n\n중요한 것은 '돈복이 있다/없다'보다 내가 돈을 벌고 지키는 과정에서 어떤 행동을 반복하는지입니다.",
        '직업과 사업': f"{p['work']}\n\n이 사주에서는 {labels[strongest]} 성향을 일에 활용할 때 장점이 커질 가능성이 있습니다. 반대로 {weakest}와 연결된 부분이 부족해지면 일을 시작하거나 유지하는 과정에서 특정 부분이 병목이 될 수 있습니다. 따라서 직업을 선택할 때 직종 이름만 보기보다 '내가 결정권을 얼마나 갖는가', '결과가 얼마나 빨리 보이는가', '사람과 숫자 중 무엇을 더 많이 다루는가'를 기준으로 비교하는 것이 현실적입니다.\n\n사업을 한다면 잘하는 일을 직접 붙잡고 있는 것과 시스템으로 넘기는 일을 구분하는 것이 특히 중요합니다.",
        '연애와 인간관계': f"{p['love']}\n\n관계에서는 내가 상대에게 무엇을 기대하는지보다, 기대가 충족되지 않았을 때 어떤 반응을 보이는지를 살펴보는 것이 중요합니다. {p['pattern']}\n\n가까운 사람일수록 참다가 한 번에 이야기하기보다 작은 불편을 초기에 말하는 편이 관계를 오래 유지하는 데 도움이 됩니다. 상대를 바꾸는 것보다 내가 어떤 상황에서 마음을 닫거나 과하게 책임지는지를 아는 것이 이 사주를 활용하는 현실적인 방법입니다.",
        '반복되기 쉬운 패턴': f"현재 오행 분포는 {count_text}으로 나타납니다. 가장 강한 {strongest} 기운은 {labels[strongest]} 쪽 장점으로 활용될 수 있지만, 과해지면 그 장점이 오히려 부담으로 바뀔 수 있습니다. 상대적으로 적은 {weakest} 기운은 반대 방향의 행동을 의식적으로 연습할 때 균형을 잡는 참고점이 됩니다.\n\n{p['pattern']}\n\n특히 큰 결정을 앞두고 같은 고민을 반복한다면 '정보가 부족해서인지, 결정이 무서워서인지, 책임질 결과가 부담스러운 것인지'를 구분해보는 것이 좋습니다.",
        '내가 조심할 부분': f"{p['advice']}\n\n또 하나는 본인의 강점을 모든 상황에 적용하지 않는 것입니다. 강점도 상황이 바뀌면 과해질 수 있습니다. 빠른 사람이 항상 빨라야 하는 것도 아니고, 책임감이 강한 사람이 모든 일을 책임져야 하는 것도 아닙니다. 내 방식이 효과적인 상황과 그렇지 않은 상황을 구분하는 것이 장기적으로 더 큰 장점이 됩니다.",
        '대운과 시기': f"{daewoon_text}\n\n대운은 10년 단위의 큰 흐름이므로 '올해 무조건 무슨 일이 생긴다'는 식으로 단정하기보다 어떤 주제에 선택이 집중되기 쉬운지를 보는 것이 좋습니다.\n\n현재와 다음 대운의 경계에서는 직업, 돈, 관계처럼 삶의 우선순위가 달라지는 경험을 할 수 있으므로, 중요한 결정을 할 때 현재의 편안함뿐 아니라 3~5년 뒤 유지 가능한지도 함께 비교해보세요.",
        '내 사주를 실제 생활에 적용한다면': f"첫째, {strongest} 기운의 장점을 돈과 일에서 적극적으로 활용하세요. 둘째, {weakest} 기운과 관련된 행동은 의식적으로 보완하세요. 셋째, 관계에서는 감정이 커진 순간 결론을 내리기보다 확인하고 말하는 시간을 가지세요.\n\n이 세 가지를 생활 기준으로 잡으면 사주를 단순한 운세가 아니라 자신의 선택 습관을 점검하는 도구로 활용할 수 있습니다.",
        '마지막으로': '이 리포트는 전통적인 사주 해석을 바탕으로 자신을 돌아보기 위한 참고 자료입니다. 미래를 확정하거나 특정 사건을 보장하는 예언이 아니며, 실제 선택과 결과는 현실의 조건과 본인의 판단에 따라 달라질 수 있습니다.'
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
    return {'supabase_url':SUPABASE_URL,'supabase_publishable_key':SUPABASE_PUBLISHABLE_KEY,'toss_client_key':TOSS_CLIENT_KEY}

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

def _require_supabase_admin():
    if not SUPABASE_ADMIN:
        raise RuntimeError('SUPABASE_SERVICE_ROLE_KEY가 Render 환경변수에 없습니다.')

def _get_supabase_user(access_token):
    response = requests.get(
        f'{SUPABASE_URL}/auth/v1/user',
        headers={'apikey': SUPABASE_PUBLISHABLE_KEY, 'Authorization': f'Bearer {access_token}'},
        timeout=10,
    )
    if response.status_code != 200:
        return None
    return response.json()

@app.post('/payment/create-order')
def create_payment_order():
    try:
        _require_supabase_admin()
        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            return {'error':'로그인이 필요합니다.'}, 401
        user = _get_supabase_user(auth.split(' ', 1)[1])
        if not user or not user.get('id'):
            return {'error':'로그인 세션이 유효하지 않습니다.'}, 401
        payload = request.get_json(silent=True) or {}
        reading_id = str(payload.get('reading_id', '')).strip()
        if not reading_id:
            return {'error':'사주 결과를 찾을 수 없습니다.'}, 400
        reading_res = SUPABASE_ADMIN.table('readings').select('id,user_id').eq('id', reading_id).eq('user_id', user['id']).single().execute()
        if not reading_res.data:
            return {'error':'내 사주 결과만 결제할 수 있습니다.'}, 403
        order_id = 'SAJU-' + uuid.uuid4().hex
        product = PRODUCTS['saju_detail']
        SUPABASE_ADMIN.table('orders').insert({
            'user_id': user['id'], 'reading_id': reading_id, 'order_id': order_id,
            'product_name': product['name'], 'amount': product['amount'], 'status': 'READY',
        }).execute()
        return {'order_id':order_id,'amount':product['amount'],'product_name':product['name']}
    except Exception as exc:
        print('CREATE ORDER ERROR:', repr(exc))
        return {'error':'주문 생성 중 오류가 발생했습니다.'}, 500

@app.get('/payment/success')
def payment_success():
    payment_key = request.args.get('paymentKey', '').strip()
    order_id = request.args.get('orderId', '').strip()
    amount_raw = request.args.get('amount', '').strip()
    try:
        _require_supabase_admin()
        if not TOSS_SECRET_KEY:
            raise RuntimeError('TOSS_SECRET_KEY가 Render 환경변수에 없습니다.')
        if not payment_key or not order_id or not amount_raw:
            return render_template('payment_result.html', success=False, message='결제 정보가 올바르지 않습니다.'), 400
        try:
            amount = int(amount_raw)
        except ValueError:
            return render_template('payment_result.html', success=False, message='결제 금액이 올바르지 않습니다.'), 400
        order_res = SUPABASE_ADMIN.table('orders').select('*').eq('order_id', order_id).single().execute()
        order = order_res.data
        if not order:
            return render_template('payment_result.html', success=False, message='주문을 찾을 수 없습니다.'), 404
        expected_amount = PRODUCTS['saju_detail']['amount']
        if order.get('amount') != expected_amount or amount != expected_amount:
            return render_template('payment_result.html', success=False, message='결제 금액 검증에 실패했습니다.'), 400
        if order.get('status') == 'PAID':
            return redirect(url_for('saved_saju_result', reading_id=order['reading_id']))
        credential = base64.b64encode((TOSS_SECRET_KEY + ':').encode()).decode()
        confirm = requests.post(
            'https://api.tosspayments.com/v1/payments/confirm',
            headers={'Authorization': f'Basic {credential}', 'Content-Type': 'application/json', 'Idempotency-Key': str(uuid.uuid4())},
            json={'paymentKey':payment_key,'orderId':order_id,'amount':expected_amount},
            timeout=20,
        )
        if confirm.status_code >= 400:
            print('TOSS CONFIRM ERROR:', confirm.status_code, confirm.text)
            return render_template('payment_result.html', success=False, message='결제 승인에 실패했습니다. 잠시 후 다시 시도해주세요.'), 400
        reading_res = SUPABASE_ADMIN.table('readings').select('id,free_summary').eq('id', order['reading_id']).single().execute()
        saved = (reading_res.data or {}).get('free_summary') or {}
        calculation = saved.get('calculation') if isinstance(saved, dict) else None
        if not calculation:
            return render_template('payment_result.html', success=False, message='사주 분석 데이터를 찾을 수 없습니다.'), 500
        report = make_detailed_report(calculation)
        report['_version'] = 2
        SUPABASE_ADMIN.table('orders').update({'payment_key':payment_key,'status':'PAID','paid_at':'now()'}).eq('order_id', order_id).execute()
        SUPABASE_ADMIN.table('paid_reports').upsert({'reading_id':order['reading_id'],'report':report}, on_conflict='reading_id').execute()
        return redirect(url_for('saved_saju_result', reading_id=order['reading_id']) + '?paid=1')
    except Exception as exc:
        print('PAYMENT SUCCESS ERROR:', repr(exc))
        return render_template('payment_result.html', success=False, message='결제 처리 중 오류가 발생했습니다.'), 500

@app.post('/payment/regenerate-report')
def regenerate_report():
    try:
        _require_supabase_admin()
        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            return {'error':'로그인이 필요합니다.'}, 401
        user = _get_supabase_user(auth.split(' ', 1)[1])
        if not user or not user.get('id'):
            return {'error':'로그인 세션이 유효하지 않습니다.'}, 401
        payload = request.get_json(silent=True) or {}
        reading_id = str(payload.get('reading_id', '')).strip()
        if not reading_id:
            return {'error':'결과를 찾을 수 없습니다.'}, 400

        order_res = (
            SUPABASE_ADMIN.table('orders')
            .select('id,reading_id,status,user_id')
            .eq('reading_id', reading_id)
            .eq('user_id', user['id'])
            .eq('status', 'PAID')
            .limit(1)
            .execute()
        )
        if not order_res.data:
            return {'error':'결제된 리포트를 찾을 수 없습니다.'}, 403

        reading_res = (
            SUPABASE_ADMIN.table('readings')
            .select('id,free_summary')
            .eq('id', reading_id)
            .eq('user_id', user['id'])
            .single()
            .execute()
        )
        saved = (reading_res.data or {}).get('free_summary') or {}
        calculation = saved.get('calculation') if isinstance(saved, dict) else None
        if not calculation:
            return {'error':'사주 분석 데이터를 찾을 수 없습니다.'}, 500

        report = make_detailed_report(calculation)
        report['_version'] = 2
        SUPABASE_ADMIN.table('paid_reports').upsert(
            {'reading_id': reading_id, 'report': report},
            on_conflict='reading_id'
        ).execute()
        return {'ok': True, 'report': report}
    except Exception as exc:
        print('REGENERATE REPORT ERROR:', repr(exc))
        return {'error':'상세 리포트 갱신 중 오류가 발생했습니다.'}, 500

@app.get('/payment/fail')
def payment_fail():
    message = request.args.get('message', '결제가 취소되었거나 완료되지 않았습니다.')
    return render_template('payment_result.html', success=False, message=message)


@app.route('/my')
def my_page(): return render_template('my.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=int(os.getenv('PORT',5000)),debug=True)
