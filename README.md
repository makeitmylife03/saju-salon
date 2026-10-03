# 사주살롱 MVP v3

현재 연결된 기능:
- Supabase Auth 이메일 매직링크 로그인
- 로그인한 사용자의 사주 결과 Supabase 저장
- `readings` 조회 및 내 결과 페이지
- 결제 완료 여부에 따라 상세 리포트 공개 구조
- 상세 리포트는 `paid_reports`에 분리 저장

## 환경변수
`SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `FLASK_SECRET_KEY`를 설정하세요.

브라우저에 들어가는 것은 Publishable key뿐입니다. Secret/service_role 키는 절대 노출하지 마세요.

## 다음 단계
1. Supabase Auth 이메일 설정 확인
2. 매직링크 로그인 테스트
3. 사주 저장/재조회 테스트
4. 토스페이먼츠 결제창 및 서버 승인 API 연결
5. 결제 성공 시 `orders.status=PAID` 저장 및 `paid_reports` 생성
6. 실제 만세력 계산과 AI 리포트 생성 연결
