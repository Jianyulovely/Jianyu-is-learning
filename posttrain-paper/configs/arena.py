"""Central configuration for the compute-matched arena (P1).

Only edit this file. Everything else reads from here.

Design note
-----------
The whole experiment is cheap because of ONE trick: we sample K responses per
prompt ONCE, then reuse that same pool for
  (a) RFT      -> keep the correct trajectories, run SFT on them
  (b) DPO      -> pair correct vs incorrect trajectories into preferences
  (c) self-consistency -> vote over the K answers, no training at all
If you sample separately for each method, the budget triples and the paper dies.
"""

CONFIG = {
    # ---------------------------------------------------------------- models
    # Pin a revision if you can, so the paper is reproducible.
    "models": {
        "0.5B": "Qwen/Qwen2.5-0.5B-Instruct",
        "1.5B": "Qwen/Qwen2.5-1.5B-Instruct",
        # 3B is the third scale point. bf16 weights ~6 GB, so it fits the
        # 16 GB card, but LoRA + activations at seq_len 1024 put total use near
        # the limit: start with micro_batch=1 and check nvidia-smi before
        # launching a budget run. NOT yet measured -- treat 3B as unvalidated.
        "3B": "Qwen/Qwen2.5-3B-Instruct",
    },
    # Which one a bare `python src/xxx.py` uses when --model is not given.
    "default_model": "1.5B",

    # ------------------------------------------------------------------ data
    "data": {
        # Prompts used for SFT / RFT / DPO (they must be the SAME set).
        "train_frac_of_gsm8k": 0.35,   # ~2600 of 7473
        "extra_math_prompts": 400,     # from hendrycks_math train
        "dev_frac": 0.05,              # carved out of train, never touched by test
        "max_prompt_tokens": 512,
        "max_new_tokens": 512,
    },

    # ------------------------------------------------------------ sampling
    "sampling": {
        "k": 8,                 # responses per prompt
        "temperature": 0.7,
        "top_p": 0.95,
        "batch_size": 24,       # lower to 8 if you OOM on 16GB
    },

    # ----------------------------------------------------------------- lora
    "lora": {
        "r": 16,
        "alpha": 32,
        "dropout": 0.05,
        "target_modules": [
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
    },

    # ------------------------------------------------------------- training
    "train": {
        "max_seq_len": 1024,     # response + prompt; 2048 also fits on 1.5B/16GB
        "micro_batch": 2,
        "grad_accum": 8,
        "lr_sft": 1e-4,
        "lr_dpo": 5e-5,
        "warmup_ratio": 0.03,
        "weight_decay": 0.0,
        "grad_clip": 1.0,
        # "auto" -> bf16 when the GPU has it (Ampere/Ada/Hopper/Blackwell),
        # else fp32. Explicitly NOT fp16 on Pascal (Titan Xp): sm_61 runs fp16
        # at ~1/64 rate, so fp32 is both correct and faster there.
        # Run src/check_env.py on any new machine before trusting this.
        "dtype": "auto",
        "grad_checkpointing": True,
    },

    "dpo": {
        "beta": 0.1,
        "max_pairs": 6000,
    },

    # ------------------------------------------------------- budget sweep
    # The x-axis of Figure 1. Training stops when the budget is spent,
    # NOT when the model converges -- that is the whole point.
    #
    # Unit is MINUTES, not hours, and that is not a detail. With ~3000 training
    # prompts at effective batch 16, one epoch is ~188 steps ~= 94 seconds. So a
    # 1-hour budget is ~38 epochs and an 8-hour budget is ~306 epochs: the whole
    # 1/2/4/8-hour axis would sit deep inside the overfitting regime and all
    # curves would flatten into each other. 5-60 minutes covers
    # underfit -> about right -> overfit, which is the region where the
    # comparison can actually discriminate between methods.
    "budget_minutes": [5, 15, 30, 60],
    # Steps used to measure throughput before a budget run.
    "calibration_steps": 12,

    # -------------------------------------------------------------- eval
    "eval": {
        "batch_size": 16,
        "max_new_tokens": 512,
        "temperature": 0.0,       # greedy
        "datasets": ["gsm8k_test", "math500"],
        # main metric uses "standard"; all three are always reported
        "parsers": ["lenient", "standard", "strict"],
    },

    "seeds": [42, 1234],
}
