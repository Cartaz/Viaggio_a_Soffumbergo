shader_type spatial;
render_mode cull_disabled;

// The mesh stays allocated. Only 35 transforms and four arm capsules are uploaded.
uniform mat4 skin_matrices[35];
uniform mat4 torso;
uniform mat4 torso_inverse;
uniform vec4 capsule_a[4];
uniform vec4 capsule_b[4];
uniform vec4 cape_color : source_color = vec4(0.31, 0.12, 0.39, 1.0);

void vertex() {
	mat4 skin = skin_matrices[int(CUSTOM0.x)] * CUSTOM1.x
		+ skin_matrices[int(CUSTOM0.y)] * CUSTOM1.y
		+ skin_matrices[int(CUSTOM0.z)] * CUSTOM1.z
		+ skin_matrices[int(CUSTOM0.w)] * CUSTOM1.w;
	vec3 p = (skin * vec4(VERTEX, 1.0)).xyz;
	vec3 n = normalize(mat3(skin) * NORMAL);
	vec3 radii = vec3(0.137, 0.17, 0.122);
	for (int iteration = 0; iteration < 6; iteration++) {
		bool changed = false;
		vec3 local = (torso_inverse * vec4(p, 1.0)).xyz - vec3(0.0, 0.42, 0.0);
		vec3 unit = local / radii;
		if (dot(unit, unit) < 1.0) {
			unit = length(unit) > 0.000001 ? normalize(unit) : vec3(0.0, 1.0, 0.0);
			p = (torso * vec4(vec3(0.0, 0.42, 0.0) + unit * radii, 1.0)).xyz;
			n = normalize(mat3(torso) * (unit / radii));
			changed = true;
		}
		for (int c = 0; c < 4; c++) {
			vec3 a = capsule_a[c].xyz;
			vec3 segment = capsule_b[c].xyz - a;
			float t = clamp(dot(p - a, segment) / max(dot(segment, segment), 0.000001), 0.0, 1.0);
			vec3 q = a + segment * t;
			vec3 offset = p - q;
			float radius = capsule_a[c].w;
			if (dot(offset, offset) < radius * radius) {
				vec3 direction = length(offset) > 0.000001 ? normalize(offset) : vec3(q.x > 0.0 ? 1.0 : -1.0, 0.0, 0.0);
				p = q + direction * (radius + 0.001);
				n = direction;
				changed = true;
			}
		}
		if (!changed) { break; }
	}
	vec3 radial = (torso_inverse * vec4(p, 1.0)).xyz - vec3(0.0, 0.42, 0.0);
	radial.y = 0.0;
	vec3 escape = mat3(torso) * normalize(radial);
	for (int iteration = 0; iteration < 4; iteration++) {
		bool escaped = false;
		for (int c = 0; c < 4; c++) {
			vec3 a = capsule_a[c].xyz;
			vec3 segment = capsule_b[c].xyz - a;
			float t = clamp(dot(p - a, segment) / max(dot(segment, segment), 0.000001), 0.0, 1.0);
			float radius = capsule_a[c].w;
			if (length(p - a - segment * t) >= radius) { continue; }
			vec3 offset = p - a - segment * 0.5;
			radius += length(segment) * 0.5;
			float along = dot(offset, escape);
			float exit_distance = -along + sqrt(max(0.0, along * along - dot(offset, offset) + radius * radius));
			p += escape * (exit_distance + 0.001);
			n = escape;
			escaped = true;
		}
		if (!escaped) { break; }
	}
	VERTEX = p;
	NORMAL = n;
}

void fragment() {
	ALBEDO = cape_color.rgb;
	ROUGHNESS = 0.78;
}
