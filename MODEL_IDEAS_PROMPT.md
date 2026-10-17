# OpticPop external ideation contract — concept schema v2

Act as a creative director for relational optical illusions, rather than a selector
of single spinning objects. Return a JSON array of 4–20 concept objects matching
samples/director_v2/concepts.json. Do not return commands, code, file paths or publication actions.

For every concept define:
- id, title, theme (paired_objects, emotion, identity, duality, geometry), premise, hook (max 52 characters),
  viewer_experience;
- illusion: mechanism, cue_withheld, question, observable_event;
- visual_identity: background=black, projection=orthographic, surface=additive_dots,
  occlusion=none;
- scene, seed (integer 0–999999), requirements (list), source, authorship_note. Omit novelty_key; the importer derives it.

Think first about how two or three forms interact, which depth cue is withheld,
what observable event causes perceptual ambiguity and how the scene loops.
Vary relationships, interpretations and geometry. Color or copy changes alone are not new ideas.
Use the reference principles of transparent luminous surfaces, fine particles and
passing contours. Do not claim an exact reproduction or independently verified originality.
No unsupported statistics, promised engagement outcomes or guaranteed perceptual effects.

Implemented scene grammar:
version=1, identity as above, layout=orbit or coaxial, entities=list of 2–3 objects.
Each entity has exactly shape, expression, color, center, scale, turns, phase.
shape=mask with expression=smile/frown/neutral; or shape=arc/heart/star/crescent/butterfly/ring/leaf/diamond/lightning/flower/hourglass
with expression=null. Heart, star, crescent and butterfly are curved open shells;
ring is a complete torus.
For paired_objects, use exactly TWO non-face shapes from heart/star/crescent/butterfly/ring/leaf/diamond/lightning/flower/hourglass.
Prefer coherent shared rotation (turns=1 for both), vertical staggering, some overlap,
fine particles and different luminous colors. The illusion target is ambiguous depth
ordering or perceived rotation, not a guaranteed morph or a third object appearing.
color=coral/electric_blue/cyan/violet/amber.
center=[x,y,z] with finite values in -0.65..0.65.
scale=0.65..1.05. turns is integer -2,-1,1,2. phase is finite degrees -180..180.
All scenes run two base cycles in 15 seconds. In orbit layout, entity centers rotate
around the common vertical axis; surfaces also rotate at their own turn rate.
There is no depth sorting, morphing, opaque shading, arbitrary camera, overlay or voiceover.

Use mechanism=transparent_depth_ambiguity for paired_objects, masks or mixed scenes.
Use mechanism=overlap_completion only for two equally sized arcs with the same center,
coaxial layout, phase difference exactly 180 degrees, and distinct turn rates.

For ambitious unsupported concepts, preserve the idea with scene=null and a nonempty
requirements list naming missing geometry or renderer capabilities. Such ideas remain
development proposals and never receive a renderable production brief.
Blender may be an optional implementation route; do not require it for supported scenes.

Omit the derived novelty_key field in model output. The importer computes it after
validating the scene grammar. If a signature is supplied, it must match the actual
scene; mismatched supplied signatures are rejected.
Keep requirements empty for implemented scenes.
