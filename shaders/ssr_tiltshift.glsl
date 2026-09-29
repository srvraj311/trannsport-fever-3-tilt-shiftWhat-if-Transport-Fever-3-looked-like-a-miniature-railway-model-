
// ---- srvraj311_tiltshift: distance-based tilt-shift depth of field (Cities: Skylines II style) ----------------------------
// Appended to the base game's shaders/misc/ssr_apply.fs by tools/build.py; the game's own main() is renamed ssrMain().
//
// 1. Focus: a near-weighted (soft minimum) average distance over 63 points in a patch below the screen centre (sky
//    ignored), so the nearest object in the patch - a train in front of a field - wins. A pole, wire or
//    gap passing through that patch moves the focus only a little, so the image does not flicker or pop.
// 2. Blur: by distance only, measured as log2(distance / focus) so it scales with the zoom. Separate near and far ranges
//    (like CS2's Near/Far Start/End): a sharp zone around the focus, then a smooth ramp to full blur. Behind the focus the
//    ramp is longer, so objects slightly further away stay clear.
// 3. Gather: 48 taps at FIXED screen offsets (a disk of the largest blur radius); the pixel's blur only fades taps in and out
//    by their distance, so the taps never slide across the image and fine detail does not shimmer while the blur changes.
//    Taps sharper than the pixel are ignored, so sharp poles and trees do not smear halos onto the background behind them.
//    (A true delay is impossible: the engine gives this pass no memory of earlier frames.)
// Tune the values below, then press Right Alt + T in game to reload shaders.

const float TS_MAX_BLUR = 9.75;    // largest blur radius, in pixels of a 1080p screen (scales with resolution)

// Focus patch (screen fractions; y from the top of the screen).
const float TS_FOCUS_X  = 0.5;
const float TS_FOCUS_Y  = 0.56;    // slightly below the centre: where followed vehicles and the ground ahead sit
const float TS_FOCUS_W  = 0.22;    // patch half width
const float TS_FOCUS_H  = 0.12;    // patch half height
const float TS_FOCUS_NEAR_BIAS = 1.6; // how strongly nearer surfaces win the focus (0 = plain average; 1.6 = half as far
                                    // counts ~3x as much), so a vehicle in front of a field is what gets focused

// Ranges in log2(distance / focus): 1.0 = twice as far (or half as far). Values blend from CLOSE to FAR with the zoom.
const float TS_ZOOM_CLOSE = 40.0;  // metres: focus at or below this uses the *_CLOSE values (vehicle follow, street level)
const float TS_ZOOM_FAR   = 400.0; // metres: focus at or beyond this uses the *_FAR values (normal city view)
const vec4  TS_RANGE_CLOSE = vec4(0.7, 1.3, 0.8, 2.0);  // near sharp, near ramp, far sharp, far ramp
const vec4  TS_RANGE_FAR   = vec4(0.3, 1.0, 0.4, 1.3);
const float TS_AMOUNT_CLOSE = 0.85;                     // overall strength zoomed in
const float TS_AMOUNT_FAR   = 1.0;                      // overall strength zoomed out

// Cab view: the camera looks almost level and the focus is close. There the bottom half of the screen (track and cab
// surroundings just ahead) is kept sharp. Both conditions fade in smoothly, so switching camera does not pop.
const float TS_CAB_PITCH_LEVEL = 0.10;  // sin(downward pitch) at or below which the camera counts as level (~6 degrees)
const float TS_CAB_PITCH_DOWN  = 0.25;  // ... and at or above which it does not (~14 degrees; follow and city cameras)
const float TS_CAB_FOCUS_NEAR  = 150.0; // metres: focus at or below this counts as close
const float TS_CAB_FOCUS_FAR   = 400.0;
const float TS_CAB_SPLIT       = 0.5;   // screen height (from the top) below which blur is removed
const float TS_CAB_SOFT        = 0.06;  // soft edge around that line

const int   TS_TAPS = 48;

float tsCab = 0.0;                 // 0..1, set in main()

// Blur multiplier for a screen height (from the top): 0 in the lower half while in cab view, else 1.
float tsKeep(float screenY) {
	return 1.0 - tsCab * smoothstep(TS_CAB_SPLIT - TS_CAB_SOFT, TS_CAB_SPLIT + TS_CAB_SOFT, screenY);
}

vec2 tsTex(vec2 screen) {          // screen position (y from the top) -> texture coordinate for colorTex / depthBufTex
#ifdef INVERT_FRAMEBUFFER_READ_Y
	screen.y = 1.0 - screen.y;
#endif
	return screen;
}

float tsRawDepth(vec2 tex) {
	return textureLod(depthBufTex, tex, 0.0).r;
}

float tsDist(float raw) {          // metres from the camera plane
	return -calcEyeZ(raw);
}

float tsFocus() {
	float sumLog = 0.0;
	float sumW = 0.0;
	for (int j = 0; j < 7; ++j) {
		for (int i = 0; i < 9; ++i) {
			vec2 o = vec2(float(i) / 4.0 - 1.0, float(j) / 3.0 - 1.0);   // -1..1 in both directions
			float d = tsDist(tsRawDepth(tsTex(vec2(TS_FOCUS_X, TS_FOCUS_Y) + o * vec2(TS_FOCUS_W, TS_FOCUS_H))));
			if (d > 0.5 * u_ssao.nearFar.y) {
				continue;                                                  // sky / far plane: nothing to focus on
			}
			float w = exp(-2.0 * dot(o, o));                               // centre counts most
			sumLog += w * exp2(-TS_FOCUS_NEAR_BIAS * log2(max(d, 1.0)));    // soft minimum: nearer counts more
			sumW += w;
		}
	}
	return sumW > 0.0 ? exp2(-log2(sumLog / sumW) / TS_FOCUS_NEAR_BIAS) : u_ssao.nearFar.y;
}

// Blur radius in 1080p pixels for a surface at dist.
float tsCoc(float dist, float focus, vec4 range, float amount) {
	float r = log2(max(dist, 1.0) / focus);
	float nearBlur = smoothstep(range.x, range.x + range.y, -r);
	float farBlur = smoothstep(range.z, range.z + range.w, r);
	return max(nearBlur, farBlur) * TS_MAX_BLUR * amount;
}

void main() {
	ssrMain();

	float focus = tsFocus();
	float zoom = smoothstep(TS_ZOOM_CLOSE, TS_ZOOM_FAR, focus);
	vec4 range = mix(TS_RANGE_CLOSE, TS_RANGE_FAR, zoom);
	float down = u_ssao.invViewMat[2].z;             // camera looks along -Z; in the z-up world this is sin(downward pitch)
	tsCab = (1.0 - smoothstep(TS_CAB_PITCH_LEVEL, TS_CAB_PITCH_DOWN, down)) *
			(1.0 - smoothstep(TS_CAB_FOCUS_NEAR, TS_CAB_FOCUS_FAR, focus));
	float amount = mix(TS_AMOUNT_CLOSE, TS_AMOUNT_FAR, zoom);

	vec2 tex = texCoord;
#ifdef INVERT_FRAMEBUFFER_READ_Y
	tex.y = 1.0 - tex.y;
#endif
	float coc = tsCoc(tsDist(tsRawDepth(tex)), focus, range, amount) * tsKeep(tsTex(tex).y);
	if (coc < 0.5) {
		return;
	}

	vec2 size = vec2(textureSize(colorTex, 0));
	vec2 px = vec2(size.y / 1080.0) / size;          // one 1080p pixel, in texture units
	vec3 acc = textureLod(colorTex, tex, 0.0).rgb;
	float tot = 1.0;
	for (int i = 1; i <= TS_TAPS; ++i) {
		float rt = sqrt(float(i) / float(TS_TAPS)) * TS_MAX_BLUR;   // tap radius, fixed (taps are sorted by radius)
		if (rt > coc + 1.0) {
			break;
		}
		float a = float(i) * 2.39996323;
		vec2 t = tex + vec2(cos(a), sin(a)) * rt * px;
		float sc = tsCoc(tsDist(tsRawDepth(t)), focus, range, amount) * tsKeep(tsTex(t).y);
		float w = clamp(coc - rt + 1.0, 0.0, 1.0)     // inside this pixel's blur disk (soft edge)
				* clamp(sc / coc, 0.0, 1.0);           // sharper neighbours (poles, trees in focus) do not bleed in
		acc += w * textureLod(colorTex, t, 0.0).rgb;
		tot += w;
	}
	color.rgb = mix(color.rgb, acc / tot, smoothstep(0.5, 2.0, coc));
}
