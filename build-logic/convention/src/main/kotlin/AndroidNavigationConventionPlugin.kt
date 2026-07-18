import org.gradle.api.Plugin
import org.gradle.api.Project
import org.gradle.api.artifacts.VersionCatalogsExtension
import org.gradle.kotlin.dsl.dependencies

/**
 * Type-safe Navigation(Navigation 3) 기본 설정 convention.
 *
 * - kotlin.plugin.serialization 을 적용해 @Serializable 라우트(NavKey) 를 지원한다.
 * - Nav3 런타임/UI/ViewModel 번들과 직렬화 런타임을 주입한다.
 *
 * Hilt 연동(hilt-navigation-compose)은 Hilt 에 종속되므로
 * AndroidHiltConventionPlugin 에서 담당한다.
 */
class AndroidNavigationConventionPlugin : Plugin<Project> {
    override fun apply(target: Project) {
        with(target) {
            pluginManager.apply("org.jetbrains.kotlin.plugin.serialization")

            val libs = extensions.getByType(VersionCatalogsExtension::class.java).named("libs")

            dependencies {
                add("implementation", libs.findBundle("navigation3").get())
                add("implementation", libs.findLibrary("kotlinx-serialization-json").get())
            }
        }
    }
}
