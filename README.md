# Saramin AI Finder 🚀

사람인 채용공고 크롤링 및 기술 스택 분석 안드로이드 앱입니다.

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

