package black.android.hardware.fingerprint;

import android.os.IBinder;
import android.os.IInterface;

import top.niunaijun.blackreflection.annotation.BClassName;
import top.niunaijun.blackreflection.annotation.BStaticMethod;

@BClassName("android.hardware.fingerprint.IFingerprintService")
public interface IFingerprintService {
    @BClassName("android.hardware.fingerprint.IFingerprintService$Stub")
    interface Stub {
        @BStaticMethod
        IInterface asInterface(IBinder IBinder0);
    }
}
