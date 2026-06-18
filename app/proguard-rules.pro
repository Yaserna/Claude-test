# موتور مجازی‌سازی به‌شدت روی reflection و کلاس‌های داخلی تکیه دارد؛
# برای جلوگیری از خراب‌شدن در حالت release کل پکیج موتور را نگه می‌داریم.
-keep class top.niunaijun.blackbox.** { *; }
-keep class com.infinityclone.app.core.** { *; }
-dontwarn top.niunaijun.blackbox.**
