import kotlinx.kover.gradle.plugin.dsl.CoverageUnit

plugins {
    kotlin("multiplatform") version "2.3.0"
    id("org.jetbrains.kotlinx.kover") version "0.9.9"
}

group = "de.kreisgeist"
version = "0.1.0-SNAPSHOT"

repositories {
    mavenCentral()
}

kotlin {
    jvm()
    linuxX64 {
        binaries {
            executable {
                entryPoint = "de.kreisgeist.aidl.compiler.native.main"
            }
        }
    }

    sourceSets {
        commonTest.dependencies {
            implementation(kotlin("test"))
        }
    }
}

kover {
    reports {
        verify {
            rule {
                minBound(95, CoverageUnit.LINE)
                minBound(95, CoverageUnit.BRANCH)
            }
        }
    }
}
