#version 440
// Glass vertex stage: besides the usual texture coordinate we derive
// where this fragment lands in the window, so the fragment stage can sample
// the (layered) scene that sits behind the glass without any QML-side
// mapToItem() bookkeeping.

layout(location = 0) in vec4 qt_Vertex;
layout(location = 1) in vec2 qt_MultiTexCoord0;

layout(location = 0) out vec2 qt_TexCoord0;
layout(location = 1) out vec2 screenUV;

layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float flipY;
    vec2 itemSize;
    vec2 sourceSize;
    float radius;
    float bevel;
    float refraction;
    float dispersion;
    float frost;
    float blurBias;
    float saturation;
    float specular;
    float shine;
    float press;
    vec4 tint;
    vec4 rimColor;
};

out gl_PerVertex { vec4 gl_Position; };

void main()
{
    qt_TexCoord0 = qt_MultiTexCoord0;
    gl_Position = qt_Matrix * qt_Vertex;
    vec2 ndc = gl_Position.xy / gl_Position.w;
    screenUV = vec2(ndc.x * 0.5 + 0.5, 0.5 - ndc.y * 0.5 * flipY);
}
