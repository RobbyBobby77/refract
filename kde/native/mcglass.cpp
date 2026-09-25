// C entry points used from Python through ctypes. The window pointer is the
// QWindow behind the PySide6 wrapper (shiboken6.getCppPointer).

#include <KWindowEffects>
#include <QRect>
#include <QRegion>
#include <QWindow>

namespace {
QRegion toRegion(const int *rects, int count)
{
    QRegion region;
    for (int i = 0; i < count; ++i)
        region += QRect(rects[4 * i], rects[4 * i + 1], rects[4 * i + 2], rects[4 * i + 3]);
    return region;
}
}

extern "C" {

// True when the compositor can blur behind windows (KWin with blur enabled).
Q_DECL_EXPORT bool mcglass_available()
{
    return KWindowEffects::isEffectAvailable(KWindowEffects::BlurBehind);
}

// Blur (and optionally tint the contrast of) what's behind `window`.
// `rects` holds `count` x,y,w,h quadruples in logical pixels; count == 0
// means the whole window.
Q_DECL_EXPORT void mcglass_apply(QWindow *window, bool enable, const int *rects, int count,
                                 double contrast, double intensity, double saturation)
{
    if (!window)
        return;
    const QRegion region = toRegion(rects, count);
    KWindowEffects::enableBlurBehind(window, enable, region);
    const bool withContrast = enable && KWindowEffects::isEffectAvailable(KWindowEffects::BackgroundContrast);
    KWindowEffects::enableBackgroundContrast(window, withContrast, contrast, intensity, saturation, region);
}

}
