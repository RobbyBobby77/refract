#version 440
// Content-layer material: a translucent rounded card with a lit hairline
// rim. It does not sample the backdrop (it lives inside the layered scene),
// so it is cheap and safe to use anywhere.

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;

layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec2 itemSize;
    float radius;
    float specular;
    vec4 fill;          // non-premultiplied rgba
    vec4 fillBottom;    // gradient end colour
    vec4 rimColor;      // rgb + alpha
};

float sdRoundBox(vec2 p, vec2 b, float r)
{
    vec2 q = abs(p) - b + vec2(r);
    return min(max(q.x, q.y), 0.0) + length(max(q, 0.0)) - r;
}

void main()
{
    vec2 halfSize = itemSize * 0.5;
    vec2 p = qt_TexCoord0 * itemSize - halfSize;
    float r = min(radius, min(halfSize.x, halfSize.y));
    float d = sdRoundBox(p, halfSize, r);

    vec2 e = vec2(0.5, 0.0);
    vec2 g = vec2(sdRoundBox(p + e.xy, halfSize, r) - sdRoundBox(p - e.xy, halfSize, r),
                  sdRoundBox(p + e.yx, halfSize, r) - sdRoundBox(p - e.yx, halfSize, r));
    vec2 n = dot(g, g) > 1e-8 ? normalize(g) : vec2(0.0, -1.0);

    vec4 base = mix(fill, fillBottom, qt_TexCoord0.y);
    vec3 col = base.rgb * base.a;
    float a = base.a;

    float inside = max(-d, 0.0);
    vec2 L = normalize(vec2(-0.55, -0.85));
    float facing = dot(n, L);
    float hair = 1.0 - smoothstep(0.0, 1.25, inside);
    float rim = hair * (0.18 + 0.82 * pow(abs(facing), 1.8)) * rimColor.a * specular;
    col += rimColor.rgb * rim;
    a = max(a, rim);

    float cover = clamp(0.5 - d, 0.0, 1.0);
    fragColor = vec4(col, a) * cover * qt_Opacity;
}
