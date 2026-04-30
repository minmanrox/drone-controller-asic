# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, FallingEdge, Timer, Lock
from cocotb.utils import get_sim_time

CLK_PERIOD_NS = 40  # 25 MHz
PERIOD_CYCLES = 500_000  # 20 ms @ 25 MHz
HIGH_CYCLES_MAX = 50_000
LOW_CYCLES_MAX  = PERIOD_CYCLES - HIGH_CYCLES_MAX
HIGH_CYCLES_MIN = 25_000
LOW_CYCLES_MIN  = PERIOD_CYCLES - HIGH_CYCLES_MIN


######################
## Helper Functions ##
######################


async def setup_dut(dut):
    dut.ena.value = 1
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 10)


async def measure_pwm_duty(dut, cycles: int) -> dict[int, float]:
    """
    Measure duty cycle of pwm_out1..4 over 'cycles' rising edges of dut.clk.
    Returns a dict with fractional duty: {1: d1, 2: d2, 3: d3, 4: d4}.
    """

    # Counters for high time
    high_counts = {
        1: 0,
        2: 0,
        3: 0,
        4: 0,
    }

    for _ in range(cycles):
        await RisingEdge(dut.clk)
        high_counts[1] += int(dut.uo_out.value[0])
        high_counts[2] += int(dut.uo_out.value[1])
        high_counts[3] += int(dut.uo_out.value[2])
        high_counts[4] += int(dut.uo_out.value[3])

    duty = {ch: high_counts[ch] / cycles for ch in high_counts}
    return duty


async def drive_pwm_input(clk, signal, high_cycles, low_cycles, periods):
    """Drive 'signal' with 'periods' PWM periods at given high/low cycle counts."""
    for _ in range(periods):
        signal.value = 1
        for _ in range(high_cycles):
            await RisingEdge(clk)
        signal.value = 0
        for _ in range(low_cycles):
            await RisingEdge(clk)


_ui_in_lock = Lock()


async def set_vec_bit(vec_handle, bit_idx, bit_val):
    async with _ui_in_lock:
        v = vec_handle.value
        v[bit_idx] = bit_val
        vec_handle.value = v


async def drive_pwm_bit(clk, vec_handle, bit_idx, high_cycles, low_cycles, periods, dut=None):
    for _ in range(periods):
        await set_vec_bit(vec_handle, bit_idx, 1)
        if dut:
            dut._log.info(f"Set bit idx {bit_idx} to 1")
        for _ in range(high_cycles):
            await RisingEdge(clk)

        await set_vec_bit(vec_handle, bit_idx, 0)
        if dut:
            dut._log.info(f"Set bit idx {bit_idx} to 0")
        for _ in range(low_cycles):
            await RisingEdge(clk)


def build_ui_in_value(pwm1, pwm2, pwm3, pwm4, arm):
    return (
        "0"                           # ui_in[7]
        "0"                           # ui_in[6]
        f"{int(arm)}"                 # ui_in[5]
        f"{int(pwm4)}"                # ui_in[4]
        f"{int(pwm3)}"                # ui_in[3]
        f"{int(pwm2)}"                # ui_in[2]
        f"{int(pwm1)}"                # ui_in[1]
        "0"                           # ui_in[0]
    )


async def drive_multiple_pwms(clk, vec_handle, pwm_cfgs, periods):
    """
    pwm_cfgs:
        dict {bit_idx: (high_cycles, low_cycles)}
        expected bits:
            1 -> pwm1
            2 -> pwm2
            3 -> pwm3
            4 -> pwm4
            5 -> arm
    """
    total_cycles = periods * PERIOD_CYCLES

    for cycle_in_test in range(total_cycles):
        cycle_in_period = cycle_in_test % PERIOD_CYCLES

        bit_values = {}
        for bit_idx, (high_cycles, low_cycles) in pwm_cfgs.items():
            bit_values[bit_idx] = 1 if cycle_in_period < high_cycles else 0

        vec_handle.value = build_ui_in_value(
            pwm1=bit_values.get(1, 0),
            pwm2=bit_values.get(2, 0),
            pwm3=bit_values.get(3, 0),
            pwm4=bit_values.get(4, 0),
            arm=bit_values.get(5, 0),
        )

        await RisingEdge(clk)


def set_input_values(
    dut,
    pwm_in1=0,
    pwm_in2=0,
    pwm_in3=0,
    pwm_in4=0,
    arm_in=0,
):
    for sig in [pwm_in1, pwm_in2, pwm_in3, pwm_in4, arm_in]:
        if sig != 0 and sig != 1:
            assert False, "set_input_values() args must be 1 or 0"

    bitstring = (
        "0"                           # ui_in[7]
        "0"                           # ui_in[6]
        f"{int(arm_in)}"              # ui_in[5]
        f"{int(pwm_in4)}"             # ui_in[4]
        f"{int(pwm_in3)}"             # ui_in[3]
        f"{int(pwm_in2)}"             # ui_in[2]
        f"{int(pwm_in1)}"             # ui_in[1]
        "0"                           # ui_in[0]
    )

    dut.ui_in.value = bitstring


async def drive_controls(dut, throttle, pitch, roll, yaw, periods=1):
    if not (0 <= throttle <= 1):
        raise ValueError("throttle must be between 0 and 1")
    if not (0 <= pitch <= 1):
        raise ValueError("pitch must be between 0 and 1")
    if not (0 <= roll <= 1):
        raise ValueError("roll must be between 0 and 1")
    if not (0 <= yaw <= 1):
        raise ValueError("yaw must be between 0 and 1")

    throttleCyclesHigh = int(throttle * (HIGH_CYCLES_MAX - HIGH_CYCLES_MIN) + HIGH_CYCLES_MIN)
    pitchCyclesHigh    = int(pitch    * (HIGH_CYCLES_MAX - HIGH_CYCLES_MIN) + HIGH_CYCLES_MIN)
    rollCyclesHigh     = int(roll     * (HIGH_CYCLES_MAX - HIGH_CYCLES_MIN) + HIGH_CYCLES_MIN)
    yawCyclesHigh      = int(yaw      * (HIGH_CYCLES_MAX - HIGH_CYCLES_MIN) + HIGH_CYCLES_MIN)

    pwm_cfgs = {
        1: (throttleCyclesHigh, PERIOD_CYCLES - throttleCyclesHigh),
        2: (yawCyclesHigh,      PERIOD_CYCLES - yawCyclesHigh),
        3: (pitchCyclesHigh,    PERIOD_CYCLES - pitchCyclesHigh),
        4: (rollCyclesHigh,     PERIOD_CYCLES - rollCyclesHigh),
        5: (HIGH_CYCLES_MAX,    LOW_CYCLES_MAX),  # arm held high with PWM-style config
    }

    await drive_multiple_pwms(
        clk=dut.clk,
        vec_handle=dut.ui_in,
        pwm_cfgs=pwm_cfgs,
        periods=periods,
    )


async def read_mixer_values(dut):
    """Sample current logic levels for the 4 PWM outputs."""
    return {
        "throttleRaw": str(dut.user_project.controller.mx.throttle.value),
        "pitchRaw":    str(dut.user_project.controller.mx.pitch.value),
        "rollRaw":     str(dut.user_project.controller.mx.roll.value),
        "yawRaw":      str(dut.user_project.controller.mx.yaw.value),
        "throttleInt": int(dut.user_project.controller.mx.throttleSigned.value.to_signed()),
        "pitchInt":    int(dut.user_project.controller.mx.pitchSigned.value.to_signed()),
        "rollInt":     int(dut.user_project.controller.mx.rollSigned.value.to_signed()),
        "yawInt":      int(dut.user_project.controller.mx.yawSigned.value.to_signed()),
        "m1":       str(dut.user_project.controller.mx.motor1.value),
        "m2":       str(dut.user_project.controller.mx.motor2.value),
        "m3":       str(dut.user_project.controller.mx.motor3.value),
        "m4":       str(dut.user_project.controller.mx.motor4.value),
        "m1Int":       int(dut.user_project.controller.mx.motor1.value.to_signed()),
        "m2Int":       int(dut.user_project.controller.mx.motor2.value.to_signed()),
        "m3Int":       int(dut.user_project.controller.mx.motor3.value.to_signed()),
        "m4Int":       int(dut.user_project.controller.mx.motor4.value.to_signed()),
    }


######################
## Tests begin here ##
######################


@cocotb.test()
async def dummy_smoke_test(dut):
    """Simple smoke test: toggle inputs and run a few cycles."""
    dut._log.info("Starting dummy smoke test")

    # Initialize inputs
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, unit="ns").start())
    # dut.ui_in.value[1] = 0
    # dut.ui_in.value[2] = 0
    # dut.ui_in.value[3] = 0
    # dut.ui_in.value[4] = 0
    # dut.ui_in.value[5] = 0
    # dut.ui_in.value[6] = 0
    set_input_values(dut) # default is 0 for all inputs

    await setup_dut(dut)

    # Let things settle
    await Timer(1, unit="ns")

    # Apply a simple stimulus
    # dut.ui_in.value[5] = 1
    set_input_values(dut, arm_in=1)
    dut._log.info("Arm asserted")
    await RisingEdge(dut.clk)
    # dut.ui_in.value[5] = 0
    set_input_values(dut, arm_in=0)

    # Run for 100 clock cycles
    for i in range(100):
        await RisingEdge(dut.clk)
    dut._log.info(f"Cycle {i}: pwm_out1={int(dut.uo_out.value[0])}")

    dut._log.info("Dummy smoke test completed")


@cocotb.test(skip=False)
async def test_arm_gates_throttle(dut):
    """With throttle max: arm=0 → no PWM out; arm=1 → PWM present."""
    dut._log.info("Starting arm gating test")

    # Start 25 MHz clock
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, unit="ns").start())

    # Initialize inputs
    # dut.ui_in.value[5] = 0 # arm
    # dut.ui_in.value[1] = 0 # pwm_inX
    # dut.ui_in.value[2] = 0 # pwm_inX
    # dut.ui_in.value[3] = 0 # pwm_inX
    # dut.ui_in.value[4] = 0 # pwm_inX
    set_input_values(dut)

    await setup_dut(dut)

    # Let DUT settle
    await Timer(2, unit="ms")

    # Define max and min throttle input PWM
    high_cycles_max = 50_000
    low_cycles_max  = PERIOD_CYCLES - high_cycles_max
    high_cycles_min = 25_000
    low_cycles_min  = PERIOD_CYCLES - high_cycles_min

    # Phase 1: arm=0, drive max throttle, output should remain effectively off
    dut._log.info("Phase 1: arm=0, throttle=max")

    # drive throttle and arm (for min) simultaneously
    pwm_cfgs = {
        1: (high_cycles_max, low_cycles_max), # pwm_in1
        5: (high_cycles_min, low_cycles_min), # arm
    }
    await drive_multiple_pwms(dut.clk, dut.ui_in, pwm_cfgs, 1)
    assert(dut.uo_out.value[5] == 0) # arm_led

    # Measure pwm_out1 duty over a few periods
    duty_disarmed = await measure_pwm_duty(dut, PERIOD_CYCLES)
    d1_disarmed = duty_disarmed[1]
    dut._log.info(f"Disarmed duty pwm_out1={d1_disarmed:.4f}")

    # Expect minimum duty (ideally 0.05)
    assert d1_disarmed <= 0.05, "pwm_out1 should be near 0.05 when arm=0"

    # Phase 2: arm=1, same max throttle, now PWM should be present
    dut._log.info("Phase 2: arm=1, throttle=max")

    # drive throttle and arm (for max) simultaneously
    pwm_cfgs = {
        1: (high_cycles_max, low_cycles_max), # pwm_in1
        5: (high_cycles_max, low_cycles_max), # arm
    }
    await drive_multiple_pwms(dut.clk, dut.ui_in, pwm_cfgs, 1)
    assert(dut.uo_out.value[5] == 1) # arm_led

    duty_armed = await measure_pwm_duty(dut, PERIOD_CYCLES)
    d1_armed = duty_armed[1]
    dut._log.info(f"Armed duty pwm_out1={d1_armed:.4f}")

    # Expect high pulse > 1.5ms
    assert d1_armed > 0.07, "pwm_out1 should be active when arm=1 and throttle=max"

    dut._log.info("Arm gating test PASSED")


@cocotb.test(skip=False)
async def test_throttle_min_max(dut):
    """Throttle axis only: min and max, all other axes neutral."""
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, unit="ns").start())

    await setup_dut(dut)

    # Throttle minimum
    await drive_controls(dut, throttle=0, pitch=0.5, roll=0.5, yaw=0.5)
    # levels = await read_mixer_values(dut)
    # dut._log.debug(f"Levels (min): {levels}")

    min_duties = await measure_pwm_duty(dut, PERIOD_CYCLES)
    dut._log.debug(f"Duties (min): {min_duties}")
    for motor, duty in min_duties.items():
        assert duty > 0.05 and duty < 0.07, f"min_throttle motor {motor} duty out of range at {duty}"

    # Throttle maximum
    await drive_controls(dut, throttle=1, pitch=0.5, roll=0.5, yaw=0.5)
    # levels = await read_mixer_values(dut)
    # dut._log.debug(f"Levels (min): {levels}")
    max_duties = await measure_pwm_duty(dut, PERIOD_CYCLES)
    dut._log.debug(f"Duties (max): {max_duties}")
    for motor, duty in max_duties.items():
        assert duty > 0.065 and duty < 0.08, f"max_throttle motor {motor} duty out of range at {duty}"


@cocotb.test(skip=False)
async def test_pitch_min_max(dut):
    """Pitch axis only: min and max, all other axes neutral."""
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, unit="ns").start())

    await setup_dut(dut)

    # Pitch minimum
    dut._log.info("Driving pitch low (tilt backwards)")
    await drive_controls(dut, throttle=0.5, pitch=0, roll=0.5, yaw=0.5)
    # levels = await read_mixer_values(dut)
    # dut._log.info(f"Levels (min): {levels}")

    min_duties = await measure_pwm_duty(dut, PERIOD_CYCLES)
    dut._log.info(f"Duties (min): {min_duties}")
    # expect front motors (1, 2) high, rear motors (3, 4) low
    assert min_duties[1] == min_duties[2], f"Motors 1 ({min_duties[1]}) and 2 ({min_duties[2]}) not equal"
    assert min_duties[3] == min_duties[4], f"Motors 3 ({min_duties[3]}) and 4 ({min_duties[4]}) not equal"
    assert min_duties[1] >  min_duties[4], f"Front motors ({min_duties[1]}) not faster than rear motors ({min_duties[4]})"

    # Pitch maximum
    dut._log.info("Driving pitch high (tilt forwards)")
    await drive_controls(dut, throttle=0.5, pitch=1, roll=0.5, yaw=0.5)
    # levels = await read_mixer_values(dut)
    # dut._log.info(f"Levels (min): {levels}")
    max_duties = await measure_pwm_duty(dut, PERIOD_CYCLES)
    dut._log.info(f"Duties (max): {max_duties}")
    # expect front motors (1, 2) low, rear motors (3, 4) high
    assert max_duties[1] == max_duties[2], f"Motors 1 ({max_duties[1]}) and 2 ({max_duties[2]}) not equal"
    assert max_duties[3] == max_duties[4], f"Motors 3 ({max_duties[3]}) and 4 ({max_duties[4]}) not equal"
    assert max_duties[1] <  max_duties[4], f"Front motors ({max_duties[1]}) not slower than rear motors ({max_duties[4]})"


@cocotb.test(skip=False)
async def test_roll_min_max(dut):
    """Roll axis only: min and max, all other axes neutral."""
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, unit="ns").start())

    await setup_dut(dut)

    # Roll minimum
    dut._log.info("Driving roll low (tilt left)")
    await drive_controls(dut, throttle=0.5, pitch=0.5, roll=0, yaw=0.5)
    # levels = await read_mixer_values(dut)
    # dut._log.info(f"Levels (min): {levels}")

    min_duties = await measure_pwm_duty(dut, PERIOD_CYCLES)
    dut._log.info(f"Duties (min): {min_duties}")
    # expect left motors (1, 4) low, right motors (2, 3) high
    assert min_duties[1] == min_duties[4], f"Motors 1 ({min_duties[1]}) and 4 ({min_duties[4]}) not equal"
    assert min_duties[2] == min_duties[3], f"Motors 2 ({min_duties[2]}) and 3 ({min_duties[3]}) not equal"
    assert min_duties[1] <  min_duties[2], f"Right motors ({min_duties[2]}) not faster than left motors ({min_duties[1]})"

    # Roll maximum
    dut._log.info("Driving roll high (tilt right)")
    await drive_controls(dut, throttle=0.5, pitch=0.5, roll=1, yaw=0.5)
    # levels = await read_mixer_values(dut)
    # dut._log.info(f"Levels (min): {levels}")
    max_duties = await measure_pwm_duty(dut, PERIOD_CYCLES)
    dut._log.info(f"Duties (max): {max_duties}")
    # expect left motors (1, 4) high, right motors (2, 3) low
    assert max_duties[1] == max_duties[4], f"Motors 1 ({max_duties[1]}) and 4 ({max_duties[4]}) not equal"
    assert max_duties[2] == max_duties[3], f"Motors 2 ({max_duties[2]}) and 3 ({max_duties[3]}) not equal"
    assert max_duties[1] >  max_duties[2], f"Left motors ({max_duties[1]}) not faster than right motors ({max_duties[2]})"


@cocotb.test(skip=False)
async def test_yaw_min_max(dut):
    """Yaw axis only: min and max, all other axes neutral."""
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, unit="ns").start())

    await setup_dut(dut)

    # Yaw minimum
    dut._log.info("Driving yaw low (rotate CCW)")
    await drive_controls(dut, throttle=0.5, pitch=0.5, roll=0.5, yaw=0)
    # levels = await read_mixer_values(dut)
    # dut._log.info(f"Levels (min): {levels}")

    min_duties = await measure_pwm_duty(dut, PERIOD_CYCLES)
    dut._log.info(f"Duties (min): {min_duties}")
    # expect CW motors (2, 4) low, CCW motors (1, 3) high
    assert min_duties[2] == min_duties[4], f"Motors 2 ({min_duties[1]}) and 4 ({min_duties[4]}) not equal"
    assert min_duties[1] == min_duties[3], f"Motors 1 ({min_duties[2]}) and 3 ({min_duties[3]}) not equal"
    assert min_duties[1] >  min_duties[2], f"CW motors ({min_duties[2]}) not slower than CCW motors ({min_duties[1]})"

    # Yaw maximum
    dut._log.info("Driving yaw high (rotate CW)")
    await drive_controls(dut, throttle=0.5, pitch=0.5, roll=0.5, yaw=1)
    # levels = await read_mixer_values(dut)
    # dut._log.info(f"Levels (min): {levels}")
    max_duties = await measure_pwm_duty(dut, PERIOD_CYCLES)
    dut._log.info(f"Duties (max): {max_duties}")
    # expect CW motors (2, 4) high, CCW motors (1, 3) low
    assert max_duties[2] == max_duties[4], f"Motors 2 ({max_duties[1]}) and 4 ({max_duties[4]}) not equal"
    assert max_duties[1] == max_duties[3], f"Motors 1 ({max_duties[2]}) and 3 ({max_duties[3]}) not equal"
    assert max_duties[1] <  max_duties[2], f"CCW motors ({max_duties[1]}) not slower than CW motors ({max_duties[2]})"


@cocotb.test(skip=False)
async def test_control_extremes(dut):
    """Test extreme control inputs and confirm outputs stay within bounds and match expected behavior"""
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, unit="ns").start())

    await setup_dut(dut)

    dut._log.info("Driving all inputs low")
    await drive_controls(dut, throttle=0, pitch=0, roll=0, yaw=0)
    # levels = await read_mixer_values(dut)
    # dut._log.info(f"Levels (min): {levels}")

    min_duties = await measure_pwm_duty(dut, PERIOD_CYCLES)
    dut._log.info(f"Duties (min): {min_duties}")
    # check outputs in range (1-2ms)
    for motor, duty in min_duties.items():
        assert duty >= 0.05 and duty <= 0.1, f"All low - Motor {motor} duty out of range at {duty}"
    # for all controls low, motors speeds should be M4 < M1 = M2 = M3
    assert min_duties[1] == min_duties[2], f"All low - Motors 1 {min_duties[1]}) and 2 ({min_duties[2]}) not equal"
    assert min_duties[1] == min_duties[3], f"All low - Motors 1 {min_duties[1]}) and 3 ({min_duties[3]}) not equal"
    assert min_duties[4] <  min_duties[1], f"All low - Motor 4 ({min_duties[4]}) not slower than other motors ({min_duties[1]})"


    dut._log.info("Driving all inputs high")
    await drive_controls(dut, throttle=1, pitch=1, roll=1, yaw=1)
    # levels = await read_mixer_values(dut)
    # dut._log.info(f"Levels (max): {levels}")

    max_duties = await measure_pwm_duty(dut, PERIOD_CYCLES)
    dut._log.info(f"Duties (max): {max_duties}")
    # check outputs in range (1-2ms)
    for motor, duty in max_duties.items():
        assert duty >= 0.05 and duty <= 0.1, f"All high - Motor {motor} duty out of range at {duty}"
    # for all controls low, motors speeds should be M4 > M1 = M2 = M3
    assert max_duties[1] == max_duties[2], f"All high - Motors 1 {max_duties[1]}) and 2 ({max_duties[2]}) not equal"
    assert max_duties[1] == max_duties[3], f"All high - Motors 1 {max_duties[1]}) and 3 ({max_duties[3]}) not equal"
    assert max_duties[4] >  max_duties[1], f"All high - Motor 4 ({max_duties[4]}) not faster than other motors ({max_duties[1]})"


@cocotb.test(skip=False)
async def test_neutral_controls(dut):
    """Used to observe motor levels at neutral controls"""
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, unit="ns").start())

    await setup_dut(dut)

    dut._log.info("Driving all inputs neutral")
    await drive_controls(dut, throttle=0, pitch=0.5, roll=0.5, yaw=0.5)
    # levels = await read_mixer_values(dut)
    # dut._log.info(f"Levels (min): {levels}")

    # min_duties = await measure_pwm_duty(dut, PERIOD_CYCLES)
    # dut._log.info(f"Duties (min): {min_duties}")
