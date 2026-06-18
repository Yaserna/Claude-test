pluginManagement {
    repositories {
        maven { url = uri("https://www.jitpack.io") }
        google {
            content {
                includeGroupByRegex("com\\.android.*")
                includeGroupByRegex("com\\.google.*")
                includeGroupByRegex("androidx.*")
            }
        }
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.PREFER_SETTINGS)
    repositories {
        maven { url = uri("https://www.jitpack.io") }
        google()
        mavenCentral()
    }
}

rootProject.name = "InfinityClone"

include(":app")
include(":Bcore")
include(":black-reflection")
include(":compiler")
