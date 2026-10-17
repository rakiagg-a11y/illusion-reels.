# Adapted optical-illusion code

Only the algorithms identified below were ported into `illusion_lab.py`. No upstream
application, setup script, remote JavaScript, model weights or network dependency is
executed by the local workflow. Full MIT notices are retained in `third_party/` and
copyright attribution appears in the renderer header. Upstream code and licenses
were inspected at these immutable commits on 2026-10-18.

| Family | Source and pinned code | Copyright / license | Adaptation |
|---|---|---|---|
| Ebbinghaus | [RealityBending/Pyllusion](https://github.com/RealityBending/Pyllusion), [`ebbinghaus_parameters.py` at 8fff53e](https://github.com/RealityBending/Pyllusion/blob/8fff53efd783e666ea29262b8d0c671c088c0453/pyllusion/Ebbinghaus/ebbinghaus_parameters.py) | Copyright (c) 2018 Dominique Makowski; [MIT notice](third_party/Pyllusion.LICENSE) | Port of the surrounding-circle center calculation. Adds bounded radius/count/gap options, portrait placement, orbital motion and a context-fade control. Equal target radius is preserved. The upstream image helper was also reviewed. |
| Footsteps | [altunenes/sorceress](https://github.com/altunenes/sorceress), [`steps.js` at 1186eba](https://github.com/altunenes/sorceress/blob/1186eba2af2a9e151e0712662c8315a57b4548a8/docs/js/steps.js) | Copyright (c) 2021 Enes; [MIT notice](third_party/sorceress.LICENSE) | Ports the striped field and shared block displacement into deterministic Pillow frames. Replaces DOM state, user controls and requestAnimationFrame with one time function, equal velocity, integer-cycle motion and a gray-field control. |
| Penrose cubes | [llop/penrose-triangle-js](https://github.com/llop/penrose-triangle-js), [`penrose-triangle.js` at af94cf0](https://github.com/llop/penrose-triangle-js/blob/af94cf09cdd2900a3b9ee753cd8526db5ab94a83/penrose-triangle.js) | Copyright (c) 2019 Albert Lobo; [MIT notice](third_party/penrose-triangle-js.LICENSE) | Ports cube placement, edge increments, three face polygons and the split-first-cube drawing order. Replaces Canvas with Pillow, and adds portrait framing, constrained variations, palettes and deterministic timing. This is a 2D impossible-occlusion construction. |

Machine-readable provenance is in `third_party/sources.json` and in each schema-v3
brief. The source object must match the supported family; arbitrary source code,
paths, URLs and additional parameters cannot be injected through a brief.

The existing paired-object renderer remains project code. Its user-provided mask
reference and Blender project are not redistributed here. Third-party authors do
not endorse this project. Further upstream changes require explicit review and
updating the pinned revision and retained notices.
