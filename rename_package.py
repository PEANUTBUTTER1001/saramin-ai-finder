import os
import sys
import shutil

# Windows 콘솔(cp949 등)에서 한글/기호 출력이 깨지거나 크래시나는 것 방지
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


# 치환/이동에서 건드리면 안 되는 디렉토리 (경로 세그먼트 단위로 정확히 매칭)
# 주의: 'build' 만 스킵하고 'build-logic'(소스)은 스킵하지 않도록 세그먼트 비교 사용
SKIP_DIRS = {'.git', '.gradle', 'build', '.idea', '.omc'}

# 내부 문자열 치환 대상 확장자
EXTENSIONS = ('.kt', '.xml', '.kts', '.gradle', '.properties', '.json', '.pro', '.md')


def to_pascal(name):
    """kebab/snake 표기를 PascalCase 로 변환. android-base-template -> AndroidBaseTemplate"""
    parts = name.replace('-', ' ').replace('_', ' ').split()
    return ''.join(p[:1].upper() + p[1:] for p in parts)


def should_skip(dirpath):
    parts = dirpath.replace('\\', '/').split('/')
    return any(seg in SKIP_DIRS for seg in parts)


def replace_text_in_file(file_path, replacements):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        original = content
        for old, new in replacements:
            content = content.replace(old, new)
        if content != original:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  수정: {file_path}")
    except Exception as e:
        print(f"파일 수정 실패: {file_path} - {e}")


def rename_package(root_dir, old_pkg, new_pkg, old_name, new_name):
    old_pascal = to_pascal(old_name)
    new_pascal = to_pascal(new_name)

    # 치환 순서: 세 문자열은 표기법이 서로 달라(snake/kebab/Pascal) 겹치지 않으므로 순서 무관하게 안전
    replacements = [
        (old_pkg, new_pkg),        # 1) 패키지명 (점 표기)  : package/import, namespace, applicationId
        (old_name, new_name),      # 2) 표시명 (kebab)      : rootProject.name, app_name
        (old_pascal, new_pascal),  # 3) 심볼 (PascalCase)   : Application 클래스, Compose 테마 함수, XML 스타일명
    ]

    print("적용할 치환:")
    for o, n in replacements:
        print(f"  {o}  ->  {n}")

    # [1/3] 파일 내부 문자열 치환
    print("\n[1/3] 파일 내부 문자열 치환 중...")
    for dirpath, _, filenames in os.walk(root_dir):
        if should_skip(dirpath):
            continue
        for filename in filenames:
            if filename.endswith(EXTENSIONS):
                replace_text_in_file(os.path.join(dirpath, filename), replacements)

    # [2/3] PascalCase 를 포함한 파일명 변경 (예: AndroidBaseTemplateApplication.kt)
    print("\n[2/3] 파일명 변경 중...")
    for dirpath, _, filenames in os.walk(root_dir):
        if should_skip(dirpath):
            continue
        for filename in filenames:
            if old_pascal in filename:
                src = os.path.join(dirpath, filename)
                dst = os.path.join(dirpath, filename.replace(old_pascal, new_pascal))
                os.rename(src, dst)
                print(f"  이름변경: {filename} -> {os.path.basename(dst)}")

    # [3/3] 물리 폴더 구조 변경 (패키지 경로)
    print("\n[3/3] 소스 폴더 구조 변경 중...")
    old_path_part = old_pkg.replace('.', os.sep)
    new_path_part = new_pkg.replace('.', os.sep)
    source_roots = [
        'app/src/main/java', 'app/src/androidTest/java', 'app/src/test/java',
        'app/src/main/kotlin', 'app/src/androidTest/kotlin', 'app/src/test/kotlin',
    ]
    for target_base in source_roots:
        base_dir = os.path.join(root_dir, target_base)
        if not os.path.exists(base_dir):
            continue

        old_full_path = os.path.join(base_dir, old_path_part)
        new_full_path = os.path.join(base_dir, new_path_part)

        if os.path.exists(old_full_path):
            os.makedirs(os.path.dirname(new_full_path), exist_ok=True)
            shutil.copytree(old_full_path, new_full_path, dirs_exist_ok=True)
            shutil.rmtree(old_full_path)

            # 찌꺼기 빈 폴더 청소
            current_dir = os.path.dirname(old_full_path)
            while current_dir != base_dir and os.path.exists(current_dir) and not os.listdir(current_dir):
                os.rmdir(current_dir)
                current_dir = os.path.dirname(current_dir)

    print("\n[완료] 변경 완료! Android Studio에서 'Sync Project with Gradle Files' 를 실행하세요.")


if __name__ == "__main__":
    # 사용법: python rename_package.py <기존패키지> <새패키지> <기존표시명> <새표시명>
    if len(sys.argv) < 5:
        print("[사용법] python rename_package.py <기존패키지> <새패키지> <기존표시명> <새표시명>")
        print("[예시]")
        print("   python rename_package.py \\")
        print("       com.peanutbutter1001.android_base_template com.mycompany.myapp \\")
        print("       android-base-template my-app")
        sys.exit(1)

    old_package = sys.argv[1]
    new_package = sys.argv[2]
    old_display = sys.argv[3]
    new_display = sys.argv[4]
    rename_package(os.getcwd(), old_package, new_package, old_display, new_display)
