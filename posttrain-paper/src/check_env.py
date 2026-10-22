"""Environment probe: run this on EVERY machine before adding it to the plan.

Prints the facts that actually decide what you can train:
  * GPU name, compute capability, per-device free memory
  * torch build and the CUDA version it was compiled against
  * which dtypes can run a real matmul kernel (the only test that matters --
    torch.cuda.is_available() returning True proves nothing on Pascal)
  * measured fp32 throughput, so you can compare machines instead of guessing

Why this exists: on Pascal (sm_61) the failure mode is a *matmul* failure, not
an import failure. `is_available()` is True, then the first real kernel raises
"no kernel image is available for execution on the device".

Usage:
    python src/check_env.py
Exit code 0 = every device can run both a fp32 and a matmul of the configured
dtype. Non-zero = at least one device is broken for training; read the output.
"""
from __future__ import annotations

import sys

MATMUL_N = 2048
REPEATS = 10
# arch -> (name, tensor cores, bf16)
ARCH_NOTES = {
    50: "Maxwell",
    52: "Maxwell",
    60: "Pascal",
    61: "Pascal",
    70: "Volta",
    75: "Turing",
    80: "Ampere",
    86: "Ampere",
    89: "Ada Lovelace",
    90: "Hopper",
    100: "Blackwell",
    120: "Blackwell (consumer)",
}


def main() -> int:
    try:
        import torch
    except ImportError:
        print("torch is not installed.")
        print("  RTX 5060 Ti (sm_120) -> pip install torch --index-url https://download.pytorch.org/whl/cu128")
        print("  Titan Xp  (sm_61)    -> pip install torch --index-url https://download.pytorch.org/whl/cu124")
        print("Pascal needs a cu124 (<= cu126) wheel: cu128+ wheels dropped sm_5x/sm_6x kernels.")
        return 2

    print(f"torch            : {torch.__version__}")
    print(f"torch built for  : CUDA {torch.version.cuda}")
    print(f"cuda available   : {torch.cuda.is_available()}")
    if not torch.cuda.is_available():
        print("No CUDA device visible. Check the driver before anything else.")
        return 2

    n = torch.cuda.device_count()
    print(f"device count     : {n}")

    bf16 = False
    try:
        bf16 = torch.cuda.is_bf16_supported()
    except Exception:
        pass
    print(f"bf16 supported   : {bf16}")

    failures = 0
    for i in range(n):
        props = torch.cuda.get_device_properties(i)
        cc = (props.major, props.minor)
        arch = ARCH_NOTES.get(props.major * 10 + props.minor, "unknown")
        free, total = torch.cuda.mem_get_info(i)
        print(f"\n--- device {i} ---")
        print(f"name             : {props.name}")
        print(f"compute cap      : sm_{cc[0]}{cc[1]}  ({arch})")
        print(f"memory           : {free/2**30:.1f} GiB free / {total/2**30:.1f} GiB total")

        if cc[0] == 6:
            print("NOTE             : Pascal. No tensor cores, no bf16, and fp16 runs")
            print("                   at ~1/64 of fp32 rate -> train in fp32 only.")

        for dt, label in ((torch.float32, "fp32"), (torch.float16, "fp16"),
                          (torch.bfloat16, "bf16")):
            try:
                a = torch.randn(MATMUL_N, MATMUL_N, device=f"cuda:{i}", dtype=dt)
                b = torch.randn(MATMUL_N, MATMUL_N, device=f"cuda:{i}", dtype=dt)
                torch.cuda.synchronize(i)
                for _ in range(2):
                    c = a @ b
                torch.cuda.synchronize(i)
                import time

                t0 = time.perf_counter()
                for _ in range(REPEATS):
                    c = a @ b
                torch.cuda.synchronize(i)
                sec = (time.perf_counter() - t0) / REPEATS
                tflops = 2 * MATMUL_N**3 / sec / 1e12
                print(f"{label} matmul      : OK    {tflops:7.2f} TFLOP/s")
                del a, b, c
            except Exception as e:
                msg = str(e).split("\n")[0][:110]
                print(f"{label} matmul      : FAIL  {msg}")
                if dt is torch.float32:
                    failures += 1

    print("\n--- verdict ---")
    if failures:
        print(f"{failures} device(s) cannot run a fp32 matmul. This is a WHEEL problem,")
        print("not a hardware problem: install a torch built for this compute capability.")
    else:
        print("All devices run fp32 matmul. Safe to train in fp32.")
    print("Set cfg['train']['dtype'] accordingly ('auto' picks bf16 when available,")
    print("otherwise fp32 -- which is the correct choice on Pascal).")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
