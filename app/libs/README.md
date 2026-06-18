# محل قرارگیری AAR موتور

فایل AAR موتور مجازی‌سازی (NewBlackbox/BlackBox) را اینجا بگذار، مثلاً:

```
app/libs/blackbox.aar
```

سپس در `app/build.gradle.kts` این خط را از حالت کامنت خارج کن:

```kotlin
implementation(files("libs/blackbox.aar"))
```

راهنمای کامل فعال‌سازی در `README.md` ریشه‌ی پروژه، بخش «افزودن موتور» آمده است.
