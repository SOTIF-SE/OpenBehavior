We use the following prompt template for all approaches. For each language and initial configuration, we fill in the corresponding inputs and supply the relevant documentation, examples, and behavior libraries. Each request generates one scenario script.

The five languages are those listed in `language.md`. The initial configurations are `s4_v1` … `s4_v10`, and the script produced by each request is kept under `scripts_with_setting/<language>/`, one file per configuration, named after its configuration ID.

Use [language] to write one executable scenario script for the following testing task.

**Testing task.** The scenario takes place on a three-lane road with traffic traveling in the same direction. An ego vehicle follows a specified route requiring a lane change to the left. Three NPC vehicles share the road. Describe their driving behaviors to support testing of the ego vehicle’s interactions with surrounding traffic.

**Environment and supplied materials.**

- Map and road segment: [value].
- Language documentation and examples: [materials].
- Available runtime, behavior libraries, and model interfaces: [materials].

**Initial configuration.** Configuration ID: [ID]. Positions, headings, and velocities use the coordinate system and units specified in [reference].

- Ego vehicle: [vehicle type, initial position, heading, initial state, route, and destination].
- NPC1: [vehicle type, initial position, heading, and velocity].
- NPC2: [vehicle type, initial position, heading, and velocity].
- NPC3: [vehicle type, initial position, heading, and velocity].

Use these initial conditions exactly. Do not resample positions, add or remove vehicles, or modify the ego vehicle’s route or destination.

**Requirements.**

1. The specified ego controller drives the ego vehicle. Do not script its driving actions or modify its controller.
2. Design the subsequent driving behaviors of the three NPCs using the supplied language and tools. No particular action sequence, interaction outcome, or behavior-model combination is required.
3. You may use supported reactive behaviors, stochastic choices, behavior composition, or model interfaces. Use only capabilities documented in the supplied materials.
4. Ensure that NPC behaviors are consistent with the road configuration. Do not force a collision, violation, or particular ego response.
5. If the script includes stochastic choices, specify their ranges, distributions, sampling times, and seed-setting mechanisms. Otherwise, state that no stochastic choices are used.
6. Do not invent syntax, APIs, or unavailable behavior implementations. If the task cannot be implemented with the supplied tools, identify the missing capability explicitly.

**Required output.** Provide one complete scenario script, its dependencies and
execution command, a brief description of each NPC’s behavior, and any stochastic
configuration.
