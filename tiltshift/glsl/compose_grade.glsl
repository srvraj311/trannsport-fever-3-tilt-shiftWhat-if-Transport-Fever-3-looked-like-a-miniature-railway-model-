
// ---- srvraj311_tiltshift: colour boost ----------------------------------------------------------------------------------
// Inserted into the base game's shaders/hdr/compose.fs (final tone mapping) by the TF3 Tilt-Shift app; applied to the
// finished image, like a photographed model. The values written here are the app's defaults.
const float TS_SATURATION = 0.15;  // extra colour saturation
const float TS_CONTRAST   = 0.06;  // extra contrast around mid grey

vec3 tsGrade(vec3 c) {
	float l = dot(c, vec3(0.2126, 0.7152, 0.0722));
	c = mix(vec3(l), c, 1.0 + TS_SATURATION);
	c = (c - 0.5) * (1.0 + TS_CONTRAST) + 0.5;
	return clamp(c, 0.0, 1.0);
}

