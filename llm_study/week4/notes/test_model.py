"""最小化测试脚本，也可以直接复制到 Notebook 中分段运行。"""

from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


# Notebook 当前目录通常是 llm_study/week4/notes。
model_path = Path("notes/Qwen2.5-Law-SFT/checkpoint-400")
device = "cuda" if torch.cuda.is_available() else "cpu"
dtype = torch.float16 if device == "cuda" else torch.float32

print("device:", device)
if device == "cuda":
    print("gpu:", torch.cuda.get_device_name(0))
print("model:", model_path.resolve())

tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "left"

model = AutoModelForCausalLM.from_pretrained(
    model_path,
    dtype=dtype,
    local_files_only=True,
).to(device)
model.eval()


def ask(question, max_new_tokens=256):
    messages = [
        {"role": "system", "content": "你是一个严谨的中文法律助手。"},
        {"role": "user", "content": question},
    ]
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    inputs = tokenizer(prompt, return_tensors="pt").to(device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.pad_token_id,
        )

    new_tokens = outputs[0, inputs["input_ids"].shape[1]:]
    return tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


# Notebook 中先运行这两行，确认一次生成是否正常。
question = "违章停车与违法停车是否有区别？"
print(ask(question))


# 需要交互时，将 while False 改为 while True 后运行这一段。
while False:
    question = input("你：").strip()
    if question.lower() in {"quit", "exit", "q"}:
        break
    if question:
        print("助手：", ask(question))
