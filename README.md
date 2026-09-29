# Saramin AI Finder 🚀

사람인 채용공고 크롤링 및 기술 스택 분석 프로젝트입니다. 기존 Android 앱과 별도의 Windows PC 앱을 포함합니다.

## Windows PC 앱

PC 앱은 공고 목록과 읽을 수 있는 상세 텍스트를 SQLite에 누적 저장합니다. 자격요건과 우대사항을 각각 분리해 검색·기술 키워드별 공고 수 분석·CSV 내보내기를 할 수 있습니다. 여러 검색어의 감시 조건을 저장하고 **감시 시작**을 누르면 즉시 한 번, 이후 설정한 간격마다 앱 실행 중 자동 확인합니다. 앱을 다시 열면 감시는 중지 상태이며 다시 시작해야 합니다. 수집·감시 작업마다 통계형 Windows/앱 내 팝업을 한 번 표시하며 공고별 알림 이력은 별도로 보관합니다.

설치 없는 배포물은 `desktop/dist/SaraminFinder/실행.bat`로 시작합니다. Python은 배포 폴더에 포함되며 사용 중 빈 CMD 창이 남지 않습니다. 데이터는 `%LOCALAPPDATA%\SaraminAIFinder\jobs.sqlite3`에 보관됩니다. 배포물 생성 및 개발·검증 방법은 [PC 앱 안내](desktop/README.md)를 참조하세요.

초기 검색 조건은 서울 전체, 신입~경력 3년, 학력무관/4년제 대졸 이상이며 `AI` 감시 조건이 기본 등록됩니다. PC 앱의 **공고 감시 → 공통 검색 조건**에서 지역·경력·학력을 변경하고, 감시 조건의 **수정** 버튼에서 검색어·간격을 변경할 수 있습니다.

**수집 작업**에서는 매번 별도의 지역·경력·학력 조건을 선택할 수 있습니다. **공고 데이터**에는 공고등록일·채용마감일·사람인 원본 링크가 표시되며 등록일과 D-Day 기준으로 정렬할 수 있습니다. 상세한 날짜 처리 기준은 [PC 앱 안내](desktop/README.md)를 참조하세요.

공고 데이터와 요건 분석에서는 분야·경력·기술을 각각 여러 개 선택해 조회할 수 있습니다. 분야는 쉼표로 나눈 키워드를 별도로 저장합니다. **설정**에서는 제공된 Pretendard 폰트를 사용하는 전체 화면 글자 크기를 80~140%로 조절할 수 있습니다.

**공고 감시**의 새 공고 알림과 **요건 분석** 결과에서는 공고 상세와 사람인 원본 링크를 각각 열 수 있습니다.

아래 내용은 기존 Android 앱에 관한 안내입니다.

## ✨ 주요 기능 (Features)

*   **스마트 기술 스택 분석 및 통계**: 
    *   공고를 탭하면 백그라운드에서 공고 상세 페이지의 텍스트(자격요건/우대사항)를 파싱하여 AI, Backend, Cloud 등 36종의 주요 기술 스택(Python, Kotlin, AWS, RAG 등)을 추출합니다.
    *   한국어/영어 동의어를 정규식으로 정밀하게 매핑하여(예: '파이썬' -> 'Python'), 내가 열람한 공고들의 기술 스택 빈도수 누적 통계를 차트로 제공합니다.
*   **사람인 공식 앱 다이렉트 딥링킹 (Deep Linking)**: 
    *   기기에 설치된 사람인 공식 앱의 해당 공고 상세 화면으로 즉시 진입합니다.
*   **오프라인 캐싱 (Local Caching)**: 수집된 공고 목록과 기술 스택 조회 통계는 로컬 JSON 파일로 안전하게 영속화되어, 앱을 껐다 켜도 데이터가 유지되며 불필요한 네트워크 통신을 방지합니다.

## 🛠️ 기술 스택 (Tech Stack)

*   **언어**: Kotlin 
*   **UI Toolkit**: Jetpack Compose (Material Design 3)
*   **아키텍처**: MVVM (Model-View-ViewModel) 패턴
*   **비동기 처리**: Kotlin Coroutines & Flow
*   **의존성 주입**: Dagger-Hilt
*   **네트워크 & 크롤링**: Jsoup (HTML DOM Parsing)
*   **직렬화**: Kotlinx-serialization (JSON 로컬 캐싱)
*   **테스트**: JUnit4

## 📂 프로젝트 구조 (Architecture)

단일 책임 원칙(SRP)을 준수하여 철저히 분리된 구조를 가집니다.

```
com.peanutbutter1001.saramin_ai_finder
│
├── data/
│   ├── model/         # JobItem, JobDetails, StatsData (데이터 모델 클래스)
│   └── repository/    # SaraminRepository (캐시 관리 및 Jsoup 네트워크 크롤링 담당)
│
├── di/                # RepositoryModule (Hilt 의존성 주입 모듈)
│
├── navigation/        # AppNavHost, AppDestinations (Compose 화면 네비게이션)
│
├── ui/
│   ├── components/    # JobCard, BadgeTag 등 재사용 가능한 순수 UI 컴포넌트 모음
│   ├── screens/       # Home, Stats 화면 및 각 ViewModel (UI 상태 관리)
│   └── theme/         # Color, Theme, Type (다크 네온 테마 디자인 시스템)
│
└── utils/
    ├── HtmlParser.kt  # DOM 파싱 및 문자열 추출 유틸리티
    ├── IntentUtils.kt # 사람인 공식 앱 다이렉트 딥링크 라우팅 유틸리티
    └── TechKeywords.kt# 36종의 다국어 기술 스택 정규식 매핑 상수
```

## 🚀 시작하기 (Getting Started)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/PEANUTBUTTER1001/saramin-ai-finder.git
   ```
2. **Open in Android Studio:** 안드로이드 스튜디오 (Ladybug 이상 권장)에서 프로젝트를 엽니다.
3. **Build and Run:** 기기나 에뮬레이터에 빌드하여 실행합니다. 
   *(딥링크 기능 테스트를 위해서는 안드로이드 기기 또는 에뮬레이터에 '사람인(kr.co.saramin.brandapp)' 앱이 설치되어 있어야 합니다.)*

