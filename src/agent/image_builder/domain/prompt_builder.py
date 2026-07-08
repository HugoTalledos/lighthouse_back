from .models import ImageBrief

_MOODS = [
    "warm morning light",
    "cool evening tones",
    "neutral studio light",
]


class PromptBuilder:
    def build_prompts(self, brief: ImageBrief) -> list[str]:
        style = ", ".join(brief.style_hints) if brief.style_hints else "clean, professional"
        prompts = []
        for i in range(brief.n_images):
            mood = _MOODS[i % len(_MOODS)]
            prompt = (
                f"A 1200x628 Facebook ad background image. "
                f"Concept: {brief.value_proposition}. "
                f"Audience: {brief.target_customer}. "
                f"Style: {style}, {mood}. "
                f"No text, no watermarks, no logos, no UI elements."
            )
            prompts.append(prompt)
        return prompts
