"""End-to-end wiring check. Run: python -m scripts.smoke_test"""

from app.application.dependencies.providers import get_embeddings, get_llm


def check_llm() -> None:
    reply = get_llm().generate(
        [
            {"role": "system", "content": "You are terse."},
            {"role": "user", "content": "Say hello in exactly 3 words."},
        ]
    )
    print(f"[llm]        OK -> {reply!r}")


def check_embeddings() -> None:
    vec = get_embeddings().embed_query("hello world")
    print(f"[embeddings] OK -> dims={len(vec)}, first3={vec[:3]}")


if __name__ == "__main__":
    check_llm()
    check_embeddings()
