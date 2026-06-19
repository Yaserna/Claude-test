package top.niunaijun.blackbox.fake.service;

import black.android.hardware.biometrics.BRIAuthServiceStub;
import black.android.os.BRServiceManager;
import top.niunaijun.blackbox.fake.hook.BinderInvocationStub;
import top.niunaijun.blackbox.fake.service.base.PkgMethodProxy;

/**
 * پروکسی سرویس بیومتریک مدرن (BiometricManager / BiometricPrompt).
 *
 * اپ‌های امروزی به‌جای FingerprintManager قدیمی از BiometricPrompt استفاده می‌کنند
 * که پشت آن سرویس "auth" (android.hardware.biometrics.IAuthService) قرار دارد.
 * این سرویس در موتور هوک نشده بود، برای همین اثر انگشت در فضای مجازی کار نمی‌کرد.
 *
 * مثل پروکسی اثر انگشت، نام پکیج (opPackageName) را با پکیج میزبان جایگزین می‌کنیم
 * تا سیستم تماس را بپذیرد و پنجره‌ی بیومتریک نمایش داده شود.
 */
public class IAuthServiceProxy extends BinderInvocationStub {
    // Context.AUTH_SERVICE یک ثابت مخفی (@hide) است و در SDK عمومی نیست؛
    // برای همین مقدار رشته‌ای آن را مستقیم استفاده می‌کنیم.
    private static final String AUTH_SERVICE = "auth";

    public IAuthServiceProxy() {
        super(BRServiceManager.get().getService(AUTH_SERVICE));
    }

    @Override
    protected Object getWho() {
        return BRIAuthServiceStub.get().asInterface(BRServiceManager.get().getService(AUTH_SERVICE));
    }

    @Override
    protected void inject(Object baseInvocation, Object proxyInvocation) {
        replaceSystemService(AUTH_SERVICE);
    }

    @Override
    public boolean isBadEnv() {
        return false;
    }

    @Override
    protected void onBindMethod() {
        super.onBindMethod();
        addMethodHook(new PkgMethodProxy("canAuthenticate"));
        addMethodHook(new PkgMethodProxy("hasEnrolledBiometrics"));
        addMethodHook(new PkgMethodProxy("authenticate"));
        addMethodHook(new PkgMethodProxy("cancelAuthentication"));
        addMethodHook(new PkgMethodProxy("getAuthenticatorIds"));
        addMethodHook(new PkgMethodProxy("getLastAuthenticationTime"));
    }
}
