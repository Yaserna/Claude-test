package top.niunaijun.blackbox.fake.service;

import android.content.Context;

import black.android.hardware.fingerprint.BRIFingerprintServiceStub;
import black.android.os.BRServiceManager;
import top.niunaijun.blackbox.fake.hook.BinderInvocationStub;
import top.niunaijun.blackbox.fake.service.base.PkgMethodProxy;


public class IFingerprintManagerProxy extends BinderInvocationStub {
    public IFingerprintManagerProxy() {
        super(BRServiceManager.get().getService(Context.FINGERPRINT_SERVICE));
    }

    @Override
    protected Object getWho() {
        // اینترفیس درست FingerprintService (قبلاً اشتباهاً IGraphicsStats بود که باعث
        // می‌شد هوک‌ها اعمال نشوند و اثر انگشت در فضای مجازی کار نکند).
        return BRIFingerprintServiceStub.get().asInterface(BRServiceManager.get().getService(Context.FINGERPRINT_SERVICE));
    }

    @Override
    protected void inject(Object baseInvocation, Object proxyInvocation) {
        replaceSystemService(Context.FINGERPRINT_SERVICE);
    }

    @Override
    public boolean isBadEnv() {
        return false;
    }

    @Override
    protected void onBindMethod() {
        super.onBindMethod();
        addMethodHook(new PkgMethodProxy("isHardwareDetected"));
        addMethodHook(new PkgMethodProxy("hasEnrolledFingerprints"));
        addMethodHook(new PkgMethodProxy("authenticate"));
        addMethodHook(new PkgMethodProxy("cancelAuthentication"));
        addMethodHook(new PkgMethodProxy("getEnrolledFingerprints"));
        addMethodHook(new PkgMethodProxy("getAuthenticatorId"));
    }
}
