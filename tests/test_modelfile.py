"""Tests for model family detection and Modelfile generation."""

from hf2ollama.modelfile.generator import (
    detect_family,
    generate_modelfile,
    sanitize_model_name,
)
from hf2ollama.modelfile.templates import TEMPLATES


class TestDetectFamily:
    def test_llama4(self) -> None:
        assert detect_family("Meta-Llama-4-Maverick-17B-Q4_K_M.gguf") == "llama4"
        assert detect_family("llama4-scout-Q6_K.gguf") == "llama4"

    def test_llama3(self) -> None:
        assert detect_family("Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf") == "llama3"
        assert detect_family("llama-3-70b-instruct.gguf") == "llama3"

    def test_gemma(self) -> None:
        assert detect_family("gemma-4-12B-it-Q4_K_M.gguf") == "gemma"
        assert detect_family("gemma3-27B-Q8_0.gguf") == "gemma"
        assert detect_family("google_gemma-2-9b-it.gguf") == "gemma"

    def test_qwen(self) -> None:
        assert detect_family("Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf") == "qwen"
        assert detect_family("Qwen3-8B-Q6_K.gguf") == "qwen"
        assert detect_family("QwQ-32B-Q4_K_M.gguf") == "qwen"

    def test_mistral(self) -> None:
        assert detect_family("Mistral-7B-Instruct-v0.3-Q4_K_M.gguf") == "mistral"
        assert detect_family("Mixtral-8x7B-Instruct-Q5_K_M.gguf") == "mistral"
        assert detect_family("Nemo-12B-Q4_K_M.gguf") == "mistral"

    def test_phi(self) -> None:
        assert detect_family("Phi-4-mini-instruct-Q4_K_M.gguf") == "phi"
        assert detect_family("phi-3-medium-Q6_K.gguf") == "phi"

    def test_deepseek(self) -> None:
        assert detect_family("DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf") == "deepseek"
        assert detect_family("ds-r1-lite-Q4_K_M.gguf") == "deepseek"

    def test_granite(self) -> None:
        assert detect_family("granite-3.1-8b-instruct-Q4_K_M.gguf") == "granite"

    def test_command_r(self) -> None:
        assert detect_family("command-r-plus-Q4_K_M.gguf") == "command-r"
        assert detect_family("c4ai-command-r7b-Q4_K_M.gguf") == "command-r"

    def test_fallback_chatml(self) -> None:
        assert detect_family("some-unknown-model-Q4_K_M.gguf") == "chatml"


class TestSanitizeModelName:
    def test_basic(self) -> None:
        name = sanitize_model_name("Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf")
        assert "qwen" in name
        assert "q4_k_m" in name
        assert ".gguf" not in name

    def test_no_special_chars(self) -> None:
        name = sanitize_model_name("Some Model (v2) [Q8_0].gguf")
        assert "(" not in name
        assert " " not in name

    def test_quant_tag_appended(self) -> None:
        name = sanitize_model_name("llama3-8b-Q6_K.gguf")
        assert ":q6_k" in name


class TestGenerateModelfile:
    def test_contains_from_directive(self) -> None:
        mf = generate_modelfile("model-Q4_K_M.gguf", family="qwen")
        assert "FROM ./model-Q4_K_M.gguf" in mf

    def test_contains_template(self) -> None:
        mf = generate_modelfile("model.gguf", family="llama3")
        assert "TEMPLATE" in mf
        assert "<|start_header_id|>" in mf

    def test_contains_stop_tokens(self) -> None:
        mf = generate_modelfile("model.gguf", family="qwen")
        assert 'PARAMETER stop "<|im_end|>"' in mf

    def test_all_families_generate(self) -> None:
        for family in TEMPLATES:
            mf = generate_modelfile("test.gguf", family=family)
            assert "FROM ./test.gguf" in mf
            assert "TEMPLATE" in mf
            assert "PARAMETER stop" in mf
