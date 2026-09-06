plugins {
    kotlin("jvm") version "2.3.0"
    id("org.jetbrains.intellij.platform")
}

group = "de.kreisgeist"
version = "0.1.0-SNAPSHOT"

dependencies {
    implementation("com.google.code.gson:gson:2.13.1")
    testImplementation(kotlin("test"))
    intellijPlatform {
        intellijIdea("2026.2.0.1")
        bundledPlugin("com.intellij.java")
        pluginVerifier()
        zipSigner()
    }
}

kotlin {
    jvmToolchain(17)
}

intellijPlatform {
    pluginConfiguration {
        name = "AIDL Language Support"
        ideaVersion {
            sinceBuild = "253"
        }
    }
}

tasks.test {
    useJUnitPlatform()
}
