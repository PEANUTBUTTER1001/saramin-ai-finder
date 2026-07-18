plugins {
    `kotlin-dsl`
}

group = "com.example.buildlogic"

dependencies {
    compileOnly(libs.android.gradlePlugin)
    compileOnly(libs.kotlin.gradlePlugin)
    compileOnly(libs.ksp.gradlePlugin)
    compileOnly(libs.hilt.gradlePlugin)
    compileOnly(libs.kotlin.serialization.gradlePlugin)
}

gradlePlugin {
    plugins {
        register("androidApplication") {
            id = "my.android.application"
            implementationClass = "AndroidApplicationConventionPlugin"
        }

        register("androidLibrary") {
            id = "my.android.library"
            implementationClass = "AndroidLibraryConventionPlugin"
        }

        register("androidCompose") {
            id = "my.android.compose"
            implementationClass = "AndroidComposeConventionPlugin"
        }

        register("androidHilt") {
            id = "my.android.hilt"
            implementationClass = "AndroidHiltConventionPlugin"
        }

        register("androidNavigation") {
            id = "my.android.navigation"
            implementationClass = "AndroidNavigationConventionPlugin"
        }
    }
}
