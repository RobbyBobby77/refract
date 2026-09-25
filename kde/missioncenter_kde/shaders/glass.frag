#version 440
// Liquid glass: a rounded slab of glass that frosts, saturates and bends the
// scene behind it. The rim behaves like a convex lens (content is pulled in
// and split into colour fringes), and a specular line catches the light on
// the upper-left and lower-right edges.

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 1) in vec2 screenUV;
layout(location = 0) out vec4 fragColor;

layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float flipY;
    vec2 itemSize;      // logical px
    vec2 sourceSize;    // logical px of the backdrop texture (the window)
    float radius;       // corner radius, px
    float bevel;        // width of the curved rim, px
    float refraction;   // max rim displacement, px
    float dispersion;   // chromatic split, 0..1
    float frost;        // blur radius, px
    float blurBias;     // mip bias for the frosted samples
    float saturation;   // vibrancy (1 = unchanged)
    float specular;     // rim highlight strength
    float shine;        // top sheen strength
    float press;        // 0..1 interaction glow
    vec4 tint;          // rgb + mix amount
    vec4 rimColor;      // rgb + alpha of the highlight
};

layout(binding = 1) uniform sampler2D source;

float sdRoundBox(vec2 p, vec2 b, float r)
{
    vec2 q = abs(p) - b + vec2(r);
    return min(max(q.x, q.y), 0.0) + length(max(q, 0.0)) - r;
}

vec4 frosted(vec2 uv, vec2 pxToUv, float amount)
{
    // Golden-angle spiral taps over a mip-biased lookup: a cheap, smooth
    // single-pass blur that still feels like thick frosted glass.
    const float GOLDEN = 2.39996323;
    vec4 acc = texture(source, uv, blurBias);
    float wsum = 1.0;
    for (int i = 0; i < 12; ++i) {
        float fi = float(i) + 0.5;
        float rr = sqrt(fi / 12.0) * amount;
        vec2 o = vec2(cos(fi * GOLDEN), sin(fi * GOLDEN)) * rr * pxToUv;
        float w = 1.0 - 0.6 * (fi / 12.0);
        acc += texture(source, uv + o, blurBias) * w;
        wsum += w;
    }
    return acc / wsum;
}

void main()
{
    vec2 halfSize = itemSize * 0.5;
    vec2 p = qt_TexCoord0 * itemSize - halfSize;
    float r = min(radius, min(halfSize.x, halfSize.y));
    float d = sdRoundBox(p, halfSize, r);

    // Outward surface normal from the distance field gradient.
    vec2 e = vec2(0.5, 0.0);
    vec2 g = vec2(sdRoundBox(p + e.xy, halfSize, r) - sdRoundBox(p - e.xy, halfSize, r),
                  sdRoundBox(p + e.yx, halfSize, r) - sdRoundBox(p - e.yx, halfSize, r));
    vec2 n = dot(g, g) > 1e-8 ? normalize(g) : vec2(0.0, -1.0);

    float inside = max(-d, 0.0);
    float bw = max(bevel, 1.0);
    float t = clamp(1.0 - inside / bw, 0.0, 1.0);          // 1 at the edge
    float lens = 1.0 - sqrt(max(1.0 - t * t, 0.0));        // quarter-circle rim profile

    vec2 pxToUv = 1.0 / max(sourceSize, vec2(1.0));
    vec2 disp = -n * refraction * lens * pxToUv;
    float fr = mix(frost, frost * 0.45, lens);            // crisper where the rim bends light

    // Sample each channel with a slightly different bend for dispersion.
    // Kept branch-free: implicit-derivative lookups inside a divergent branch
    // produce seams along the rim boundary.
    // The scene is premultiplied and may be translucent (over KWin's blur),
    // so alpha is carried through: the desktop keeps showing through.
    float k = dispersion * 0.35 * step(0.002, lens);
    vec4 mid = frosted(screenUV + disp, pxToUv, fr);
    vec4 s = vec4(frosted(screenUV + disp * (1.0 - k), pxToUv, fr).r, mid.g,
                  frosted(screenUV + disp * (1.0 + k), pxToUv, fr).b, mid.a);

    // Vibrancy on the unpremultiplied colour, then the material tint laid
    // over it as its own translucent layer.
    vec3 c = s.rgb / max(s.a, 1e-4);
    float luma = dot(c, vec3(0.2126, 0.7152, 0.0722));
    c = mix(vec3(luma), c, saturation);
    vec3 col = tint.rgb * tint.a + c * s.a * (1.0 - tint.a);
    float matter = tint.a + s.a * (1.0 - tint.a);

    // Specular rim: a hairline that is brightest where it faces the light,
    // plus a softer glow inside the bevel.
    vec2 L = normalize(vec2(-0.55, -0.85));
    float facing = dot(n, L);
    float hair = 1.0 - smoothstep(0.0, 1.35, inside);
    float rimLight = hair * (0.22 + 0.78 * pow(abs(facing), 1.6));
    float glow = lens * lens * (0.35 + 0.65 * max(facing, 0.0));
    col += rimColor.rgb * rimColor.a * specular * (rimLight + glow * 0.45);

    // Gentle sheen towards the top, and a lift when pressed.
    float sheen = 1.0 - smoothstep(0.0, 0.55, qt_TexCoord0.y);
    col += vec3(shine * 0.05 * sheen);
    col += vec3(press * 0.07);

    // Highlights are emitted light (added in premultiplied space).
    float cover = clamp(0.5 - d, 0.0, 1.0);
    fragColor = vec4(col, matter) * cover * qt_Opacity;
}
