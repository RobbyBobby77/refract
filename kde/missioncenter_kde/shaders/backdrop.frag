#version 440
// Window backdrop, clipped to the rounded window shape. Modes:
//   0  desktop wallpaper, blurred and tinted (macOS "desktop tinting")
//   1  procedural aurora gradient (fallback when there's no wallpaper)
//   2  flat fill – translucent over KWin's blur-behind ("glass") or opaque
// A hairline rim along the edge gives the window a crisp, lit outline.

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;

layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec2 itemSize;
    vec2 imageSize;
    float radius;
    float blurBias;
    float mode;
    float saturation;
    float grain;
    vec4 overlay;       // rgb + amount, laid over image/aurora
    vec4 fillTop;       // flat mode: rgba, non-premultiplied
    vec4 fillBottom;
    vec4 rim;           // rgb + alpha of the edge highlight
    vec4 c1;
    vec4 c2;
    vec4 c3;
    vec4 c4;
};

layout(binding = 1) uniform sampler2D source;

float sdRoundBox(vec2 p, vec2 b, float r)
{
    vec2 q = abs(p) - b + vec2(r);
    return min(max(q.x, q.y), 0.0) + length(max(q, 0.0)) - r;
}

float hash(vec2 p)
{
    return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
}

vec3 blob(vec2 uv, vec2 c, float s, vec3 color)
{
    float d = length((uv - c) * vec2(1.0, 1.25));
    return color * exp(-d * d / (s * s));
}

void main()
{
    vec2 halfSize = itemSize * 0.5;
    vec2 p = qt_TexCoord0 * itemSize - halfSize;
    float d = sdRoundBox(p, halfSize, min(radius, min(halfSize.x, halfSize.y)));
    float cover = clamp(0.5 - d, 0.0, 1.0);
    float dither = (hash(qt_TexCoord0 * itemSize) - 0.5) * grain;

    vec3 col;
    float alpha = 1.0;
    if (mode > 1.5) {
        vec4 f = mix(fillTop, fillBottom, qt_TexCoord0.y);
        col = f.rgb + dither;
        alpha = f.a;
    } else {
        if (mode < 0.5) {
            // "cover" fit of the wallpaper into the window
            float itemAspect = itemSize.x / max(itemSize.y, 1.0);
            float imgAspect = imageSize.x / max(imageSize.y, 1.0);
            vec2 scale = itemAspect > imgAspect ? vec2(1.0, imgAspect / itemAspect)
                                                : vec2(itemAspect / imgAspect, 1.0);
            vec2 uv = (qt_TexCoord0 - 0.5) * scale + 0.5;
            const float GOLDEN = 2.39996323;
            vec3 acc = vec3(0.0);
            float wsum = 0.0;
            for (int i = 0; i < 16; ++i) {
                float fi = float(i) + 0.5;
                float rr = sqrt(fi / 16.0) * 0.035;
                vec2 o = vec2(cos(fi * GOLDEN), sin(fi * GOLDEN)) * rr * scale;
                float w = 1.0 - 0.5 * fi / 16.0;
                acc += texture(source, uv + o, blurBias).rgb * w;
                wsum += w;
            }
            col = acc / wsum;
        } else {
            vec2 uv = qt_TexCoord0;
            col = c4.rgb;
            col += blob(uv, vec2(0.12, 0.18), 0.55, c1.rgb);
            col += blob(uv, vec2(0.92, 0.10), 0.50, c2.rgb);
            col += blob(uv, vec2(0.70, 0.95), 0.60, c3.rgb);
            col += blob(uv, vec2(0.25, 0.90), 0.35, c2.rgb * 0.6);
        }
        float luma = dot(col, vec3(0.2126, 0.7152, 0.0722));
        col = mix(vec3(luma), col, saturation);
        col = mix(col, overlay.rgb, overlay.a) + dither;
    }

    // Lit hairline just inside the edge, strongest along the top.
    float inside = max(-d, 0.0);
    float hair = (1.0 - smoothstep(0.0, 1.2, inside)) * rim.a * (0.55 + 0.45 * (1.0 - qt_TexCoord0.y));
    vec3 premul = col * alpha + rim.rgb * hair;
    float a = max(alpha, hair);

    fragColor = vec4(premul, a) * cover * qt_Opacity;
}
