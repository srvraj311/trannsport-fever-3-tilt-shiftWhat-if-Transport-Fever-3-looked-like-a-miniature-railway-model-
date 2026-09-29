
// ---- srvraj311_tiltshift: colour boost and screen-band blur (inserted into shaders/hdr/compose.fs by tools/build.py) -------
// Colour boost: a little more saturation and contrast, like a photographed model.
const float TS_SATURATION = 0.15;
const float TS_CONTRAST   = 0.06;

vec3 tsGrade(vec3 c) {
	float l = dot(c, vec3(0.2126, 0.7152, 0.0722));
	c = mix(vec3(l), c, 1.0 + TS_SATURATION);
	c = (c - 0.5) * (1.0 + TS_CONTRAST) + 0.5;
	return clamp(c, 0.0, 1.0);
}

// Simple (fallback) tilt-shift: no depth, a sharp horizontal band with blur towards the top and bottom of the screen.
const float TS_BAND_CENTER   = 0.5;   // screen height of the sharp band's centre (0 = one edge, 1 = the other)
const float TS_BAND_HALF     = 0.12;  // half height of the fully sharp band
const float TS_BAND_SOFT     = 0.30;  // distance over which it fades to full blur
const float TS_BAND_MAX_BLUR = 10.0;  // blur radius, in pixels of a 1080p screen

vec3 tsBandBlur(vec2 uv) {
	vec3 base = texture(texFramebuf, uv).rgb;
	float r = smoothstep(TS_BAND_HALF, TS_BAND_HALF + TS_BAND_SOFT, abs(uv.y - TS_BAND_CENTER)) * TS_BAND_MAX_BLUR;
	if (r < 0.5) {
		return base;
	}
	vec2 size = vec2(textureSize(texFramebuf, 0));
	vec2 px = vec2(size.y / size.x, 1.0) / 1080.0 * r;
	vec3 acc = base;
	for (int i = 1; i <= 24; ++i) {
		float f = sqrt(float(i) / 24.0);
		float a = float(i) * 2.39996323;
		acc += texture(texFramebuf, uv + vec2(cos(a), sin(a)) * px * f).rgb;
	}
	return acc / 25.0;
}

