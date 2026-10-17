# Visual principles extracted from the supplied reference

The local reference is an approximately 11.75-second screen recording.
Only the artwork informed this implementation; account UI, notifications and
other screen-recording details were excluded. The reference media is not committed.

Observed: a red smiling mask and a blue sad mask, vertically staggered,
convex open surfaces with fine luminous particles and clear facial strokes,
a black background, overlapping contours, profile views and repeated rotation.

Interpretation: transparent/additive overlap and weak front/back occlusion cues
make surface order and perceived rotation ambiguous. This is an interpretation
of the sampled frames, not a claim about the source artist's implementation.

The new renderer uses procedural elliptical convex shells, surface-mapped facial
curves, additive point splatting from pointcloud.Scene and independent layer turns.
It preserves the principles while allowing different relationships and geometry.
The reference does not show an implemented third face or literal morphing, so those
effects are not claimed for the current renderer.
