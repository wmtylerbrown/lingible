"""Translation failure messages with brand voice."""

import random
from typing import List


class TranslationMessages:
    """Translation failure messages grouped by type for varied UX."""

    LOW_CONFIDENCE: List[str] = [
        "Hmm, we're not vibing with this one. Try different wording or break it down? No cap, we want to get it right.",
        "This one's got us confused, not gonna lie. Maybe rephrase it?",
        "We're drawing a blank on this one. Try breaking it into smaller pieces?",
        "Hmm, we're not getting it. Can you say it differently?",
        "Ngl, this one's tricky. Mind rewording it for us?",
    ]

    NO_TRANSLATION_GENZ_TO_ENGLISH: List[str] = [
        "Looks like this is already in plain English, or it's slang we haven't learned yet. Help us out?",
        "This already sounds pretty standard to us. No slang detected, or it's something new!",
        "We're not seeing any Gen Z here. Already in plain English, fam!",
        "This seems like regular English already, or it's new slang we haven't caught yet.",
    ]

    NO_TRANSLATION_ENGLISH_TO_GENZ: List[str] = [
        "This already sounds pretty Gen Z to us, or we just don't have the sauce for it yet.",
        "Honestly? This already hits different. Can't make it more Gen Z!",
        "This is already giving Gen Z energy. We got nothing to add!",
        "Ngl, this is already peak Gen Z. Nothing to change here!",
    ]

    @staticmethod
    def get_random_message(message_list: List[str]) -> str:
        """
        Get a random message from the list.

        Args:
            message_list: List of messages to choose from

        Returns:
            Randomly selected message
        """
        return random.choice(message_list)

    @classmethod
    def get_low_confidence_message(cls) -> str:
        """Get a random low confidence message."""
        return cls.get_random_message(cls.LOW_CONFIDENCE)

    @classmethod
    def get_already_english_message(cls) -> str:
        """Get a random 'already in English' message."""
        return cls.get_random_message(cls.NO_TRANSLATION_GENZ_TO_ENGLISH)

    @classmethod
    def get_already_genz_message(cls) -> str:
        """Get a random 'already Gen Z' message."""
        return cls.get_random_message(cls.NO_TRANSLATION_ENGLISH_TO_GENZ)
