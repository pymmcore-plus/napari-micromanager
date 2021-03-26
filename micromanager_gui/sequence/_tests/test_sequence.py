import itertools

import numpy as np
import pytest
from micromanager_gui.sequence import (
    INDICES,
    Channel,
    MDASequence,
    NoT,
    NoZ,
    Position,
    TDurationLoops,
    TIntervalDuration,
    TIntervalLoops,
    ZAboveBelow,
    ZAbsolutePositions,
    ZRangeAround,
    ZRelativePositions,
)

z_as_class = [
    (ZAboveBelow(above=8, below=4, step=2), [-4, -2, 0, 2, 4, 6, 8]),
    (ZAbsolutePositions(absolute=[0, 0.5, 5]), [0, 0.5, 5]),
    (ZRelativePositions(relative=[0, 0.5, 5]), [0, 0.5, 5]),
    (ZRangeAround(range=8, step=1), [-4, -3, -2, -1, 0, 1, 2, 3, 4]),
]
z_as_dict = [
    ({"above": 8, "below": 4, "step": 2}, [-4, -2, 0, 2, 4, 6, 8]),
    ({"absolute": [0, 0.5, 5]}, [0, 0.5, 5]),
    ({"relative": [0, 0.5, 5]}, [0, 0.5, 5]),
    ({"range": 8, "step": 1}, [-4, -3, -2, -1, 0, 1, 2, 3, 4]),
    (NoZ(), []),
    (None, []),
]
z_inputs = z_as_class + z_as_dict

t_as_class = [
    # frame every second for 4 seconds
    (TIntervalDuration(interval=1, duration=4), [0, 1000, 2000, 3000, 4000]),
    # 5 frames spanning 8 seconds
    (TDurationLoops(loops=5, duration=8), [0, 2000, 4000, 6000, 8000]),
    # 5 frames, taken every 250 ms
    (TIntervalLoops(loops=5, interval=0.25), [0, 250, 500, 750, 1000]),
    (
        [
            TIntervalLoops(loops=5, interval=0.25),
            TIntervalDuration(interval=1, duration=4),
        ],
        [0, 250, 500, 750, 1000, 2000, 3000, 4000, 5000],
    ),
]

t_as_dict = [
    ({"interval": 0.5, "duration": 2}, [0, 500, 1000, 1500, 2000]),
    ({"loops": 5, "duration": 8}, [0, 2000, 4000, 6000, 8000]),
    ({"loops": 5, "duration": {"seconds": 8}}, [0, 2000, 4000, 6000, 8000]),
    ({"loops": 5, "duration": {"milliseconds": 8}}, [0, 2, 4, 6, 8]),
    ({"loops": 5, "interval": 0.25}, [0, 250, 500, 750, 1000]),
    (
        [{"loops": 5, "interval": 0.25}, {"interval": 1, "duration": 4}],
        [0, 250, 500, 750, 1000, 2000, 3000, 4000, 5000],
    ),
    (NoT(), []),
    (None, []),
]
t_inputs = t_as_class + t_as_dict


all_orders = ["".join(i) for i in itertools.permutations(INDICES)]

c_inputs = [
    (Channel(config="DAPI"), ("Channel", "DAPI")),
    (Channel(config="DAPI", group="Group"), ("Group", "DAPI")),
    ("DAPI", ("Channel", "DAPI")),
    ({"config": "DAPI"}, ("Channel", "DAPI")),
    ({"config": "DAPI", "group": "Group", "acquire_every": 3}, ("Group", "DAPI")),
]

p_inputs = [
    (Position(x=100, y=200, z=300), (100, 200, 300)),
    ((100, 200, 300), (100, 200, 300)),
    ((None, 200, None), (None, 200, None)),
    ({"y": 200}, (None, 200, None)),
    ({"x": 0, "y": 1, "z": 2}, (0, 1, 2)),
    ({"z": 100, "z_plan": {"above": 8, "below": 4, "step": 2}}, (None, None, 100)),
    (np.ones(2), (1, 1, None)),
    (np.ones(3), (1, 1, 1)),
]


@pytest.mark.parametrize("zplan, zexpectation", z_inputs)
def test_z_plan(zplan, zexpectation):
    assert list(MDASequence(z_plan=zplan).z_plan) == zexpectation


@pytest.mark.parametrize("tplan, texpectation", t_inputs)
def test_t_plan(tplan, texpectation):
    assert list(MDASequence(time_plan=tplan).time_plan) == texpectation


@pytest.mark.parametrize("channel, cexpectation", c_inputs)
def test_channel(channel, cexpectation):
    channel = MDASequence(channels=[channel]).channels[0]
    assert (channel.group, channel.config) == cexpectation


@pytest.mark.parametrize("position, pexpectation", p_inputs)
def test_position(position, pexpectation):
    position = MDASequence(stage_positions=[position]).stage_positions[0]
    assert (position.x, position.y, position.z) == pexpectation


# @pytest.mark.parametrize("tplan, texpectation", t_as_dict)
# @pytest.mark.parametrize("zplan, zexpectation", z_as_dict)
# @pytest.mark.parametrize("channel, cexpectation", c_inputs)
# @pytest.mark.parametrize("position, pexpectation", p_inputs)
# @pytest.mark.parametrize("order", all_orders)
# def test_combinations(
#     tplan,
#     texpectation,
#     zplan,
#     zexpectation,
#     channel,
#     cexpectation,
#     order,
#     position,
#     pexpectation,
# ):
#     mda = MDASequence(
#         z_plan=zplan,
#         time_plan=tplan,
#         channels=[channel],
#         stage_positions=[position],
#         acquisition_order=order,
#     )
#     assert list(mda.z_plan) == zexpectation
#     assert list(mda.time_plan) == texpectation
#     assert (mda.channels[0].group, mda.channels[0].config) == cexpectation
#     position = mda.stage_positions[0]
#     assert (position.x, position.y, position.z) == pexpectation

#     list(mda)
