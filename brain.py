import anthropic
import threading


class Brain:
    def __init__(self, api_key=None, model="claude-sonnet-4-20250514"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self._lock = threading.Lock()

    def ask(self, transcript, question, callback=None):
        """Ask a question about the transcript. Streams response via callback."""
        system = (
            "You are a real-time meeting assistant. The user is in a live meeting. "
            "You have access to the meeting transcript so far. "
            "Answer the user's question concisely based on the transcript context. "
            "If they ask 'what should I say', suggest a response they could give in the meeting. "
            "If they ask for a recap, summarize the key points. "
            "Keep responses brief and actionable - they're reading this mid-conversation."
        )

        transcript_block = transcript[-8000:] if len(transcript) > 8000 else transcript

        messages = [
            {
                "role": "user",
                "content": (
                    f"Meeting transcript so far:\n---\n{transcript_block}\n---\n\n"
                    f"Question: {question}"
                ),
            }
        ]

        try:
            with self.client.messages.stream(
                model=self.model,
                max_tokens=500,
                system=system,
                messages=messages,
            ) as stream:
                full = ""
                for text in stream.text_stream:
                    full += text
                    if callback:
                        callback(full)
                return full
        except Exception as e:
            error_msg = f"[Error: {e}]"
            if callback:
                callback(error_msg)
            return error_msg

    def auto_notes(self, transcript):
        """Generate meeting notes from transcript."""
        if len(transcript.strip()) < 100:
            return "Not enough transcript yet."

        system = (
            "Generate concise meeting notes from this transcript. "
            "Use bullet points. Include: key decisions, action items, "
            "important numbers/dates mentioned. Be brief."
        )

        transcript_block = transcript[-12000:] if len(transcript) > 12000 else transcript

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                system=system,
                messages=[{"role": "user", "content": transcript_block}],
            )
            return response.content[0].text
        except Exception as e:
            return f"[Error generating notes: {e}]"
