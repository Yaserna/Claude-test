pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.PREFER_SETTINGS)
    repositories {
        google()
        mavenCentral()
        // محل قرارگیری AAR موتور مجازی‌سازی (NewBlackbox)
        flatDir { dirs("app/libs") }
    }
}

rootProject.name = "InfinityClone"
include(":app")
