
// ---- srvraj311_tiltshift PROBE: shows which passes run and whether depth decodes -----------------------------------------
// Right third green  = this pass (ssr_apply) runs with your settings.
// Middle third       = near things normal, far things (towards 2 km) turn blue: the depth buffer is read correctly.
void main() {
	ssrMain();
	if (texCoord.x > 0.667) {
		color.rgb *= vec3(0.55, 1.0, 0.55);
	} else if (texCoord.x > 0.333) {
		vec2 uv = texCoord;
#ifdef INVERT_FRAMEBUFFER_READ_Y
		uv.y = 1 - uv.y;
#endif
		float dist = -calcEyeZ(textureLod(depthBufTex, uv, 0.0).r);
		color.rgb *= mix(vec3(1.0), vec3(0.4, 0.4, 1.6), smoothstep(0.0, 2000.0, dist));
	}
}
