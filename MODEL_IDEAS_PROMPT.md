# Optional external-model ideation contract

Return only a JSON array of 1–20 distinct OpticPop reel concepts.
Use samples/director/production_brief.json → idea as the object format.
Each object needs id, title, hook, mechanism, payoff, render, requires_blender=false.
Keep id stable and unique. Title, hook, mechanism and payoff must be nonempty strings
up to 240 characters. Avoid invented statistics and promises to pin comments.

Supported render keys, exactly:
style="pointspin", obj, text, seed (integer 0–999999),
seconds=15, width=1080, height=1920, fps=30.

Supported obj values:
rainbow sphere, arrow band, crown, dark star, arrow ring, cube, DNA helix,
planet, spin text, hidden word.

For hidden word use mechanism="anamorphic word alignment".
All others use mechanism="ambiguous orthographic rotation".
For spin text and hidden word supply text: 1–12 uppercase ASCII letters,
digits or spaces, with at least one non-space character.
For all other objects text=null.

The renderer supports a rotating point cloud, fixed geometry/colors and silent audio.
Hidden words align at a particular angle. It does not implement arbitrary masks,
morphs, camera cuts, overlays, extra objects, color changes, voiceovers, or Blender scenes.
Hook goes in a caption, not on-screen. Describe the actual supported effect.
Do not include executable code, commands, file paths or publishing instructions.
Use different objects and participation prompts; respect supplied recent history.
The local evaluator validates structural feasibility; a human reviews narrative fidelity.
