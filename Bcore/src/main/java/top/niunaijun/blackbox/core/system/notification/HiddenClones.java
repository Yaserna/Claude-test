package top.niunaijun.blackbox.core.system.notification;

import android.content.Context;
import android.content.SharedPreferences;

import java.util.Collections;
import java.util.HashSet;
import java.util.Set;

import top.niunaijun.blackbox.BlackBoxCore;

/**
 * کشِ حافظه‌ایِ فهرستِ کلون‌های مخفی، برای پروسه‌ی سرورِ موتور.
 *
 * وضعیتِ مخفی‌بودن را اپِ میزبان در SharedPreferences می‌نویسد. اگر این فایل را
 * روی «مسیرِ داغِ اعلان‌ها» بخوانیم، خواندنِ SharedPreferences از مسیرهای هوک‌شده‌ی
 * موتور عبور می‌کند و می‌تواند به بن‌بست برسد و اپِ مهمان (مثل تلگرام) را روی
 * صفحه‌ی لوگو هنگ کند. برای همین خواندن فقط روی یک نخِ پس‌زمینه‌ی throttled انجام
 * می‌شود و مسیرِ داغ فقط یک {@link Set} حافظه‌ای را می‌خواند (بدون هیچ I/O).
 *
 * اگر خواندنِ پس‌زمینه هم به هر دلیلی شکست بخورد، رفتار «fail-open» است: کش خالی
 * می‌ماند، اعلان‌ها مخفی نمی‌شوند، ولی هیچ اپی هرگز هنگ نمی‌کند.
 */
public final class HiddenClones {
    private static final String PREFS = "hidden_clones";
    private static final String KEY_SET = "hidden_keys";

    private static volatile Set<String> sHidden = Collections.emptySet();
    private static volatile boolean sStarted = false;

    private HiddenClones() {
    }

    /** آیا این کلون مخفی است؟ فقط از کشِ حافظه‌ای می‌خواند (بدون I/O). */
    public static boolean isHidden(String packageName, int userId) {
        ensureRefresher();
        return sHidden.contains(packageName + "@" + userId);
    }

    private static void ensureRefresher() {
        if (sStarted)
            return;
        synchronized (HiddenClones.class) {
            if (sStarted)
                return;
            sStarted = true;
        }
        Thread t = new Thread(new Runnable() {
            @Override
            public void run() {
                while (true) {
                    try {
                        Context ctx = BlackBoxCore.getContext();
                        // MODE_MULTI_PROCESS تا تغییراتِ نوشته‌شده توسط اپِ میزبان
                        // (پروسه‌ی دیگر) از دیسک دوباره خوانده شوند.
                        SharedPreferences sp =
                                ctx.getSharedPreferences(PREFS, Context.MODE_MULTI_PROCESS);
                        Set<String> set = sp.getStringSet(KEY_SET, null);
                        sHidden = (set == null) ? Collections.<String>emptySet()
                                : new HashSet<>(set);
                    } catch (Throwable ignored) {
                        // fail-open
                    }
                    try {
                        Thread.sleep(2000);
                    } catch (InterruptedException e) {
                        return;
                    }
                }
            }
        }, "hidden-clones-refresh");
        t.setDaemon(true);
        t.start();
    }
}
