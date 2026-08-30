"""Chat templates and stop tokens for each model family.

Ported from ConvertToOllama.ps1. These are Go template strings that Ollama
interprets at runtime. The {{ .System }}, {{ .Prompt }}, {{ .Response }}
placeholders are Ollama's template variables.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChatTemplate:
    """Go template string and stop tokens for an Ollama Modelfile."""

    template: str
    stop_tokens: list[str]


TEMPLATES: dict[str, ChatTemplate] = {
    "llama4": ChatTemplate(
        template=(
            "{{- if .System }}<|header_start|>system<|header_end|>\n\n"
            "{{ .System }}<|eot|>{{- end }}\n"
            "<|header_start|>user<|header_end|>\n\n"
            "{{ .Prompt }}<|eot|>\n"
            "<|header_start|>assistant<|header_end|>\n\n"
            "{{ .Response }}<|eot|>"
        ),
        stop_tokens=["<|eot|>", "<|end_of_text|>"],
    ),
    "llama3": ChatTemplate(
        template=(
            "{{- if .System }}<|start_header_id|>system<|end_header_id|>\n\n"
            "{{ .System }}<|eot_id|>{{- end }}\n"
            "<|start_header_id|>user<|end_header_id|>\n\n"
            "{{ .Prompt }}<|eot_id|>\n"
            "<|start_header_id|>assistant<|end_header_id|>\n\n"
            "{{ .Response }}<|eot_id|>"
        ),
        stop_tokens=["<|eot_id|>", "<|end_of_text|>"],
    ),
    "gemma": ChatTemplate(
        template=(
            "{{- if .System }}<start_of_turn>user\n"
            "{{ .System }}\n\n"
            "{{ .Prompt }}<end_of_turn>\n"
            "<start_of_turn>model\n"
            "{{ .Response }}<end_of_turn>{{- else }}\n"
            "<start_of_turn>user\n"
            "{{ .Prompt }}<end_of_turn>\n"
            "<start_of_turn>model\n"
            "{{ .Response }}<end_of_turn>{{- end }}"
        ),
        stop_tokens=["<end_of_turn>"],
    ),
    "qwen": ChatTemplate(
        template=(
            "{{- if .System }}<|im_start|>system\n"
            "{{ .System }}<|im_end|>\n"
            "{{- end }}\n"
            "<|im_start|>user\n"
            "{{ .Prompt }}<|im_end|>\n"
            "<|im_start|>assistant\n"
            "{{ .Response }}<|im_end|>"
        ),
        stop_tokens=["<|im_end|>", "<|endoftext|>"],
    ),
    "mistral": ChatTemplate(
        template=(
            "{{- if .System }}[INST] {{ .System }}\n\n"
            "{{ .Prompt }} [/INST]{{ .Response }}"
            "{{- else }}[INST] {{ .Prompt }} [/INST]{{ .Response }}{{- end }}"
        ),
        stop_tokens=["[INST]", "</s>"],
    ),
    "phi": ChatTemplate(
        template=(
            "{{- if .System }}<|system|>\n"
            "{{ .System }}<|end|>\n"
            "{{- end }}\n"
            "<|user|>\n"
            "{{ .Prompt }}<|end|>\n"
            "<|assistant|>\n"
            "{{ .Response }}<|end|>"
        ),
        stop_tokens=["<|end|>", "<|endoftext|>"],
    ),
    "deepseek": ChatTemplate(
        template=(
            "{{- if .System }}<|begin▁of▁sentence|>"
            "{{ .System }}\n{{- end }}\n"
            "<|User|>{{ .Prompt }}\n"
            "<|Assistant|>{{ .Response }}<|end▁of▁sentence|>"
        ),
        stop_tokens=["<|end▁of▁sentence|>"],
    ),
    "granite": ChatTemplate(
        template=(
            "{{- if .System }}<|start_of_role|>system<|end_of_role|>\n"
            "{{ .System }}<|end_of_text|>\n"
            "{{- end }}\n"
            "<|start_of_role|>user<|end_of_role|>\n"
            "{{ .Prompt }}<|end_of_text|>\n"
            "<|start_of_role|>assistant<|end_of_role|>\n"
            "{{ .Response }}<|end_of_text|>"
        ),
        stop_tokens=["<|end_of_text|>"],
    ),
    "command-r": ChatTemplate(
        template=(
            "{{- if .System }}<|START_OF_TURN_TOKEN|><|SYSTEM_TOKEN|>"
            "{{ .System }}<|END_OF_TURN_TOKEN|>{{- end }}\n"
            "<|START_OF_TURN_TOKEN|><|USER_TOKEN|>{{ .Prompt }}<|END_OF_TURN_TOKEN|>\n"
            "<|START_OF_TURN_TOKEN|><|CHATBOT_TOKEN|>{{ .Response }}<|END_OF_TURN_TOKEN|>"
        ),
        stop_tokens=["<|END_OF_TURN_TOKEN|>"],
    ),
    "chatml": ChatTemplate(
        template=(
            "{{- if .System }}<|im_start|>system\n"
            "{{ .System }}<|im_end|>\n"
            "{{- end }}\n"
            "<|im_start|>user\n"
            "{{ .Prompt }}<|im_end|>\n"
            "<|im_start|>assistant\n"
            "{{ .Response }}<|im_end|>"
        ),
        stop_tokens=["<|im_end|>"],
    ),
}

SUPPORTED_FAMILIES = list(TEMPLATES.keys())
