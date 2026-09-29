# Saramin AI Finder — 에이전트 작업 규칙
사람인 채용공고 검색과 열람 공고의 기술 스택 통계를 제공하는 Android 앱과, 공고 누적 보관·요건 분석·신규 공고 감시를 제공하는 Windows PC 앱.
Source of Truth: `README.md`, `desktop/README.md`, `desktop/pyproject.toml`, `settings.gradle.kts`, `app/build.gradle.kts`, `gradle/libs.versions.toml`, `build-logic/convention/` · 이 문서는 사용자 승인을 받아서만 개정한다.

## 1. 명령
- 설치: (미정)
- 실행: (미정) — `README.md`는 Android Studio에서 빌드·실행하도록 안내한다.
- 테스트: `./gradlew.bat :app:testDebugUnitTest`
- 정적 검사: `./gradlew.bat :app:lintDebug`
- PC 테스트: `python -m pytest -q --basetemp desktop/.pytest-tmp desktop/tests`
- PC 화면 생성: `python desktop/tools/build_ui.py` — 프로토타입 레이아웃 변경을 반영할 때만 사용한다.
- PC 배포물 생성: `python desktop/packaging/build_portable.py` — Windows x64의 Python 3.12 개발 환경에서 실행한다.
- PC 실행: `desktop/dist/SaraminFinder/실행.bat` — 배포물 생성 후 실행한다.

## 2. 구조 지도
역할은 폴더 이름이 아니라 코드가 하는 일로 판단한다. Android 앱 코드는 `:app` 단일 모듈이다. PC 앱은 `desktop/`의 별도 Python 프로젝트다.

| 역할 | 경로 | 들어가는 것 |
|---|---|---|
| 진입 | `app/src/main/java/com/peanutbutter1001/saramin_ai_finder/MainActivity.kt`, `app/src/main/java/com/peanutbutter1001/saramin_ai_finder/navigation/`, `app/src/main/java/com/peanutbutter1001/saramin_ai_finder/ui/screens/`, `app/src/main/java/com/peanutbutter1001/saramin_ai_finder/ui/components/` | Android 진입, 화면 이동, 사용자 입력·UI 상태와 화면 컴포넌트 |
| 유스케이스 | (미정) | 별도 구현 없음. 흐름 분리가 필요할 때만 위치 결정 |
| 도메인 | `app/src/main/java/com/peanutbutter1001/saramin_ai_finder/data/model/`, `app/src/main/java/com/peanutbutter1001/saramin_ai_finder/utils/HtmlParser.kt`, `app/src/main/java/com/peanutbutter1001/saramin_ai_finder/utils/TechKeywords.kt` | 공고·통계 모델, 순수 파싱·필터·키워드 규칙 |
| 포트 | (미정) | 별도 인터페이스 없음. 외부 협력자를 분리할 때만 위치 결정 |
| 인프라 | `app/src/main/java/com/peanutbutter1001/saramin_ai_finder/data/repository/`, `app/src/main/java/com/peanutbutter1001/saramin_ai_finder/utils/IntentUtils.kt` | 사람인 네트워크·파일 캐시·통계 저장, 외부 앱·브라우저 Intent |
| 조립 | `app/src/main/java/com/peanutbutter1001/saramin_ai_finder/SaraminAiFinderApplication.kt`, `app/src/main/java/com/peanutbutter1001/saramin_ai_finder/di/` | Hilt 앱 및 저장소 제공 |
| 공유 | `app/src/main/java/com/peanutbutter1001/saramin_ai_finder/ui/theme/` | 테마와 시각 스타일 |
| 테스트 | `app/src/test/`, `app/src/androidTest/` | JVM 단위 테스트와 Android 계측 테스트 |
| PC 진입 | `desktop/src/saramin_finder/main.py`, `desktop/src/saramin_finder/ui/` | Qt 앱 시작, HTML 화면, 제한된 QWebChannel 브리지 |
| PC 유스케이스 | `desktop/src/saramin_finder/usecases/` | 수집 흐름과 CSV 분석 내보내기 |
| PC 도메인 | `desktop/src/saramin_finder/domain/` | 검색 프로필·공고·섹션 모델, 순수 검증·추출·키워드 규칙 |
| PC 인프라 | `desktop/src/saramin_finder/infrastructure/` | 사람인 HTTP/파싱, SQLite, 시각·파일 접근 |
| PC 조립 | `desktop/src/saramin_finder/main.py` | 저장소·화면·알림 연결 |
| PC 테스트·배포 | `desktop/tests/`, `desktop/packaging/` | Python 테스트와 설치 없는 `.bat` 배포 |

## 3. 의존 규칙
규칙은 §2의 역할을 기준으로 적용한다. 현재 단일 모듈에 역할 간 Gradle 경계 검사는 없다.
- [목표] (R1) 의존은 진입 → 유스케이스 → 도메인 방향으로 흐른다. 인프라는 포트를 구현하며, 도메인·포트는 진입·인프라·조립을 import하지 않는다. 현재 직접 인프라를 호출하는 진입 코드는 §6에 기록한다.
- [목표] (R2) 파일·DB·네트워크·IPC·시계·환경변수 접근은 인프라와 조립에서만 한다.
- [목표] PC의 HTML 화면은 사이트·DB에 직접 접근하지 않고, 앱에 포함된 로컬 페이지와 제한된 QWebChannel 명령만 사용한다.
- [목표] (R3) 구현체 생성과 연결은 조립에서만 한다. 그 밖의 코드는 협력자를 생성자 또는 DI로 받는다.
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
| PC 화면 및 Qt 브리지 | `desktop/src/saramin_finder/ui/` |
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

## 7. 하지 말 것
- [목표] (R7) 인터페이스·유스케이스·모듈·공통 컴포넌트는 구현이 2개 이상이거나 테스트 대역이 실제로 필요할 때만 만들고, 추가할 때 해결할 문제를 밝힌다.
- [목표] (R11) 요청된 구현에 필요한 변경만 한다. 범위 밖의 큰 리팩터링은 별도 제안으로 분리한다.
- 유스케이스 위에 서비스 계층을 더하지 않는다.
- 미래를 위한 인터페이스·기반 클래스·범용 헬퍼를 만들지 않는다.
- PC 배포 폴더와 개발용 내려받은 의존성은 Git에 포함하지 않는다. 사용자 공고 DB를 앱 업데이트 중 삭제하거나 샘플 데이터로 덮어쓰지 않는다.
- 기존 DI 경로와 별개인 DI 프레임워크를 도입하지 않는다.
- 프로젝트 고유 함정: (사람이 작성)

## 8. 완료 조건
- 변경 범위에 맞는 §1의 확인 명령을 실행하고 결과를 보고한다. 명령이 미정이거나 실행할 수 없으면 그 사실을 남긴다.
- PC 변경에는 Python 테스트, JavaScript 구문 검사, 배포판 GUI 스모크 검사 중 변경 범위에 맞는 항목을 실행한다.
- 새 순수 규칙에는 I/O 없는 단위 테스트를 둔다.
- §2·§4 밖의 위치나 역할을 만들지 않는다.
- 모듈·의존성·명령·경로 변경 시 AGENTS.md 개정을 요청한다.

## 9. 멈추고 물어볼 때
- [목표] (R10) §2에 없는 역할·위치나 새 계층·모듈이 필요하면 구현 전에 보고한다.
- [목표] (R12) 설계·리팩터링 제안에는 책임·의존성 변화와 동작 보존 테스트를 함께 제시한다.
- 새 외부 의존성, 저장 형식, 외부 계약을 바꿀 때
- §6 예외를 추가할 때
- 데이터 삭제처럼 되돌릴 수 없는 작업을 할 때
