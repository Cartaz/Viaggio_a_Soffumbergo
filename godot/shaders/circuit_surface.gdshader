shader_type spatial;
render_mode cull_back;

uniform vec4 surface_color : source_color = vec4(0.16, 0.17, 0.18, 1.0);
uniform float grain_scale = 70.0;
varying vec3 world_position;

float grain(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

void vertex() {
	world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec2 p = world_position.xz * grain_scale;
	float footprint = max(length(dFdx(p)), length(dFdy(p)));
	float aggregate = mix(0.5, grain(floor(p)), 1.0 - smoothstep(0.3, 1.0, footprint));
	float fine = mix(0.5, grain(floor(p * 3.0)), 1.0 - smoothstep(0.1, 0.333, footprint));
	ALBEDO = surface_color.rgb * (0.82 + 0.24 * aggregate + 0.06 * fine);
	ROUGHNESS = 0.96;
	METALLIC = 0.0;
	SPECULAR = 0.15;
}
