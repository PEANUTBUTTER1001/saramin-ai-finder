# Saramin AI Finder — 에이전트 작업 규칙
사람인 채용공고 검색과 열람 공고의 기술 스택 통계를 제공하는 Android 앱과, 공고 누적 보관·요건 분석·신규 공고 감시를 제공하는 Windows PC 앱.
Source of Truth: `README.md`, `desktop/README.md`, `desktop/pyproject.toml`, `settings.gradle.kts`, `app/build.gradle.kts`, `gradle/libs.versions.toml`, `build-logic/convention/` · 이 문서는 사용자 승인을 받아서만 개정한다.

## 1. 명령
- Android 설치: (미정)
- Android 실행: (미정) — `README.md`는 Android Studio에서 빌드·실행하도록 안내한다.
- 테스트: `./gradlew.bat :app:testDebugUnitTest`
- 정적 검사: `./gradlew.bat :app:lintDebug`
- PC 개발 환경: Windows x64·Python 3.12에서 `python -m pip install -e "desktop[test]"`. 배포물 준비용 Python 3.9 이상과 구분한다.
- PC 테스트: `python -m pytest -q --basetemp desktop/.pytest-tmp desktop/tests`
- PC 화면 생성: `python desktop/tools/build_ui.py` — 현재 입력 원본이 삭제되어 실행 불가. 원본 복원 또는 생성 경로 정리 전에는 사용하지 않는다.
- PC JavaScript 검사: `node --check desktop/src/saramin_finder/ui/app.js`.
- PC GUI: PowerShell에서 `$env:SARFINDER_SMOKE_OFFSCREEN="1"` 설정 후 `desktop/dist/SaraminFinder/runtime/python.exe desktop/tools/gui_smoke.py workbench`; 복원·조건 저장은 각각 `workbench_restore`·`profile` 모드.
- PC 설치·실행: 루트 `설치.bat` — 배포물 생성 → 바탕화면 바로가기 생성 → 실행.
- PC 배포물 생성: `python desktop/packaging/build_portable.py` — Windows x64, Python 3.9 이상에서 실행한다.
- PC 실행: `desktop/dist/SaraminFinder/실행.bat` 또는 바탕화면 바로가기 — 배포물 생성 후 실행한다.

## 2. 구조 지도
역할은 폴더 이름이 아니라 코드가 하는 일로 판단한다. Android 앱 코드는 `:app` 단일 모듈이다. PC 앱은 `desktop/`의 별도 Python 프로젝트다.

| 역할 | 경로 | 들어가는 것 |
|---|---|---|
| 진입 | `app/src/main/java/com/peanutbutter1001/saramin_ai_finder/MainActivity.kt`, `app/src/main/java/com/peanutbutter1001/saramin_ai_finder/navigation/`, `app/src/main/java/com/peanutbutter1001/saramin_ai_finder/ui/screens/`, `app/src/main/java/com/peanutbutter1001/saramin_ai_finder/ui/components/`, `desktop/src/saramin_finder/ui/` | Android 진입, 화면 이동, 사용자 입력·UI 상태와 화면 컴포넌트; PC HTML·Qt 브리지 |
| 유스케이스 | `desktop/src/saramin_finder/usecases/` | PC 수집·공고 및 분석 CSV; Android 별도 구현 없음 |
| 도메인 | `app/src/main/java/com/peanutbutter1001/saramin_ai_finder/data/model/`, `app/src/main/java/com/peanutbutter1001/saramin_ai_finder/utils/HtmlParser.kt`, `app/src/main/java/com/peanutbutter1001/saramin_ai_finder/utils/TechKeywords.kt`, `desktop/src/saramin_finder/domain/` | 공고·통계 모델, 순수 파싱·필터·키워드 규칙; PC 모델·검증·키워드 규칙 |
| 포트 | (미정) | 별도 인터페이스 없음. 외부 협력자를 분리할 때만 위치 결정 |
| 인프라 | `app/src/main/java/com/peanutbutter1001/saramin_ai_finder/data/repository/`, `app/src/main/java/com/peanutbutter1001/saramin_ai_finder/utils/IntentUtils.kt`, `desktop/src/saramin_finder/infrastructure/` | 사람인 네트워크·파일 캐시·통계 저장, 외부 앱·브라우저 Intent; PC HTTP·SQLite·CSV 파일 접근 |
| 조립 | `app/src/main/java/com/peanutbutter1001/saramin_ai_finder/SaraminAiFinderApplication.kt`, `app/src/main/java/com/peanutbutter1001/saramin_ai_finder/di/`, `desktop/src/saramin_finder/main.py`, `desktop/tools/build_ui.py`, `desktop/packaging/`, `설치.bat` | Hilt 앱 및 저장소 제공; PC 앱·창 진입·배포·화면 생성 조립 |
| 공유 | `app/src/main/java/com/peanutbutter1001/saramin_ai_finder/ui/theme/`, `desktop/src/saramin_finder/__init__.py` | 테마와 시각 스타일; PC 패키지 표식 |
| 테스트 | `app/src/test/`, `app/src/androidTest/`, `desktop/tests/`, `desktop/tools/gui_smoke.py`, `desktop/tools/watch_smoke.py` | JVM 단위 테스트와 Android 계측 테스트; PC 단위·GUI·감시 검증 |

## 3. 의존 규칙
규칙은 §2의 역할을 기준으로 적용한다. 현재 단일 모듈에 역할 간 Gradle 경계 검사는 없다.
- [목표] (R1) 의존은 진입 → 유스케이스 → 도메인 방향으로 흐른다. 인프라는 포트를 구현하며, 도메인·포트는 진입·인프라·조립을 import하지 않는다. 현재 직접 인프라를 호출하는 진입 코드는 §6에 기록한다.
- [목표] (R2) 파일·DB·네트워크·IPC·시계·환경변수 접근은 인프라와 조립에서만 한다.
- [목표] PC의 HTML 화면은 사이트·DB에 직접 접근하지 않고, 앱에 포함된 로컬 페이지와 제한된 QWebChannel 명령만 사용한다.
- [목표] (R3) 구현체 생성과 연결은 조립에서만 한다. 그 밖의 코드는 협력자를 생성자 또는 DI로 받는다. 생성자에서 주입받은 팩터리로 실행별 자원을 생성하는 것은 허용하되, 구체 구현의 import는 R1을 따른다.
- [목표] (R4) 진입은 입력 검증, 협력자 호출, 출력 변환을 담당한다. 규칙·계산과 복잡한 흐름 조율은 분리한다. 현재 예외는 §6에 기록한다.

## 4. 무엇을 어디에
| 넣을 것 | 위치 |
|---|---|
| 공고·상세·통계 값 모델 | `app/src/main/java/com/peanutbutter1001/saramin_ai_finder/data/model/` |
| 검색 결과 파싱·필터와 기술 키워드 매핑 | `app/src/main/java/com/peanutbutter1001/saramin_ai_finder/utils/HtmlParser.kt`, `app/src/main/java/com/peanutbutter1001/saramin_ai_finder/utils/TechKeywords.kt` |
| 사람인 요청, JSON 캐시·통계 저장 | `app/src/main/java/com/peanutbutter1001/saramin_ai_finder/data/repository/` |
| 외부 앱·브라우저로 공고 열기 | `app/src/main/java/com/peanutbutter1001/saramin_ai_finder/utils/IntentUtils.kt` |
| 화면·상태와 재사용 UI | `app/src/main/java/com/peanutbutter1001/saramin_ai_finder/ui/screens/`, `app/src/main/java/com/peanutbutter1001/saramin_ai_finder/ui/components/` |
| Hilt 구성 | `app/src/main/java/com/peanutbutter1001/saramin_ai_finder/di/` |
| PC 목록·상세 요청과 HTML 파싱 | `desktop/src/saramin_finder/infrastructure/saramin.py` |
| PC SQLite 보관·조회 | `desktop/src/saramin_finder/infrastructure/database.py` |
| PC 검색 프로필·섹션·키워드 규칙 | `desktop/src/saramin_finder/domain/` |
| PC 화면·스타일·Qt 브리지 | `desktop/src/saramin_finder/ui/app.js`, `desktop/src/saramin_finder/ui/workbench.css`, `desktop/src/saramin_finder/ui/index.html`, `desktop/src/saramin_finder/ui/bridge.py` |
| PC 화면 생성·GUI 검증 | `desktop/tools/build_ui.py`, `desktop/tools/gui_smoke.py`, `desktop/tools/watch_smoke.py` |
| PC 수집·분석 내보내기 | `desktop/src/saramin_finder/usecases/` |

## 5. 새 기능 레시피
- [목표] (R8) 먼저 관련 코드의 책임·의존성과 기존 기능 흐름을 확인한다. 현재 구조를 한꺼번에 교체하지 않고 필요한 역할부터 변경한다.
1. 모델과 순수 파싱·필터·키워드 규칙을 정한다.
2. 필요한 네트워크·저장 동작을 인프라에 구현한다.
3. 화면 상태와 사용자 동작을 진입에 연결한다.
4. 새 의존성이 생기면 조립에서 연결한다.
5. 변경한 규칙과 데이터 흐름을 관련 테스트로 확인한다.

## 6. 알려진 예외
- [목표] (R9) 아래 예외는 늘리지 않는다. 수정하는 파일에 예외가 있어도 요청 범위 밖이면 별도 작업으로 제안한다. 예외 추가는 §9에 따라 승인받는다.

| 규칙 | 파일 | 사유 |
|---|---|---|
| R1 | `app/src/main/java/com/peanutbutter1001/saramin_ai_finder/ui/screens/HomeViewModel.kt` | 포트 없이 구체 `SaraminRepository`를 직접 주입받음 |
| R1 | `app/src/main/java/com/peanutbutter1001/saramin_ai_finder/ui/screens/StatsViewModel.kt` | 포트 없이 구체 `SaraminRepository`를 직접 주입받음 |
| R1 | `app/src/main/java/com/peanutbutter1001/saramin_ai_finder/ui/screens/HomeScreen.kt` | 화면이 `IntentUtils`를 직접 호출함 |
| R4 | `app/src/main/java/com/peanutbutter1001/saramin_ai_finder/ui/screens/HomeViewModel.kt` | 캐시 표시·크롤링·오류 처리를 한 ViewModel에서 조율함 |
| R1 | `desktop/src/saramin_finder/usecases/collect.py` | 포트 없이 구체 Store·SaraminClient와 CrawlError를 직접 참조함 |
| R1 | `desktop/src/saramin_finder/usecases/analyze.py` | 포트 없이 구체 Store를 직접 참조함 |
| R1 | `desktop/src/saramin_finder/ui/bridge.py` | 구체 Store와 CSV 인프라를 직접 호출함 |
| R3 | `desktop/src/saramin_finder/ui/bridge.py` | 조립 밖에서 Collector를 생성해 연결함 |
| R4 | `desktop/src/saramin_finder/ui/bridge.py` | 진입에서 감시 예약·작업 실행·결과 및 오류 흐름을 조율함 |

## 7. 하지 말 것
- [목표] (R7) 인터페이스·유스케이스·모듈·공통 컴포넌트는 구현이 2개 이상이거나 테스트 대역이 실제로 필요할 때만 만들고, 추가할 때 해결할 문제를 밝힌다.
- [목표] (R11) 요청된 구현에 필요한 변경만 한다. 범위 밖의 큰 리팩터링은 별도 제안으로 분리한다.
- 유스케이스 위에 서비스 계층을 더하지 않는다.
- 미래를 위한 인터페이스·기반 클래스·범용 헬퍼를 만들지 않는다.
- PC 배포 폴더와 개발용 내려받은 의존성은 Git에 포함하지 않는다. DB 업그레이드와 재수집은 공고·알림·즐겨찾기·사용자 설정을 보존하며 샘플 데이터로 덮어쓰지 않는다.
- [목표] 감시 수집 시각·알림 생성 시각을 구분하고, 수동 재수집으로 감시 시각을 덮어쓰거나 과거 미기록 시각을 추정하지 않는다.
- [목표] 공고 데이터 CSV는 현재 필터·분류·정렬의 전체 결과를 내보내고 상세 추출 실패 공고도 포함한다.
- [목표] 화면 색상은 공통 테마 토큰, 글자는 기존 배율을 사용한다. 중복 스타일로 모드·글자 크기 설정을 덮어쓰지 않는다.
- 기존 DI 경로와 별개인 DI 프레임워크를 도입하지 않는다.
- 프로젝트 고유 함정: (사람이 작성)

## 8. 완료 조건
- 변경 범위에 맞는 §1의 확인 명령을 실행하고 결과를 보고한다. 명령이 미정이거나 실행할 수 없으면 그 사실을 남긴다.
- PC 변경에는 Python 테스트·JavaScript 구문 검사·배포판 GUI 중 변경 범위에 맞는 항목을 실행한다. UI는 격리 DB로 모든 메뉴·라이트/다크·900/1280px·80/100/140% 및 배포판 재실행을 확인한다.
- 새 순수 규칙에는 I/O 없는 단위 테스트를 둔다.
- §2·§4 밖의 위치나 역할을 만들지 않는다.
- 모듈·의존성·명령·경로 변경 시 AGENTS.md 개정을 요청한다.

## 9. 멈추고 물어볼 때
- [목표] (R10) §2에 없는 역할·위치나 새 계층·모듈이 필요하면 구현 전에 보고한다.
- [목표] (R12) 설계·리팩터링 제안에는 책임·의존성 변화와 동작 보존 테스트를 함께 제시한다.
- 새 외부 의존성, 저장 형식, 외부 계약을 바꿀 때
- §6 예외를 추가할 때
- 데이터 삭제처럼 되돌릴 수 없는 작업을 할 때
