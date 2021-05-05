from micromanager_gui._core._client import detatched_mmcore
from useq import MDASequence

mda = MDASequence(
    axis_order="tzpc",
    stage_positions=[(10, 20, 30)],
    channels=[dict(config="Cy5", exposure=100)],
    time_plan=dict(interval=3, loops=4),
    z_plan=dict(range=1.0, step=0.5),
)


with detatched_mmcore(config="demo") as proc:
    core = proc.core
    core.snapImage()
    a = core.getImage()
    print(a)
    print("arr", a.shape, a.dtype, a.mean())
